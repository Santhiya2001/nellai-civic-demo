"""Run migrations and tests in a newly created, disposable PostGIS database."""

import os
from pathlib import Path
import secrets
import subprocess
import sys

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import settings

url = settings().database_url
if not url.startswith("postgresql+psycopg:"):
    raise SystemExit("Configure a local PostgreSQL database first.")
admin_url = url.replace("postgresql+psycopg:", "postgresql:").rsplit("/", 1)[0] + "/postgres"
name = "nellai_test_" + secrets.token_hex(5)
test_url = url.rsplit("/", 1)[0] + "/" + name
env = os.environ | {
    "DATABASE_URL": test_url,
    "TEST_DATABASE_URL": test_url,
    "ENVIRONMENT": "test",
    "DEMO_MODE": "false",
    "REDIS_URL": "",
}
with psycopg.connect(admin_url, autocommit=True) as admin:
    admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT, env=env, check=True)
        with psycopg.connect(test_url.replace("postgresql+psycopg:", "postgresql:")) as db:
            assert (
                db.execute(
                    "SELECT count(*) FROM pg_indexes WHERE indexname IN ('ix_complaints_location_gist','ix_boundaries_geom_gist')"
                ).fetchone()[0]
                == 2
            )
            print("PostGIS migrations and both spatial indexes verified.", flush=True)
        subprocess.run(
            [sys.executable, "-m", "pytest", "--junitxml=runtime/test-results-postgis.xml"],
            cwd=ROOT,
            env=env,
            check=True,
        )
    finally:
        admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
