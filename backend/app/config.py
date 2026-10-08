from functools import lru_cache
from pathlib import Path

from pydantic import EmailStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT / ".env"), extra="ignore")
    environment: str = "development"
    database_url: str = "sqlite:///./runtime/nellai.db"
    jwt_secret: str
    access_minutes: int = 15
    refresh_days: int = 14
    district_name: str = "Tirunelveli"
    timezone: str = "Asia/Kolkata"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080"
    upload_dir: str = str(ROOT / "runtime" / "uploads")
    max_upload_mb: int = 8
    redis_url: str = ""
    demo_mode: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_starttls: bool = True
    complaint_alert_email: EmailStr | None = None
    ai_url: str = ""
    public_url: str = "http://localhost:8080"
    retention_days: int = 365

    @field_validator("complaint_alert_email", mode="before")
    @classmethod
    def empty_alert_email(cls, value):
        return value.strip() or None if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_environment(self):
        if len(self.jwt_secret) < 32 or "CHANGE" in self.jwt_secret.upper():
            raise ValueError("JWT_SECRET must be a randomly generated secret of at least 32 characters")
        if self.environment == "production":
            if self.demo_mode or not self.database_url.startswith("postgresql"):
                raise ValueError("Production requires PostgreSQL and DEMO_MODE=false")
            if not self.redis_url or not self.public_url.startswith("https://"):
                raise ValueError("Production requires Redis and an HTTPS PUBLIC_URL")
            if any(not origin.startswith("https://") for origin in self.origins):
                raise ValueError("Production CORS origins must use HTTPS")
        return self

    @property
    def origins(self):
        return [s.strip() for s in self.cors_origins.split(",") if s.strip()]


@lru_cache
def settings():
    return Settings()
