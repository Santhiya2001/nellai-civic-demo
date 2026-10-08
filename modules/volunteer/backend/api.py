from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db import get_db, now
from app.models import AuditLog, Notification, User
from app.schemas import Coordinates, Input
from app.security import admin_user, current_user
from app.services import iso
from modules.volunteer.backend.models import Activity, Participation, Volunteer

router = APIRouter(tags=["Volunteer Nellai"])


class Profile(Input):
    skills: list[str] = Field(default=[], max_length=20)
    interests: list[str] = Field(default=[], max_length=20)
    locality: str = Field(min_length=2, max_length=160)
    availability: str = Field(min_length=2, max_length=300)


class ActivityCreate(Coordinates):
    title: str = Field(min_length=5, max_length=180)
    description: str = Field(min_length=15, max_length=2000)
    category: str = Field(min_length=2, max_length=60)
    locality: str = Field(min_length=2, max_length=160)
    starts_at: datetime
    capacity: int = Field(ge=1, le=10000)


@router.get("/volunteers/me")
def my_profile(user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.get(Volunteer, user.id)
    return (
        {"skills": p.skills, "interests": p.interests, "locality": p.locality, "availability": p.availability}
        if p
        else None
    )


@router.post("/volunteers")
def register(data: Profile, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if any(len(s) > 100 for s in data.skills + data.interests):
        raise HTTPException(422, "Each skill or interest must be at most 100 characters")
    p = db.get(Volunteer, user.id)
    if not p:
        p = Volunteer(user_id=user.id)
        db.add(p)
    for k, v in data.model_dump().items():
        setattr(p, k, v)
    if user.role == "CITIZEN":
        user.role = "VOLUNTEER"
    db.add(AuditLog(actor_id=user.id, action="volunteer.register", resource_id=user.id))
    db.commit()
    return {"registered": True}


@router.get("/volunteers")
def volunteers(user: User = Depends(admin_user), db: Session = Depends(get_db)):
    return [
        {
            "name": db.get(User, p.user_id).name,
            "skills": p.skills,
            "interests": p.interests,
            "locality": p.locality,
            "availability": p.availability,
        }
        for p in db.scalars(select(Volunteer).limit(200))
    ]


@router.get("/activities")
def activities(user: User = Depends(current_user), db: Session = Depends(get_db)):
    joined = set(db.scalars(select(Participation.activity_id).where(Participation.user_id == user.id)))
    return [
        {
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "category": a.category,
            "latitude": a.latitude,
            "longitude": a.longitude,
            "locality": a.locality,
            "starts_at": iso(a.starts_at),
            "capacity": a.capacity,
            "participants": a.participants,
            "joined": a.id in joined,
        }
        for a in db.scalars(select(Activity).order_by(Activity.starts_at).limit(200))
    ]


@router.post("/activities", status_code=201)
def create_activity(data: ActivityCreate, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    if data.starts_at.tzinfo is None:
        raise HTTPException(422, "Activity time must include a timezone offset")
    values = data.model_dump()
    values["starts_at"] = data.starts_at.astimezone(timezone.utc).replace(tzinfo=None)
    if values["starts_at"] < now():
        raise HTTPException(422, "Choose a future activity time")
    activity = Activity(**values, created_by=user.id)
    db.add(activity)
    db.flush()
    for profile in db.scalars(select(Volunteer).where(Volunteer.locality == data.locality)):
        db.add(
            Notification(user_id=profile.user_id, message=f"New activity in {data.locality}: {data.title}")
        )
    db.add(AuditLog(actor_id=user.id, action="volunteer.activity.create", resource_id=activity.id))
    db.commit()
    return {"id": activity.id}


@router.post("/activities/{activity_id}/join")
def join(activity_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not db.get(Volunteer, user.id):
        raise HTTPException(409, "Register your volunteer profile first")
    if db.scalar(
        select(Participation).where(
            Participation.user_id == user.id, Participation.activity_id == activity_id
        )
    ):
        return {"joined": True}
    result = db.execute(
        update(Activity)
        .where(
            Activity.id == activity_id, Activity.participants < Activity.capacity, Activity.starts_at > now()
        )
        .values(participants=Activity.participants + 1)
    )
    if result.rowcount != 1:
        raise HTTPException(409, "Activity is full, started, or unavailable")
    db.add(Participation(activity_id=activity_id, user_id=user.id))
    db.add(Notification(user_id=user.id, message="Your volunteer activity registration is confirmed."))
    db.commit()
    return {"joined": True}
