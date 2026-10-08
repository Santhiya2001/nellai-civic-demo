from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AuditLog, User
from app.schemas import Coordinates, Input
from app.security import admin_user, current_user
from app.services import iso
from modules.water.backend.models import Observation, WaterBody

router = APIRouter(tags=["Neervalam"])


class BodyCreate(Coordinates):
    name: str = Field(min_length=3, max_length=160)
    kind: Literal["RIVER", "LAKE", "POND", "CANAL", "WELL", "TANK", "WETLAND"]
    source: str = Field(min_length=5, max_length=300)


class ObservationCreate(Input):
    kind: Literal["POLLUTION", "GARBAGE", "ENCROACHMENT", "BLOCKAGE", "LOW_LEVEL", "DAMAGE", "GENERAL"]
    description: str = Field(min_length=15, max_length=2000)


@router.get("/water-bodies")
def bodies(db: Session = Depends(get_db)):
    return [
        {
            "id": w.id,
            "name": w.name,
            "kind": w.kind,
            "latitude": w.latitude,
            "longitude": w.longitude,
            "source": w.source,
        }
        for w in db.scalars(select(WaterBody).limit(1000))
    ]


@router.post("/water-bodies", status_code=201)
def create_body(data: BodyCreate, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    body = WaterBody(**data.model_dump())
    db.add(body)
    db.flush()
    db.add(AuditLog(actor_id=user.id, action="water.body.create", resource_id=body.id))
    db.commit()
    return {"id": body.id}


@router.post("/water-bodies/{body_id}/observations", status_code=201)
def observe(
    body_id: str, data: ObservationCreate, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    if not db.get(WaterBody, body_id):
        raise HTTPException(404, "Water body not found")
    observation = Observation(water_body_id=body_id, user_id=user.id, **data.model_dump())
    db.add(observation)
    db.flush()
    db.add(AuditLog(actor_id=user.id, action="water.observation.create", resource_id=observation.id))
    db.commit()
    return {"id": observation.id, "status": "UNVERIFIED_COMMUNITY_OBSERVATION"}


@router.get("/water-bodies/{body_id}/observations")
def observations(body_id: str, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    return [
        {"id": o.id, "kind": o.kind, "description": o.description, "created_at": iso(o.created_at)}
        for o in db.scalars(select(Observation).where(Observation.water_body_id == body_id).limit(200))
    ]
