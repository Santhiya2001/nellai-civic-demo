import importlib

from fastapi import APIRouter, Depends
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AuditLog, User
from app.schemas import Input
from app.security import admin_user, current_user
from app.services import iso

GaugeReading = importlib.import_module("modules.flood-monitoring.backend.models").GaugeReading
router = APIRouter(prefix="/flood-monitoring", tags=["Community: flood monitoring"])


class Reading(Input):
    station: str = Field(min_length=3, max_length=160)
    level_m: float = Field(ge=0, le=100, allow_inf_nan=False)
    source: str = Field(min_length=5, max_length=300)


@router.get("/readings")
def readings(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [
        {
            "id": r.id,
            "station": r.station,
            "level_m": r.level_m,
            "source": r.source,
            "created_at": iso(r.created_at),
        }
        for r in db.scalars(select(GaugeReading).order_by(GaugeReading.created_at.desc()).limit(100))
    ]


@router.post("/readings", status_code=201)
def create_reading(data: Reading, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    row = GaugeReading(**data.model_dump(), recorded_by=user.id)
    db.add(row)
    db.flush()
    db.add(AuditLog(actor_id=user.id, action="flood.reading.create", resource_id=row.id))
    db.commit()
    return {"id": row.id}
