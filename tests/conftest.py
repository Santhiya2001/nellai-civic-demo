import os
import secrets
import tempfile

TEST_DIR = tempfile.TemporaryDirectory(prefix="nellai-tests-")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{TEST_DIR.name}/test.db")
os.environ["JWT_SECRET"] = secrets.token_urlsafe(48)
os.environ["UPLOAD_DIR"] = TEST_DIR.name + "/uploads"
os.environ["DEMO_MODE"] = "false"
os.environ["REDIS_URL"] = ""
os.environ["ENVIRONMENT"] = "test"
os.environ["SMTP_HOST"] = ""
os.environ["SMTP_USER"] = ""
os.environ["SMTP_PASSWORD"] = ""
os.environ["SMTP_FROM"] = ""
os.environ["COMPLAINT_ALERT_EMAIL"] = ""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import Base, SessionLocal, engine
from app.main import app, local_limits
from app.modules import synchronize


@pytest.fixture(autouse=True)
def database():
    Base.metadata.create_all(engine)
    if engine.dialect.name == "postgresql":
        with engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            connection.execute(
                text(
                    "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS location geography(Point,4326) GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(longitude,latitude),4326)::geography) STORED"
                )
            )
            connection.execute(
                text(
                    "ALTER TABLE boundaries ADD COLUMN IF NOT EXISTS geom geometry(Geometry,4326) GENERATED ALWAYS AS (ST_SetSRID(ST_GeomFromGeoJSON(geojson::text),4326)) STORED"
                )
            )
    with SessionLocal() as db:
        synchronize(db)
    local_limits.clear()
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client
