from datetime import timedelta, timezone
from math import asin, cos, radians, sin, sqrt
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from shapely.geometry import Point, shape
from sqlalchemy import select, text

from app.config import settings
from app.db import now
from app.models import (
    AuditLog,
    Authority,
    Boundary,
    Calendar,
    Complaint,
    ComplaintEvent,
    Escalation,
    Notification,
    Responsibility,
    User,
)
from app.security import ADMIN_ROLES

TERMINAL = {"CLOSED", "REJECTED", "RESOLVED", "VERIFICATION"}


def working_deadline(start, days, calendar):
    local = start.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(calendar.timezone))
    count = 0
    while count < days:
        local += timedelta(days=1)
        if local.weekday() not in calendar.weekends and local.date().isoformat() not in calendar.holidays:
            count += 1
    return local.astimezone(timezone.utc).replace(tzinfo=None)


def distance_m(lat1, lon1, lat2, lon2):
    p1, p2 = radians(lat1), radians(lat2)
    a = sin((p2 - p1) / 2) ** 2 + cos(p1) * cos(p2) * sin(radians(lon2 - lon1) / 2) ** 2
    return 6371008.8 * 2 * asin(min(1, sqrt(a)))


def boundary_ids(db, latitude, longitude):
    if db.bind.dialect.name == "postgresql":
        rows = db.execute(
            text(
                "SELECT id FROM boundaries WHERE ST_Covers(geom, ST_SetSRID(ST_MakePoint(:lon, :lat),4326))"
            ),
            {"lon": longitude, "lat": latitude},
        )
        return set(rows.scalars())
    point = Point(longitude, latitude)
    return {boundary.id for boundary in db.scalars(select(Boundary)) if shape(boundary.geojson).covers(point)}


def nearby(db, latitude, longitude, radius, category=None, since=None):
    query = select(Complaint).where(Complaint.merged_into.is_(None))
    if category:
        query = query.where(Complaint.category == category)
    if since:
        query = query.where(Complaint.created_at >= since)
    if db.bind.dialect.name == "postgresql":
        query = query.where(
            text(
                "ST_DWithin(complaints.location, ST_SetSRID(ST_MakePoint(:lon, :lat),4326)::geography, :radius)"
            )
        ).params(lon=longitude, lat=latitude, radius=radius)
        return list(db.scalars(query.order_by(Complaint.created_at.desc()).limit(200)))
    # SQLite is a development adapter; production performs an indexed PostGIS radius query.
    return [
        c
        for c in db.scalars(query.order_by(Complaint.created_at.desc()).limit(10000))
        if distance_m(latitude, longitude, c.latitude, c.longitude) <= radius
    ][:200]


def record(db, complaint, actor_id, message):
    db.add(
        ComplaintEvent(complaint_id=complaint.id, actor_id=actor_id, status=complaint.status, message=message)
    )
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=f"complaint.{complaint.status.lower()}",
            resource_id=complaint.id,
            details={"message": message},
        )
    )
    recipients = {complaint.user_id} if complaint.user_id else set()
    if complaint.assigned_authority_id:
        recipients.update(
            db.scalars(
                select(User.id).where(
                    User.authority_id == complaint.assigned_authority_id, User.active.is_(True)
                )
            )
        )
    for user_id in recipients:
        db.add(
            Notification(
                user_id=user_id, complaint_id=complaint.id, message=f"{complaint.reference}: {message}"[:500]
            )
        )


def apply_assignment(db, complaint, authority_id, calendar, days, steps, actor_id, reason):
    authority = db.get(Authority, authority_id)
    if not authority or not authority.active:
        raise HTTPException(422, "Choose an active authority")
    complaint.assigned_authority_id = authority_id
    complaint.calendar_id = calendar.id
    complaint.deadline = working_deadline(now(), days, calendar)
    complaint.escalation_steps = steps
    complaint.escalation_level = 0
    complaint.next_escalation_at = complaint.deadline
    complaint.cycle += 1
    complaint.status = "ASSIGNED"
    record(db, complaint, actor_id, f"Assigned to {authority.name}. {reason}")


def auto_assign(db, complaint):
    boundaries = boundary_ids(db, complaint.latitude, complaint.longitude)
    for rule in db.scalars(
        select(Responsibility)
        .where(Responsibility.active.is_(True), Responsibility.category.in_([complaint.category, "*"]))
        .order_by(Responsibility.priority.desc(), Responsibility.id)
    ):
        if rule.boundary_id:
            boundary = db.get(Boundary, rule.boundary_id)
            if rule.boundary_id not in boundaries or (not boundary.verified and not settings().demo_mode):
                continue
        authority = db.get(Authority, rule.authority_id)
        if not authority or not authority.active:
            continue
        complaint.responsibility_id = rule.id
        apply_assignment(
            db,
            complaint,
            rule.authority_id,
            db.get(Calendar, rule.calendar_id),
            rule.deadline_days,
            rule.escalation_steps,
            None,
            "Configured responsibility rule matched.",
        )
        return


def accessible(complaint, user):
    return (
        user.role in ADMIN_ROLES
        or complaint.user_id == user.id
        or (
            user.role == "AUTHORITY"
            and user.authority_id
            and complaint.assigned_authority_id == user.authority_id
        )
    )


def get_complaint(db, complaint_id, user, manage=False):
    complaint = db.get(Complaint, complaint_id)
    if not complaint or not accessible(complaint, user):
        raise HTTPException(404, "Complaint not found")
    if (
        manage
        and user.role not in ADMIN_ROLES
        and not (user.role == "AUTHORITY" and user.authority_id == complaint.assigned_authority_id)
    ):
        raise HTTPException(403, "Only the assigned authority or administrator can update this complaint")
    if manage and complaint.merged_into:
        raise HTTPException(409, "This report was merged; update its linked complaint")
    return complaint


def scoped_query(user):
    query = select(Complaint)
    if user.role in ADMIN_ROLES:
        return query
    if user.role == "AUTHORITY":
        return (
            query.where(Complaint.assigned_authority_id == user.authority_id)
            if user.authority_id
            else query.where(Complaint.id == "")
        )
    return query.where(Complaint.user_id == user.id)


def run_escalations(db, at=None):
    at = at or now()
    query = (
        select(Complaint)
        .where(
            Complaint.next_escalation_at <= at,
            Complaint.status.not_in(TERMINAL),
            Complaint.merged_into.is_(None),
        )
        .with_for_update(skip_locked=True)
    )
    processed = 0
    for complaint in db.scalars(query):
        steps = complaint.escalation_steps
        if complaint.escalation_level >= len(steps):
            complaint.next_escalation_at = None
            continue
        step = steps[complaint.escalation_level]
        calendar = db.get(Calendar, complaint.calendar_id)
        complaint.escalation_level += 1
        authority_id = step.get("authority_id")
        if authority_id:
            authority = db.get(Authority, authority_id)
            if not authority or not authority.active:
                raise ValueError("Escalation rule references an inactive authority")
            complaint.assigned_authority_id = authority_id
        db.add(
            Escalation(
                complaint_id=complaint.id,
                cycle=complaint.cycle,
                level=complaint.escalation_level,
                authority_id=authority_id,
            )
        )
        complaint.next_escalation_at = (
            working_deadline(complaint.next_escalation_at, step["after_days"], calendar)
            if complaint.escalation_level < len(steps)
            else None
        )
        record(
            db,
            complaint,
            None,
            f"Escalation level {complaint.escalation_level}: "
            + ("reassigned to configured authority." if authority_id else "deadline reminder sent."),
        )
        processed += 1
    db.commit()
    return processed


def iso(value):
    return value.isoformat() + "Z" if value else None


def serialize(complaint, db, public=False):
    base = {
        "id": complaint.id,
        "reference": complaint.reference,
        "category": complaint.category,
        "status": complaint.status,
        "severity": complaint.severity,
        "latitude": round(complaint.latitude, 3) if public else complaint.latitude,
        "longitude": round(complaint.longitude, 3) if public else complaint.longitude,
    }
    if public:
        return base
    authority = (
        db.get(Authority, complaint.assigned_authority_id) if complaint.assigned_authority_id else None
    )
    return base | {
        "title": complaint.title,
        "description": complaint.description,
        "locality": complaint.locality,
        "user_id": complaint.user_id,
        "image_id": complaint.image_id,
        "created_at": iso(complaint.created_at),
        "updated_at": iso(complaint.updated_at),
        "deadline": iso(complaint.deadline),
        "escalation_level": complaint.escalation_level,
        "assigned_authority_id": complaint.assigned_authority_id,
        "assigned_authority": authority.name if authority else None,
        "resolution_description": complaint.resolution_description,
        "resolution_image_id": complaint.resolution_image_id,
        "resolved_at": iso(complaint.resolved_at),
        "resolution_latitude": complaint.resolution_latitude,
        "resolution_longitude": complaint.resolution_longitude,
        "resolved_by": complaint.resolved_by,
        "ai_prediction": complaint.ai_prediction,
        "merged_into": complaint.merged_into,
        "version": complaint.version,
    }
