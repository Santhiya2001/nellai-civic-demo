import re
from datetime import date
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from shapely.geometry import shape

CATEGORIES = [
    "DRAIN_BLOCKAGE",
    "GARBAGE_DUMPING",
    "WATER_STAGNATION",
    "ROAD_DAMAGE",
    "STREETLIGHT",
    "FALLEN_TREE",
    "ILLEGAL_DUMPING",
    "LAKE_POLLUTION",
    "RIVER_POLLUTION",
    "CANAL_BLOCKAGE",
    "PUBLIC_TOILET",
    "PLASTIC_WASTE",
    "OTHER",
]
Role = Literal["CITIZEN", "VOLUNTEER", "AUTHORITY", "ADMIN", "SUPER_ADMIN", "MODULE_DEVELOPER"]
Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Register(Input):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr | None = None
    phone: str | None = None
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def email_lower(cls, v):
        return v.lower() if v else None

    @field_validator("phone")
    @classmethod
    def phone_format(cls, v):
        if v and not re.fullmatch(r"\+[1-9]\d{7,14}", v):
            raise ValueError("Use international phone format, e.g. +919876543210")
        return v

    @model_validator(mode="after")
    def contact_required(self):
        if not self.email and not self.phone:
            raise ValueError("An email address or mobile number is required")
        return self


class Login(Input):
    identifier: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class Refresh(Input):
    refresh_token: str | None = Field(default=None, max_length=2000)


class Coordinates(Input):
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)


class ComplaintCreate(Coordinates):
    title: str = Field(min_length=5, max_length=180)
    description: str = Field(min_length=15, max_length=5000)
    category: str
    image_id: str
    locality: str = Field(default="", max_length=160)

    @field_validator("category")
    @classmethod
    def valid_category(cls, v):
        if v not in CATEGORIES:
            raise ValueError("Unknown complaint category")
        return v


class Classification(Input):
    category: str
    severity: Severity
    reason: str = Field(min_length=5, max_length=1000)
    _category = field_validator("category")(ComplaintCreate.valid_category.__func__)


class Assign(Input):
    authority_id: str
    calendar_id: str
    deadline_days: int = Field(default=3, ge=1, le=90)
    reason: str = Field(min_length=5, max_length=1000)


class StatusChange(Input):
    status: Literal["ACKNOWLEDGED", "IN_PROGRESS", "REJECTED"]
    reason: str = Field(min_length=5, max_length=1000)


class Resolve(Coordinates):
    description: str = Field(min_length=15, max_length=5000)
    image_id: str


class Verify(Input):
    resolved: bool
    reason: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def rejection_reason(self):
        if not self.resolved and len(self.reason) < 5:
            raise ValueError("Explain why the issue is not resolved")
        return self


class Merge(Input):
    target_id: str
    reason: str = Field(min_length=5, max_length=1000)


class AuthorityCreate(Input):
    name: str = Field(min_length=3, max_length=160)
    department: str = Field(min_length=2, max_length=120)


class BoundaryCreate(Input):
    name: str = Field(min_length=3, max_length=160)
    geojson: dict
    source: str = Field(min_length=5, max_length=500)
    verified: bool = False

    @field_validator("geojson")
    @classmethod
    def polygon(cls, v):
        try:
            geometry = shape(v)
            if (
                geometry.geom_type not in {"Polygon", "MultiPolygon"}
                or not geometry.is_valid
                or geometry.is_empty
            ):
                raise ValueError("A valid GeoJSON Polygon or MultiPolygon is required")
            x1, y1, x2, y2 = geometry.bounds
            if x1 < -180 or x2 > 180 or y1 < -90 or y2 > 90 or len(str(v)) > 1_000_000:
                raise ValueError("Boundary coordinates or size are invalid")
        except (TypeError, KeyError, AttributeError) as exc:
            raise ValueError("Invalid GeoJSON") from exc
        return v


class CalendarCreate(Input):
    name: str = Field(min_length=2, max_length=120)
    timezone: str = "Asia/Kolkata"
    weekends: list[int] = Field(default=[5, 6], max_length=6)
    holidays: list[date] = Field(default=[], max_length=366)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, v):
        try:
            ZoneInfo(v)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Unknown time zone") from exc
        return v

    @field_validator("weekends")
    @classmethod
    def valid_weekends(cls, v):
        if len(v) != len(set(v)) or any(d not in range(7) for d in v):
            raise ValueError("Weekends must be unique values from 0 (Monday) to 6")
        return v


class EscalationStep(Input):
    after_days: int = Field(ge=1, le=90)
    authority_id: str | None = None


class ResponsibilityCreate(Input):
    category: str
    authority_id: str
    boundary_id: str | None = None
    calendar_id: str
    priority: int = Field(default=0, ge=0, le=1000)
    deadline_days: int = Field(default=3, ge=1, le=90)
    escalation_steps: list[EscalationStep] = Field(default=[], max_length=10)
    active: bool = True

    @field_validator("category")
    @classmethod
    def valid_category(cls, v):
        if v != "*" and v not in CATEGORIES:
            raise ValueError("Unknown category")
        return v


class RoleUpdate(Input):
    role: Role
    authority_id: str | None = None


class ModuleToggle(Input):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,59}$")
    enabled: bool


class DeleteAccount(Input):
    password: str = Field(max_length=128)
