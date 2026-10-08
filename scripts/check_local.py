"""Read-only deployment smoke checks, plus short-lived logins for demo accounts."""

import json
import os
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
with httpx.Client(base_url=os.environ.get("NELLAI_DEMO_URL", "http://localhost:8080"), timeout=15) as client:
    for path in [
        "/",
        "/health",
        "/docs",
        "/openapi.json",
        "/privacy.html",
        "/terms.html",
        "/api/v1/config",
        "/api/v1/map",
        "/api/v1/modules",
    ]:
        response = client.get(path)
        response.raise_for_status()
        print(f"OK {path}")
    credentials = json.loads((ROOT / "runtime/demo-credentials.json").read_text())
    for account in credentials:
        response = client.post(
            "/api/v1/auth/login", json={"identifier": account["email"], "password": account["password"]}
        )
        response.raise_for_status()
        tokens = response.json()
        headers = {"Authorization": "Bearer " + tokens["access_token"]}
        profile = client.get("/api/v1/auth/me", headers=headers)
        profile.raise_for_status()
        assert profile.json()["role"] == account["role"]
        records = client.get("/api/v1/complaints", headers=headers)
        records.raise_for_status()
        if records.json() and records.json()[0].get("image_id"):
            client.get("/api/v1/uploads/" + records.json()[0]["image_id"], headers=headers).raise_for_status()
        client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}).raise_for_status()
        print(f"OK {account['role']} login, records and logout")
print("Local demo is ready.")
