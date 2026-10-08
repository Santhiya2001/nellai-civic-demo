from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db, now
from app.mail import complaint_alert_message
from app.models import (
    AuditLog,
    Authority,
    Boundary,
    Calendar,
    Complaint,
    ComplaintEmail,
    ModuleRecord,
    Notification,
    Responsibility,
    User,
)
from app.modules import installed_manifests
from app.schemas import (
    AuthorityCreate,
    BoundaryCreate,
    CalendarCreate,
    ModuleToggle,
    ResponsibilityCreate,
    RoleUpdate,
)
from app.security import admin_user, current_user, roles
from app.services import TERMINAL, boundary_ids, iso, run_escalations, scoped_query, serialize

router = APIRouter(tags=["Platform"])


def row_dict(row):
    return {
        column.name: iso(getattr(row, column.name))
        if column.name.endswith("_at")
        else getattr(row, column.name)
        for column in row.__table__.columns
    }


@router.get("/config")
def config():
    from app.schemas import CATEGORIES

    return {
        "name": "Nellai Green & Civic",
        "district": settings().district_name,
        "demo_mode": settings().demo_mode,
        "categories": CATEGORIES,
        "version": "0.1.0",
        "ai_enabled": bool(settings().ai_url),
        "max_upload_mb": settings().max_upload_mb,
    }


@router.get("/dashboard")
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db)):
    complaints = list(db.scalars(scoped_query(user)))
    closed = [c for c in complaints if c.status == "CLOSED"]
    durations = [(c.resolved_at - c.created_at).total_seconds() / 3600 for c in closed if c.resolved_at]
    metrics = {
        "total": len(complaints),
        "open": sum(c.status not in TERMINAL for c in complaints),
        "resolved": len(closed),
        "awaiting_verification": sum(c.status == "VERIFICATION" for c in complaints),
        "overdue": sum(
            c.deadline is not None and c.deadline < now() and c.status not in TERMINAL and not c.merged_into
            for c in complaints
        ),
        "escalated": sum(c.escalation_level > 0 for c in complaints),
        "high_severity": sum(c.severity in {"HIGH", "CRITICAL"} for c in complaints),
        "average_resolution_hours": round(sum(durations) / len(durations), 1) if durations else None,
        "by_category": dict(Counter(c.category for c in complaints)),
        "by_status": dict(Counter(c.status for c in complaints)),
        "by_month": dict(sorted(Counter(c.created_at.strftime("%Y-%m") for c in complaints).items())),
        "by_locality": dict(Counter(c.locality or "Unspecified" for c in complaints)),
        "trees": 0,
        "survival_rate": None,
        "volunteers": 0,
    }
    installed = installed_manifests()
    if "green" in installed and (m := db.get(ModuleRecord, "green")) and m.enabled:
        from modules.green.backend.models import Tree

        trees = list(db.scalars(select(Tree)))
        metrics["trees"] = len(trees)
        # Only inspected trees enter the survival denominator; new plantings are unknown.
        inspected = [t for t in trees if t.status != "PLANTED"]
        metrics["survival_rate"] = (
            round(
                100
                * sum(t.status in {"HEALTHY", "NEEDS_MAINTENANCE", "DAMAGED"} for t in inspected)
                / len(inspected),
                1,
            )
            if inspected
            else None
        )
    if "volunteer" in installed and (m := db.get(ModuleRecord, "volunteer")) and m.enabled:
        from modules.volunteer.backend.models import Volunteer

        metrics["volunteers"] = len(list(db.scalars(select(Volunteer.user_id))))
    return metrics


@router.get("/map")
def map_data(db: Session = Depends(get_db)):
    complaints = db.scalars(
        select(Complaint)
        .where(Complaint.merged_into.is_(None))
        .order_by(Complaint.created_at.desc())
        .limit(1000)
    )
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [round(c.longitude, 3), round(c.latitude, 3)]},
                "properties": serialize(c, db, public=True),
            }
            for c in complaints
        ],
        "privacy": "Coordinates rounded to 3 decimals; no citizen identity, descriptions or photos.",
        "limit": 1000,
    }


@router.get("/boundaries")
def list_boundaries(db: Session = Depends(get_db)):
    return [row_dict(b) for b in db.scalars(select(Boundary))]


@router.get("/boundaries/lookup")
def lookup(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    db: Session = Depends(get_db),
):
    ids = boundary_ids(db, latitude, longitude)
    return [row_dict(db.get(Boundary, i)) for i in ids]


@router.post("/boundaries", status_code=201)
def create_boundary(data: BoundaryCreate, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    row = Boundary(**data.model_dump())
    db.add(row)
    db.flush()
    db.add(AuditLog(actor_id=user.id, action="boundary.create", resource_id=row.id))
    db.commit()
    return row_dict(row)


@router.get("/authorities")
def authorities(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [row_dict(a) for a in db.scalars(select(Authority).order_by(Authority.name))]


@router.post("/authorities", status_code=201)
def create_authority(data: AuthorityCreate, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    row = Authority(**data.model_dump())
    db.add(row)
    db.flush()
    db.add(AuditLog(actor_id=user.id, action="authority.create", resource_id=row.id))
    db.commit()
    return row_dict(row)


@router.get("/calendars")
def calendars(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [row_dict(c) for c in db.scalars(select(Calendar))]


@router.post("/calendars", status_code=201)
def create_calendar(data: CalendarCreate, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    row = Calendar(**data.model_dump(mode="json"))
    db.add(row)
    db.flush()
    db.add(AuditLog(actor_id=user.id, action="calendar.create", resource_id=row.id))
    db.commit()
    return row_dict(row)


@router.get("/responsibilities")
def responsibilities(user: User = Depends(admin_user), db: Session = Depends(get_db)):
    return [row_dict(r) for r in db.scalars(select(Responsibility))]


def check_rule(data, db):
    if not db.get(Authority, data.authority_id) or not db.get(Calendar, data.calendar_id):
        raise HTTPException(422, "Authority or calendar does not exist")
    if data.boundary_id and not db.get(Boundary, data.boundary_id):
        raise HTTPException(422, "Boundary does not exist")
    for step in data.escalation_steps:
        if step.authority_id and not db.get(Authority, step.authority_id):
            raise HTTPException(422, "Escalation authority does not exist")


@router.post("/responsibilities", status_code=201)
def create_responsibility(
    data: ResponsibilityCreate, user: User = Depends(admin_user), db: Session = Depends(get_db)
):
    check_rule(data, db)
    row = Responsibility(**data.model_dump())
    db.add(row)
    db.flush()
    db.add(AuditLog(actor_id=user.id, action="responsibility.create", resource_id=row.id))
    db.commit()
    return row_dict(row)


@router.put("/responsibilities/{rule_id}")
def update_rule(
    rule_id: str, data: ResponsibilityCreate, user: User = Depends(admin_user), db: Session = Depends(get_db)
):
    row = db.get(Responsibility, rule_id)
    if not row:
        raise HTTPException(404, "Rule not found")
    check_rule(data, db)
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    db.add(AuditLog(actor_id=user.id, action="responsibility.update", resource_id=row.id))
    db.commit()
    return row_dict(row)


@router.post("/escalations/run")
def escalate(user: User = Depends(admin_user), db: Session = Depends(get_db)):
    return {"processed": run_escalations(db)}


@router.get("/users")
def users(offset: int = Query(0, ge=0), user: User = Depends(admin_user), db: Session = Depends(get_db)):
    return [
        {"id": u.id, "name": u.name, "role": u.role, "authority_id": u.authority_id, "active": u.active}
        for u in db.scalars(select(User).order_by(User.created_at).offset(offset).limit(200))
    ]


@router.put("/users/{user_id}/role")
def update_role(
    user_id: str, data: RoleUpdate, user: User = Depends(roles("SUPER_ADMIN")), db: Session = Depends(get_db)
):
    target = db.get(User, user_id)
    if not target or not target.active:
        raise HTTPException(404, "User not found")
    if target.id == user.id:
        raise HTTPException(409, "A super administrator cannot change their own role")
    if data.role == "AUTHORITY" and not db.get(Authority, data.authority_id or ""):
        raise HTTPException(422, "An authority user must belong to an existing authority")
    target.role = data.role
    target.authority_id = data.authority_id if data.role == "AUTHORITY" else None
    db.add(AuditLog(actor_id=user.id, action="user.role", resource_id=user_id, details=data.model_dump()))
    db.commit()
    return {"id": target.id, "role": target.role}


@router.get("/modules")
def modules(db: Session = Depends(get_db)):
    return [
        manifest | {"enabled": bool(record.enabled) if (record := db.get(ModuleRecord, mid)) else False}
        for mid, manifest in installed_manifests().items()
    ]


@router.post("/modules")
def toggle_module(data: ModuleToggle, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    manifests = installed_manifests()
    row = db.get(ModuleRecord, data.id)
    if not row or data.id not in manifests:
        raise HTTPException(404, "Module must be installed from reviewed source code first")
    if data.enabled:
        for dep in manifests[data.id].get("dependencies", []):
            if not db.get(ModuleRecord, dep).enabled:
                raise HTTPException(409, f"Enable dependency {dep} first")
    else:
        for mid, manifest in manifests.items():
            if data.id in manifest.get("dependencies", []) and db.get(ModuleRecord, mid).enabled:
                raise HTTPException(409, f"Disable dependent module {mid} first")
    row.enabled = data.enabled
    db.add(
        AuditLog(
            actor_id=user.id, action="module.toggle", resource_id=data.id, details={"enabled": data.enabled}
        )
    )
    db.commit()
    return {"id": row.id, "enabled": row.enabled}


@router.get("/notifications")
def notifications(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [
        row_dict(n)
        for n in db.scalars(
            select(Notification)
            .where(Notification.user_id == user.id)
            .order_by(Notification.created_at.desc())
            .limit(100)
        )
    ]


@router.post("/notifications/{notification_id}/read", status_code=204)
def read_notification(
    notification_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    row = db.get(Notification, notification_id)
    if not row or row.user_id != user.id:
        raise HTTPException(404, "Notification not found")
    row.read = True
    db.commit()


@router.get("/audit-logs")
def audit_logs(offset: int = Query(0, ge=0), user: User = Depends(admin_user), db: Session = Depends(get_db)):
    return [
        row_dict(row)
        for row in db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(100))
    ]


@router.get("/complaint-emails")
def complaint_emails(user: User = Depends(admin_user), db: Session = Depends(get_db)):
    cfg = settings()
    counts = dict(db.execute(select(ComplaintEmail.state, func.count()).group_by(ComplaintEmail.state)).all())
    rows = db.scalars(select(ComplaintEmail).order_by(ComplaintEmail.created_at.desc()).limit(100))
    messages = []
    for alert in rows:
        complaint = db.get(Complaint, alert.complaint_id)
        messages.append({
            "id": alert.id,
            "complaint_id": complaint.id,
            "reference": complaint.reference,
            "title": complaint.title,
            "recipient": alert.recipient,
            "state": alert.state,
            "attempts": alert.attempts,
            "created_at": iso(alert.created_at),
            "sent_at": iso(alert.sent_at),
            **complaint_alert_message(db, cfg, complaint),
        })
    return {
        "recipient": cfg.complaint_alert_email,
        "delivery_configured": bool(
            cfg.smtp_host and cfg.smtp_from and (not cfg.smtp_user or cfg.smtp_password)
        ),
        "counts": {state: counts.get(state, 0) for state in ("PENDING", "SENT", "FAILED")},
        "messages": messages,
    }
