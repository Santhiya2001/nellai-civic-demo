from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.config import Settings, settings
from app.db import SessionLocal, now
from app.models import ComplaintEmail, Notification, User
from app import worker
from test_workflows import account, create, setup_authority


@pytest.fixture
def mail_config(monkeypatch):
    cfg = settings()
    monkeypatch.setattr(cfg, "complaint_alert_email", "authority@example.org")
    monkeypatch.setattr(cfg, "smtp_host", "smtp.example.org")
    monkeypatch.setattr(cfg, "smtp_from", "sender@example.org")
    monkeypatch.setattr(cfg, "smtp_user", "sender@example.org")
    monkeypatch.setattr(cfg, "smtp_password", "test-only-password")
    return cfg


@pytest.mark.parametrize("assigned", [False, True])
def test_new_complaint_emails_authority_once(client, mail_config, monkeypatch, assigned):
    if assigned:
        admin, _, _, _ = account(client, "Admin", "SUPER_ADMIN")
        setup_authority(client, admin)
    citizen, _, _, _ = account(client)
    smtp = MagicMock()
    smtp_factory = MagicMock(return_value=smtp)
    monkeypatch.setattr(worker.smtplib, "SMTP", smtp_factory)
    complaint = create(client, citizen).json()
    assert complaint["status"] == ("ASSIGNED" if assigned else "REPORTED")
    smtp_factory.assert_not_called()  # Network delivery is outside the submission request.
    with SessionLocal() as db:
        rows = list(db.scalars(select(ComplaintEmail)))
        assert len(rows) == 1
        assert rows[0].recipient == "authority@example.org"
        worker.deliver_complaint_alerts(db)
        worker.deliver_complaint_alerts(db)
        assert rows[0].state == "SENT" and rows[0].sent_at is not None
        assert rows[0].attempts == 1
    smtp_factory.assert_called_once_with("smtp.example.org", 587, timeout=15)
    connection = smtp.__enter__.return_value
    connection.starttls.assert_called_once()
    connection.login.assert_called_once_with("sender@example.org", "test-only-password")
    connection.send_message.assert_called_once()
    message = connection.send_message.call_args.args[0]
    assert message["To"] == "authority@example.org"
    assert message["From"] == "sender@example.org"
    assert complaint["reference"] in message["Subject"]
    body = message.get_content()
    for value in [complaint["title"], complaint["description"], "8.72", "77.74"]:
        assert value in body
    assert f"/#complaints/{complaint['id']}" in body
    assert "Configured test team" in body if assigned else "Pending assignment" in body
    assert len(list(message.iter_attachments())) == 0


def test_failed_smtp_retries_without_losing_complaint(client, mail_config, monkeypatch):
    citizen, _, _, _ = account(client)
    response = create(client, citizen)
    assert response.status_code == 201
    clock = now()
    monkeypatch.setattr(worker, "now", lambda: clock)
    sender = MagicMock(side_effect=[ConnectionError(), None])
    monkeypatch.setattr(worker, "send_email", sender)
    with SessionLocal() as db:
        worker.deliver_complaint_alerts(db)
        row = db.scalar(select(ComplaintEmail))
        assert row.state == "PENDING" and row.attempts == 1
        assert row.next_attempt_at == clock + timedelta(seconds=30)
    with SessionLocal() as db:  # A fresh worker session sees the same durable queue.
        worker.deliver_complaint_alerts(db)
        assert sender.call_count == 1
        clock += timedelta(seconds=31)
        worker.deliver_complaint_alerts(db)
        row = db.scalar(select(ComplaintEmail))
        assert row.state == "SENT" and row.attempts == 2
        assert sender.call_args_list[0].args[-1] == sender.call_args_list[1].args[-1]
    assert client.get(f"/api/v1/complaints/{response.json()['id']}", headers=citizen).status_code == 200


def test_five_failed_attempts_stop_retrying(client, mail_config, monkeypatch):
    citizen, _, _, _ = account(client)
    create(client, citizen)
    clock = now()
    monkeypatch.setattr(worker, "now", lambda: clock)
    sender = MagicMock(side_effect=ConnectionError())
    monkeypatch.setattr(worker, "send_email", sender)
    with SessionLocal() as db:
        for _ in range(6):
            worker.deliver_complaint_alerts(db)
            clock += timedelta(hours=1)
        row = db.scalar(select(ComplaintEmail))
        assert row.state == "FAILED" and row.attempts == 5
        assert row.sent_at is None
    assert sender.call_count == 5


def test_missing_smtp_keeps_alert_pending(client, mail_config, monkeypatch):
    monkeypatch.setattr(mail_config, "smtp_host", "")
    sender = MagicMock()
    monkeypatch.setattr(worker, "send_email", sender)
    citizen, _, _, _ = account(client)
    create(client, citizen)
    with SessionLocal() as db:
        worker.deliver_complaint_alerts(db)
        row = db.scalar(select(ComplaintEmail))
        assert row.state == "PENDING" and row.attempts == 0
    sender.assert_not_called()


def test_disabled_recipient_and_rejected_submission_do_not_queue(client, monkeypatch):
    citizen, _, _, _ = account(client)
    create(client, citizen)
    monkeypatch.setattr(settings(), "complaint_alert_email", "authority@example.org")
    assert create(client, citizen, image="missing-upload").status_code == 422
    with SessionLocal() as db:
        assert list(db.scalars(select(ComplaintEmail))) == []


def test_recipient_setting_rejects_invalid_addresses():
    assert Settings(complaint_alert_email="  ").complaint_alert_email is None
    assert Settings(complaint_alert_email="authority@example.org").complaint_alert_email == "authority@example.org"
    with pytest.raises(ValidationError):
        Settings(complaint_alert_email="not-an-email")


def test_outbox_preview_is_admin_only_and_never_exposes_credentials(client, mail_config, monkeypatch):
    monkeypatch.setattr(mail_config, "smtp_host", "")
    citizen, _, _, _ = account(client)
    complaint = create(client, citizen).json()
    assert client.get("/api/v1/complaint-emails").status_code == 401
    assert client.get("/api/v1/complaint-emails", headers=citizen).status_code == 403
    admin, _, _, _ = account(client, "Admin", "SUPER_ADMIN")
    response = client.get("/api/v1/complaint-emails", headers=admin)
    assert response.status_code == 200
    result = response.json()
    assert result["delivery_configured"] is False
    assert result["counts"] == {"PENDING": 1, "SENT": 0, "FAILED": 0}
    assert result["messages"][0]["reference"] == complaint["reference"]
    assert result["messages"][0]["recipient"] == "authority@example.org"
    assert complaint["description"] in result["messages"][0]["body"]
    assert result["messages"][0]["attempts"] == 0
    assert "test-only-password" not in response.text
    assert "smtp_password" not in response.text


@pytest.mark.parametrize("demo_mode", [True, False])
def test_placeholder_accounts_are_skipped_in_demo_mode(client, mail_config, monkeypatch, demo_mode):
    monkeypatch.setattr(mail_config, "demo_mode", demo_mode)
    citizen, user_id, _, _ = account(client)
    create(client, citizen)
    sender = MagicMock()
    monkeypatch.setattr(worker, "send_email", sender)
    with SessionLocal() as db:
        db.get(User, user_id).email = "citizen@nellai.example"
        db.commit()
        worker.deliver_email(db)
        notices = list(db.scalars(select(Notification)))
        assert notices
        assert all(n.email_state == ("SKIPPED" if demo_mode else "SENT") for n in notices)
    assert sender.call_count == (0 if demo_mode else len(notices))
