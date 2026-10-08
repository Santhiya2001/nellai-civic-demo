from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, now, uid


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(254), unique=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(24), default="CITIZEN")
    authority_id: Mapped[str | None] = mapped_column(ForeignKey("authorities.id"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class LoginSession(Base):
    __tablename__ = "login_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    refresh_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class Authority(Base):
    __tablename__ = "authorities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(160))
    department: Mapped[str] = mapped_column(String(120))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Boundary(Base):
    __tablename__ = "boundaries"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(160))
    geojson: Mapped[dict] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(500))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)


class Calendar(Base):
    __tablename__ = "calendars"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(120))
    timezone: Mapped[str] = mapped_column(String(80), default="Asia/Kolkata")
    weekends: Mapped[list] = mapped_column(JSON, default=lambda: [5, 6])
    holidays: Mapped[list] = mapped_column(JSON, default=list)


class Responsibility(Base):
    __tablename__ = "responsibilities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    category: Mapped[str] = mapped_column(String(60))
    authority_id: Mapped[str] = mapped_column(ForeignKey("authorities.id"))
    boundary_id: Mapped[str | None] = mapped_column(ForeignKey("boundaries.id"))
    calendar_id: Mapped[str] = mapped_column(ForeignKey("calendars.id"))
    priority: Mapped[int] = mapped_column(Integer, default=0)
    deadline_days: Mapped[int] = mapped_column(Integer, default=3)
    # Each level has after_days (relative to the last deadline), authority_id or null for reminder.
    escalation_steps: Mapped[list] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Upload(Base):
    __tablename__ = "uploads"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    filename: Mapped[str] = mapped_column(String(80))
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Complaint(Base):
    __tablename__ = "complaints"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    reference: Mapped[str] = mapped_column(String(20), unique=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(60), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    locality: Mapped[str] = mapped_column(String(160), default="")
    image_id: Mapped[str | None] = mapped_column(ForeignKey("uploads.id"))
    severity: Mapped[str] = mapped_column(String(16), default="MEDIUM")
    status: Mapped[str] = mapped_column(String(24), default="REPORTED", index=True)
    assigned_authority_id: Mapped[str | None] = mapped_column(ForeignKey("authorities.id"), index=True)
    responsibility_id: Mapped[str | None] = mapped_column(ForeignKey("responsibilities.id"))
    calendar_id: Mapped[str | None] = mapped_column(ForeignKey("calendars.id"))
    deadline: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    next_escalation_at: Mapped[datetime | None] = mapped_column(DateTime)
    escalation_steps: Mapped[list] = mapped_column(JSON, default=list)
    escalation_level: Mapped[int] = mapped_column(Integer, default=0)
    cycle: Mapped[int] = mapped_column(Integer, default=0)
    resolution_description: Mapped[str | None] = mapped_column(Text)
    resolution_image_id: Mapped[str | None] = mapped_column(ForeignKey("uploads.id"))
    resolved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    resolution_latitude: Mapped[float | None] = mapped_column(Float)
    resolution_longitude: Mapped[float | None] = mapped_column(Float)
    ai_prediction: Mapped[dict | None] = mapped_column(JSON)
    merged_into: Mapped[str | None] = mapped_column(ForeignKey("complaints.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {"version_id_col": version}
    __table_args__ = (Index("ix_complaint_coordinates", "latitude", "longitude"),)


class ComplaintEvent(Base):
    __tablename__ = "complaint_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    complaint_id: Mapped[str] = mapped_column(ForeignKey("complaints.id"), index=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(24))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Escalation(Base):
    __tablename__ = "escalations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    complaint_id: Mapped[str] = mapped_column(ForeignKey("complaints.id"))
    cycle: Mapped[int] = mapped_column(Integer)
    level: Mapped[int] = mapped_column(Integer)
    authority_id: Mapped[str | None] = mapped_column(ForeignKey("authorities.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (UniqueConstraint("complaint_id", "cycle", "level"),)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    message: Mapped[str] = mapped_column(String(500))
    complaint_id: Mapped[str | None] = mapped_column(ForeignKey("complaints.id"))
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    email_state: Mapped[str] = mapped_column(String(16), default="PENDING")
    email_attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ComplaintEmail(Base):
    """One durable authority alert per new complaint, independent of user accounts."""

    __tablename__ = "complaint_emails"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    complaint_id: Mapped[str] = mapped_column(ForeignKey("complaints.id"))
    recipient: Mapped[str] = mapped_column(String(254))
    state: Mapped[str] = mapped_column(String(16), default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (
        UniqueConstraint("complaint_id", "recipient", name="uq_complaint_email_recipient"),
        Index("ix_complaint_emails_pending", "state", "next_attempt_at"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80))
    resource_id: Mapped[str] = mapped_column(String(80))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ModuleRecord(Base):
    __tablename__ = "module_registry"
    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    version: Mapped[str] = mapped_column(String(30))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
