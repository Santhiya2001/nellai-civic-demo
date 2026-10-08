from datetime import date

from sqlalchemy import Date, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, uid


class PlantingSite(Base):
    __tablename__ = "green_planting_sites"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(160))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    ownership_status: Mapped[str] = mapped_column(String(24), default="UNVERIFIED")
    verification_reference: Mapped[str | None] = mapped_column(Text)
    verified_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    capacity: Mapped[int] = mapped_column(default=0)


class Tree(Base):
    __tablename__ = "green_trees"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    species: Mapped[str] = mapped_column(String(160))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    planting_date: Mapped[date] = mapped_column(Date)
    organization: Mapped[str] = mapped_column(String(160), default="")
    volunteer_group: Mapped[str] = mapped_column(String(160), default="")
    status: Mapped[str] = mapped_column(String(24), default="PLANTED")
    maintenance_date: Mapped[date | None] = mapped_column(Date)
    image_id: Mapped[str | None] = mapped_column(ForeignKey("uploads.id"))
    site_id: Mapped[str | None] = mapped_column(ForeignKey("green_planting_sites.id"))
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
