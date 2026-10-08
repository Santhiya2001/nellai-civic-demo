"""Configure Gmail complaint alerts interactively; never print or send the app password."""

import argparse
from getpass import getpass
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT)]

from dotenv import set_key
from pydantic import EmailStr, TypeAdapter, ValidationError

from app.config import settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Show configuration status without sending email")
    args = parser.parse_args()
    cfg = settings()
    if args.check:
        print("Complaint recipient:", cfg.complaint_alert_email or "not configured")
        print("SMTP host:", cfg.smtp_host or "not configured")
        print("Sender:", cfg.smtp_from or "not configured")
        print("SMTP password:", "configured" if cfg.smtp_password else "not configured")
        print("No email was sent.")
        return
    if not sys.stdin.isatty():
        raise SystemExit("Run this command in your own terminal so the password can be entered privately.")

    print("Steps 1 and 2 ask for EMAIL ADDRESSES. Press Enter to keep the address in brackets.")
    print("Wait until step 3 before entering your Gmail App Password; it will be hidden.")

    def email_prompt(label, default=""):
        value = input(f"{label}" + (f" [{default}]" if default else "") + ": ").strip() or default
        try:
            return str(TypeAdapter(EmailStr).validate_python(value))
        except ValidationError:
            raise SystemExit(
                "This prompt needs an email address, not an App Password. "
                "Run setup again and press Enter to keep the displayed email address. "
                "Enter the App Password only at step 3. No configuration was changed."
            ) from None

    recipient = email_prompt("Step 1/3: Authority email to receive complaints", cfg.complaint_alert_email or "")
    sender = email_prompt("Step 2/3: Gmail account to send from", cfg.smtp_user or recipient)
    print("Create a Gmail app password: https://myaccount.google.com/apppasswords")
    print("Enter the app password here, not in chat. Your ordinary Google password is not used.")
    password = "".join(getpass("Step 3/3: Gmail App Password (hidden): ").split())
    if len(password) != 16 or not password.isalnum():
        raise SystemExit("Expected a 16-character app password; no configuration was changed.")
    updates = {
        "COMPLAINT_ALERT_EMAIL": recipient,
        "SMTP_HOST": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "SMTP_USER": sender,
        "SMTP_PASSWORD": password,
        "SMTP_FROM": sender,
        "SMTP_STARTTLS": "true",
    }
    # Write atomically with private permissions and preserve all unrelated settings.
    fd, filename = tempfile.mkstemp(prefix=".email-config-", dir=ROOT)
    path = Path(filename)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write((ROOT / ".env").read_text())
        for key, value in updates.items():
            set_key(path, key, value)
        path.chmod(0o600)
        path.replace(ROOT / ".env")
    finally:
        path.unlink(missing_ok=True)
    print(f"Saved Gmail configuration. New complaint alerts will go to {recipient}.")
    if (ROOT / "runtime/portable-dependencies.sha256").exists():
        print("Start the app again using your Windows, Linux or macOS launcher. No email was sent by setup.")
    else:
        print("Restart the app with bash stop.sh, then bash start.sh. No email was sent by this setup command.")


if __name__ == "__main__":
    main()
