"""Generate private local configuration. Never overwrite an existing .env."""

import argparse
import os
from pathlib import Path
import secrets

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--docker", action="store_true")
parser.add_argument("--demo", action="store_true")
args = parser.parse_args()
path = root / ".env"
if path.exists():
    raise SystemExit(".env already exists; edit it explicitly instead of replacing secrets.")
password = secrets.token_urlsafe(32)
body = (
    (root / ".env.example")
    .read_text()
    .replace("CHANGE_TO_A_RANDOM_SECRET_AT_LEAST_32_CHARACTERS", secrets.token_urlsafe(48))
    .replace("POSTGRES_PASSWORD=\n", f"POSTGRES_PASSWORD={password}\n")
)
if args.demo:
    body = body.replace("DEMO_MODE=false", "DEMO_MODE=true")
if args.docker:
    body = body.replace(
        "sqlite:///./runtime/nellai.db", f"postgresql+psycopg://nellai:{password}@db:5432/nellai"
    ).replace("REDIS_URL=\n", "REDIS_URL=redis://redis:6379/0\n")
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as handle:
    handle.write(body)
print("Created private .env with generated secrets.")
