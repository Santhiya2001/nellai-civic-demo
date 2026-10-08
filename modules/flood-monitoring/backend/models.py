from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, now, uid


class GaugeReading(Base):
    __tablename__ = "flood_gauge_readings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    station: Mapped[str] = mapped_column(String(160))
    level_m: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(300))
    recorded_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
