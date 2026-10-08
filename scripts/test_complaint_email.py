"""Submit one labelled local demo complaint and inspect its authority email status.

Repeated runs reuse the saved test complaint instead of creating more reports.
Actual email delivery is performed by the running application worker.
"""

import json
from pathlib import Path
import sys

import httpx
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT)]

from app.config import settings
from app.db import SessionLocal
from app.models import ComplaintEmail
from app.modules import import_models


def main():
    cfg = settings()
    marker = ROOT / "runtime/complaint-email-test.json"
    if marker.exists():
        complaint = json.loads(marker.read_text())
    else:
        credentials = json.loads((ROOT / "runtime/demo-credentials.json").read_text())
        citizen = next(account for account in credentials if account["role"] == "CITIZEN")
        with httpx.Client(base_url=cfg.public_url, timeout=30) as client:
            client.get("/health").raise_for_status()
            login = client.post(
                "/api/v1/auth/login", json={"identifier": citizen["email"], "password": citizen["password"]}
            )
            login.raise_for_status()
            tokens = login.json()
            headers = {"Authorization": "Bearer " + tokens["access_token"]}
            try:
                with (ROOT / "tests/fixtures/evidence.png").open("rb") as photo:
                    upload = client.post(
                        "/api/v1/uploads",
                        headers=headers,
                        files={"file": ("demo-evidence.png", photo, "image/png")},
                    )
                upload.raise_for_status()
                response = client.post(
                    "/api/v1/complaints",
                    headers=headers,
                    json={
                        "title": "EMAIL DELIVERY TEST: demo drain complaint",
                        "description": (
                            "TEST ONLY: This complaint was submitted by the project owner to verify "
                            "automatic authority email notifications. Example: a blocked drain near "
                            "a bus stop. No real civic incident is being reported and no field action is required."
                        ),
                        "category": "DRAIN_BLOCKAGE",
                        "locality": "Demonstration location only",
                        "latitude": 8.72,
                        "longitude": 77.741,
                        "image_id": upload.json()["id"],
                    },
                )
                response.raise_for_status()
                data = response.json()
                complaint = {key: data[key] for key in ("id", "reference", "title")}
                marker.write_text(json.dumps(complaint, indent=2) + "\n")
                marker.chmod(0o600)
            finally:
                client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    print("Complaint:", complaint["reference"])
    print("Title:", complaint["title"])
    print("Open:", f"{cfg.public_url.rstrip('/')}/#complaints/{complaint['id']}")
    import_models()
    with SessionLocal() as db:
        alert = db.scalar(select(ComplaintEmail).where(ComplaintEmail.complaint_id == complaint["id"]))
        if alert is None:
            print("No authority email was queued. Check COMPLAINT_ALERT_EMAIL and restart the app.")
            return
        print("Recipient:", alert.recipient)
        print("Email state:", alert.state)
        print("Delivery attempts:", alert.attempts)
        if not cfg.smtp_host or not cfg.smtp_from:
            print("SMTP is not configured. The email is queued but has not been sent.")
        elif alert.state == "SENT":
            print("The SMTP server accepted the email. Check your inbox and spam folder.")
        elif alert.state == "PENDING":
            print("Waiting for the worker. Restart the app if you recently changed its email settings.")
        elif alert.state == "FAILED":
            print("Delivery failed after retries. Check the sending account settings and worker log.")


if __name__ == "__main__":
    main()
