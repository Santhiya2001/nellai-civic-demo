"""Run a separate process: python -m app.worker. No worker runs inside API processes."""

import logging
import smtplib
import ssl
import time
from datetime import timedelta
from email.message import EmailMessage

from sqlalchemy import select, text

from app.config import settings
from app.db import SessionLocal, now
from app.mail import complaint_alert_message
from app.models import Complaint, ComplaintEmail, Notification, User
from app.modules import import_models
from app.services import run_escalations

log = logging.getLogger(__name__)


def send_email(cfg, recipient, subject, body, message_id):
    message = EmailMessage()
    message["From"] = cfg.smtp_from
    message["To"] = recipient
    message["Subject"] = subject
    message["Message-ID"] = f"<{message_id}@notifications.nellai.local>"
    message.set_content(body)
    with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=15) as smtp:
        if cfg.smtp_starttls:
            smtp.starttls(context=ssl.create_default_context())
        if cfg.smtp_user:
            smtp.login(cfg.smtp_user, cfg.smtp_password)
        smtp.send_message(message)


def deliver_complaint_alerts(db):
    cfg = settings()
    if not cfg.smtp_host or not cfg.smtp_from:
        return
    rows = db.scalars(
        select(ComplaintEmail)
        .where(ComplaintEmail.state == "PENDING", ComplaintEmail.next_attempt_at <= now())
        .order_by(ComplaintEmail.created_at)
        .limit(30)
        .with_for_update(skip_locked=True)
    )
    for alert in rows:
        complaint = db.get(Complaint, alert.complaint_id)
        message = complaint_alert_message(db, cfg, complaint)
        alert.attempts += 1
        try:
            send_email(
                cfg, alert.recipient, message["subject"], message["body"], alert.id
            )
        except Exception as exc:
            # Do not log SMTP replies: providers can echo addresses or credentials.
            log.warning("Complaint alert %s delivery failed (%s)", alert.id, type(exc).__name__)
            if alert.attempts >= 5:
                alert.state = "FAILED"
            else:
                alert.next_attempt_at = now() + timedelta(seconds=30 * 2 ** (alert.attempts - 1))
        else:
            alert.state = "SENT"
            alert.sent_at = now()
    db.commit()


def deliver_email(db):
    cfg = settings()
    if not cfg.smtp_host:
        return
    rows = db.scalars(
        select(Notification)
        .where(Notification.email_state == "PENDING", Notification.email_attempts < 5)
        .order_by(Notification.created_at)
        .limit(30)
        .with_for_update(skip_locked=True)
    )
    for notification in rows:
        user = db.get(User, notification.user_id)
        if (
            not user or not user.active or not user.email
            or (cfg.demo_mode and user.email.lower().endswith(".example"))
        ):
            notification.email_state = "SKIPPED"
            continue
        notification.email_attempts += 1
        try:
            send_email(
                cfg, user.email, "Nellai Green & Civic update",
                notification.message + "\n\n" + cfg.public_url, notification.id,
            )
            notification.email_state = "SENT"
        except Exception:
            log.exception("Notification delivery failed: %s", notification.id)
    db.commit()


def tick():
    with SessionLocal() as db:
        # Advisory lock protects the entire job if several worker containers start.
        if db.bind.dialect.name == "postgresql":
            with db.bind.connect() as lock_connection:
                if not lock_connection.scalar(text("SELECT pg_try_advisory_lock(73019281)")):
                    return
                try:
                    deliver_complaint_alerts(db)
                    run_escalations(db)
                    deliver_email(db)
                finally:
                    lock_connection.execute(text("SELECT pg_advisory_unlock(73019281)"))
        else:
            deliver_complaint_alerts(db)
            run_escalations(db)
            deliver_email(db)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import_models()
    while True:
        try:
            tick()
        except Exception:
            log.exception("Worker tick failed; will retry")
        time.sleep(30)
