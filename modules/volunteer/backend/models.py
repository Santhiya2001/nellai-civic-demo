from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, uid


class Volunteer(Base):
    __tablename__ = "volunteer_profiles"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    interests: Mapped[list] = mapped_column(JSON, default=list)
    locality: Mapped[str] = mapped_column(String(160))
    availability: Mapped[str] = mapped_column(String(300))


class Activity(Base):
    __tablename__ = "volunteer_activities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(String(2000))
    category: Mapped[str] = mapped_column(String(60))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    locality: Mapped[str] = mapped_column(String(160))
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    capacity: Mapped[int] = mapped_column(Integer)
    participants: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))


class Participation(Base):
    __tablename__ = "volunteer_participation"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    activity_id: Mapped[str] = mapped_column(ForeignKey("volunteer_activities.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    __table_args__ = (UniqueConstraint("activity_id", "user_id"),)
