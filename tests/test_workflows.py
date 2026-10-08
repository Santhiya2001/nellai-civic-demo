from datetime import datetime, timedelta
from io import BytesIO
import secrets

from PIL import Image
from sqlalchemy import select

from app.db import SessionLocal, now
from app.models import Calendar, Complaint, Escalation, User
from app.services import working_deadline


def account(client, name="Citizen", role="CITIZEN", authority_id=None):
    email = secrets.token_hex(5) + "@example.com"
    password = secrets.token_urlsafe(16)
    response = client.post("/api/v1/auth/register", json={"name": name, "email": email, "password": password})
    assert response.status_code == 201, response.text
    user_id = response.json()["id"]
    if role != "CITIZEN":
        with SessionLocal() as db:
            user = db.get(User, user_id)
            user.role = role
            user.authority_id = authority_id
            db.commit()
    login = client.post("/api/v1/auth/login", json={"identifier": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": "Bearer " + login.json()["access_token"]}, user_id, login.json(), password


def photograph(client, headers):
    out = BytesIO()
    Image.new("RGB", (50, 50), "green").save(out, "JPEG")
    response = client.post(
        "/api/v1/uploads", files={"file": ("evidence.jpg", out.getvalue(), "image/jpeg")}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create(client, headers, image=None):
    return client.post(
        "/api/v1/complaints",
        json={
            "title": "Blocked drain near market",
            "description": "A blocked drain requires cleaning near the public market.",
            "category": "DRAIN_BLOCKAGE",
            "latitude": 8.72,
            "longitude": 77.74,
            "image_id": image or photograph(client, headers),
        },
        headers=headers,
    )


def setup_authority(client, admin):
    authority = client.post(
        "/api/v1/authorities",
        json={"name": "Configured test team", "department": "Test maintenance"},
        headers=admin,
    ).json()
    calendar = client.post(
        "/api/v1/calendars",
        json={"name": "Weekday calendar", "weekends": [5, 6], "holidays": ["2026-09-21"]},
        headers=admin,
    ).json()
    r = client.post(
        "/api/v1/responsibilities",
        json={
            "category": "*",
            "authority_id": authority["id"],
            "calendar_id": calendar["id"],
            "deadline_days": 3,
            "escalation_steps": [
                {"after_days": 1, "authority_id": None},
                {"after_days": 1, "authority_id": authority["id"]},
            ],
        },
        headers=admin,
    )
    assert r.status_code == 201, r.text
    return authority["id"], calendar["id"]


def test_end_to_end_assignment_escalation_resolution_reopen(client):
    admin, _, _, _ = account(client, "Admin", "SUPER_ADMIN")
    team, _ = setup_authority(client, admin)
    officer, _, _, _ = account(client, "Officer", "AUTHORITY", team)
    citizen, _, _, _ = account(client)
    response = create(client, citizen)
    assert response.status_code == 201, response.text
    complaint = response.json()
    cid = complaint["id"]
    assert complaint["status"] == "ASSIGNED" and complaint["deadline"]
    with SessionLocal() as db:
        c = db.get(Complaint, cid)
        c.deadline = now() - timedelta(days=5)
        c.next_escalation_at = c.deadline
        db.commit()
    assert client.post("/api/v1/escalations/run", headers=admin).json()["processed"] == 1
    assert client.post("/api/v1/escalations/run", headers=admin).json()["processed"] == 1
    assert client.post("/api/v1/escalations/run", headers=admin).json()["processed"] == 0
    with SessionLocal() as db:
        assert len(list(db.scalars(select(Escalation)))) == 2
    for status in ["ACKNOWLEDGED", "IN_PROGRESS"]:
        assert (
            client.post(
                f"/api/v1/complaints/{cid}/status",
                json={"status": status, "reason": "Work order is being handled."},
                headers=officer,
            ).status_code
            == 200
        )
    assert (
        client.post(
            f"/api/v1/complaints/{cid}/resolve",
            json={
                "description": "Drain cleared and water flow restored.",
                "image_id": photograph(client, officer),
                "latitude": 8.72,
                "longitude": 77.74,
            },
            headers=officer,
        ).json()["status"]
        == "VERIFICATION"
    )
    assert (
        client.post(f"/api/v1/complaints/{cid}/verify", json={"resolved": True}, headers=admin).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/complaints/{cid}/verify",
            json={"resolved": False, "reason": "The drain is still blocked."},
            headers=citizen,
        ).json()["status"]
        == "IN_PROGRESS"
    )
    assert (
        client.post(
            f"/api/v1/complaints/{cid}/resolve",
            json={
                "description": "Second visit completed; obstruction removed.",
                "image_id": photograph(client, officer),
                "latitude": 8.72,
                "longitude": 77.74,
            },
            headers=officer,
        ).status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/complaints/{cid}/verify", json={"resolved": True}, headers=citizen).json()[
            "status"
        ]
        == "CLOSED"
    )
    detail = client.get(f"/api/v1/complaints/{cid}", headers=citizen).json()
    assert len(detail["history"]) >= 10
    assert client.get("/api/v1/notifications", headers=citizen).json()


def test_privacy_permissions_and_private_uploads(client):
    owner, _, _, _ = account(client)
    other, _, _, _ = account(client, "Other")
    complaint = create(client, owner).json()
    cid = complaint["id"]
    assert client.get(f"/api/v1/complaints/{cid}", headers=other).status_code == 404
    assert client.get("/api/v1/complaints", headers=other).json() == []
    assert client.get("/api/v1/uploads/" + complaint["image_id"], headers=other).status_code == 404
    assert client.get("/api/v1/uploads/" + complaint["image_id"]).status_code == 401
    assert client.get("/api/v1/uploads/" + complaint["image_id"], headers=owner).status_code == 200
    assert (
        client.post(
            "/api/v1/authorities", json={"name": "Forged authority", "department": "Xx"}, headers=other
        ).status_code
        == 403
    )
    public = client.get("/api/v1/map").json()["features"][0]["properties"]
    assert not {"email", "phone", "user_id", "description", "image_id", "title"} & public.keys()
    assert create(client, other, complaint["image_id"]).status_code == 422


def test_refresh_rotation_replay_and_logout(client):
    headers, _, tokens, _ = account(client)
    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert rotated.status_code == 200
    assert (
        client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code
        == 401
    )
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/refresh", headers={"Origin": "https://attacker.example"}, json={}
        ).status_code
        == 403
    )


def test_validation_and_forbidden_self_promotion(client):
    assert (
        client.post(
            "/api/v1/auth/register",
            json={
                "name": "Attacker",
                "email": "a@example.com",
                "password": secrets.token_urlsafe(16),
                "role": "SUPER_ADMIN",
            },
        ).status_code
        == 422
    )
    headers, _, _, _ = account(client)
    assert (
        client.post(
            "/api/v1/uploads", headers=headers, files={"file": ("x.jpg", b"not an image", "image/jpeg")}
        ).status_code
        == 415
    )
    assert (
        client.post(
            "/api/v1/uploads", headers=headers, files={"file": ("x.svg", b"<svg/>", "image/svg+xml")}
        ).status_code
        == 415
    )
    assert client.post("/api/v1/calendars", headers=headers, json={"name": "Forged"}).status_code == 403


def test_working_days_holidays_timezone():
    calendar = Calendar(timezone="Asia/Kolkata", weekends=[5, 6], holidays=["2026-09-21"])
    assert working_deadline(datetime(2026, 9, 18, 10), 1, calendar) == datetime(2026, 9, 22, 10)
    assert working_deadline(datetime(2026, 9, 18, 10), 3, calendar) == datetime(2026, 9, 24, 10)


def test_module_disable_and_core_independence(client):
    admin, _, _, _ = account(client, "Admin", "SUPER_ADMIN")
    modules = client.get("/api/v1/modules").json()
    assert "flood-monitoring" in {m["id"] for m in modules}
    assert client.get("/api/v1/flood-monitoring/readings", headers=admin).status_code == 404
    assert (
        client.post(
            "/api/v1/modules", json={"id": "flood-monitoring", "enabled": True}, headers=admin
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/flood-monitoring/readings",
            json={"station": "Test station", "level_m": 1.2, "source": "Manual test measurement"},
            headers=admin,
        ).status_code
        == 201
    )
    for m in modules:
        assert (
            client.post("/api/v1/modules", json={"id": m["id"], "enabled": False}, headers=admin).status_code
            == 200
        )
    assert client.get("/api/v1/trees").status_code == 404
    assert create(client, admin).status_code == 201
    assert client.get("/health").status_code == 200


def test_gis_duplicates_and_merge_preserves_source(client):
    admin, _, _, _ = account(client, "Admin", "SUPER_ADMIN")
    a = create(client, admin).json()
    b = create(client, admin).json()
    matches = client.get("/api/v1/complaints/" + a["id"] + "/duplicates", headers=admin).json()
    assert matches[0]["complaint"]["id"] == b["id"]
    assert len(client.get("/api/v1/complaints/nearby?latitude=8.72&longitude=77.74&radius=100").json()) == 2
    result = client.post(
        "/api/v1/complaints/" + a["id"] + "/merge",
        headers=admin,
        json={"target_id": b["id"], "reason": "Same drain and location, confirmed."},
    )
    assert result.status_code == 200
    assert client.get("/api/v1/complaints/" + a["id"], headers=admin).json()["merged_into"] == b["id"]
    assert (
        client.post(
            "/api/v1/complaints/" + b["id"] + "/merge",
            headers=admin,
            json={"target_id": a["id"], "reason": "Attempt a circular merge"},
        ).status_code
        == 409
    )


def test_tree_land_verification_and_volunteer_capacity(client):
    admin, _, _, _ = account(client, "Admin", "SUPER_ADMIN")
    citizen, _, _, _ = account(client)
    assert (
        client.post(
            "/api/v1/planting-sites",
            headers=admin,
            json={
                "name": "Example site",
                "latitude": 8.7,
                "longitude": 77.7,
                "ownership_status": "OFFICIALLY_VERIFIED",
            },
        ).status_code
        == 422
    )
    activity = client.post(
        "/api/v1/activities",
        headers=admin,
        json={
            "title": "Test planting day",
            "description": "An organized tree planting event for testing.",
            "category": "TREE_PLANTING",
            "locality": "Nellai",
            "latitude": 8.7,
            "longitude": 77.7,
            "starts_at": (now() + timedelta(days=2)).isoformat() + "Z",
            "capacity": 1,
        },
    ).json()
    assert client.post("/api/v1/activities/" + activity["id"] + "/join", headers=citizen).status_code == 409
    profile = {
        "locality": "Nellai",
        "availability": "Weekends",
        "skills": ["Planting"],
        "interests": ["Trees"],
    }
    assert client.post("/api/v1/volunteers", headers=citizen, json=profile).status_code == 200
    assert client.post("/api/v1/activities/" + activity["id"] + "/join", headers=citizen).status_code == 200
    assert client.post("/api/v1/activities/" + activity["id"] + "/join", headers=citizen).status_code == 200
    other, _, _, _ = account(client, "Other")
    client.post("/api/v1/volunteers", headers=other, json=profile)
    assert client.post("/api/v1/activities/" + activity["id"] + "/join", headers=other).status_code == 409


def test_account_deletion_revokes_access_and_anonymizes(client):
    headers, uid, _, password = account(client)
    c = create(client, headers).json()
    assert (
        client.request("DELETE", "/api/v1/auth/me", headers=headers, json={"password": password}).status_code
        == 204
    )
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    with SessionLocal() as db:
        user = db.get(User, uid)
        complaint = db.get(Complaint, c["id"])
        assert user.email is None and not user.active
        assert complaint.user_id is None and complaint.image_id is None


def test_ai_contract_does_not_invent_predictions():
    from fastapi.testclient import TestClient
    from ai.main import app

    response = TestClient(app).post("/v1/classify", json={"description": "A blocked drain"})
    assert response.status_code == 200
    assert response.json()["available"] is False
    assert response.json()["confidence"] is None
