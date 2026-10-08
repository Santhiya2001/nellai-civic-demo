# Installation and VS Code

## Prepared machine

Open `/home/santhiya/nellai-build/nellai-green-civic` in VS Code. Run `bash start.sh` from that folder. The browser URL is http://localhost:8080; Swagger is http://localhost:8080/docs. The generated logins are in `runtime/DEMO_CREDENTIALS.md`.

If the server is already running, open the URL or stop it with `bash stop.sh`. The background log is `runtime/demo.log`. Never run a second copy of the worker against the SQLite adapter.

## New installation

For the packaged demonstration on Windows, Linux or macOS, use
[RUN_ON_ANOTHER_PC.md](../RUN_ON_ANOTHER_PC.md). It includes the built website and
creates SQLite demo data using Python 3.12, without Node.js or Docker. The steps
below are the original development setup.

Install Node.js 20.19+ and Python with pip, then run `bash setup.sh`. It uses `uv` to acquire Python 3.12 if needed and stores everything in an isolated `.venv`. On the first installation only, it creates a private `.env`, SQLite database, and labelled sample records. Subsequent setup runs do not replace secrets or reseed existing accounts.

The installed dependencies are pinned in `backend/requirements.lock` and `web/package-lock.json`. Do not copy someone else's `.env` or demo passwords. The `.env.example` contains configuration field names only.

## PostgreSQL/PostGIS

With Docker installed and available to your user, run `bash scripts/local_database.sh`. It creates container `nellai-postgis`, binds PostgreSQL to `127.0.0.1:55432`, uses volume `nellai_postgis_data`, and writes a generated password to `runtime/database.env` (private and ignored by Git). It applies migrations, seeds demo records, and updates the local `.env`. This is a separate database from SQLite; it does not migrate existing demonstration data.

Do not remove the volume unless you intend to delete its records. `docker stop nellai-postgis` stops the database without deleting its data. The start script restarts that named container when the configured URL uses local port 55432.

## Troubleshooting

### Email every new complaint to an authority

Run `.venv/bin/python scripts/configure_email.py` in your own terminal. Enter the
confirmed authority recipient address and the Gmail account used to send mail.
Enter a Google app password at the hidden prompt; do not use your normal Google
password or put the app password in chat. Google requires 2-Step Verification for
app passwords, and some accounts are ineligible. See
[Google's app-password instructions](https://support.google.com/accounts/answer/185833).
The helper uses `smtp.gmail.com`, port 587 and STARTTLS, as documented in
[Google's SMTP settings](https://support.google.com/mail/answer/7104828).

For another mail provider, edit `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`,
`SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_STARTTLS` and `COMPLAINT_ALERT_EMAIL` in the
private `.env`. This worker supports SMTP with STARTTLS (not implicit TLS on port
465). The recipient is an email address and does not need a platform account to
receive an alert. Accessing the linked private report still requires an authorized
account.

Restart using `bash stop.sh` followed by `bash start.sh`. The launcher applies the
new database migration and starts the email worker. The existing PostGIS service
must be available for startup. Every successfully submitted new complaint queues
one alert, even when no responsibility rule matches. Existing complaints are not
backfilled. Alerts include the reference, title, description, category, location,
assigned team and a link; no photo attachments or citizen contact fields are sent.

The worker checks about every 30 seconds and retries failures up to five times
with increasing delays. Alerts remain pending while SMTP is unconfigured and
survive restarts. Successful sends are marked `SENT`, and exhausted retries are
marked `FAILED` in `complaint_emails`. SMTP acceptance is not a guarantee of inbox
delivery; a worker crash after SMTP acceptance but before saving can also cause a
retry of that message. The same Message-ID is retained on retries.

Use `.venv/bin/python scripts/configure_email.py --check` to inspect configuration
without exposing the password or sending mail. The existing account-specific
notifications are still delivered separately when SMTP is enabled.

Internet access and a running app/worker are necessary for email delivery. A
localhost link opens the app only on the computer hosting it; use a deployed
`PUBLIC_URL` when authorities need to open reports from other computers.

### Common startup problems

| Problem | Fix |
|---|---|
| Port 8080 is occupied | Run `bash stop.sh`; otherwise find and stop your other service. `bash start.sh --port 8081` also works, but add that origin to `CORS_ORIGINS` for refresh cookies. |
| Missing web build | Run `npm --prefix web ci` then `npm --prefix web run build`. |
| Python missing | Run `bash setup.sh`. Use `.venv/bin/python`, not the OS Python 3.8. |
| Database connection fails | Run `docker start nellai-postgis`, then `docker logs nellai-postgis`. |
| Docker permission denied | Give your user Docker access using your OS administration process; or use the SQLite adapter. |
| npm reports a corporate certificate error | Configure your actual organization's trusted CA. On this machine `npm ci --cafile=/etc/ssl/certs/ca-certificates.crt` was used. Do not disable TLS verification. |
| Map tiles are blank | Check internet. Local markers and APIs still work; OSM is an external basemap. |
| Location access denied | Enter latitude and longitude manually. Permission is requested only when “Use my current location” is pressed. |
| Login fails | Use the generated file `runtime/DEMO_CREDENTIALS.md`, or register a new citizen account. |
| Rate limit reached | Wait 60 seconds. Authentication is limited to 15 attempts per source IP per minute. |

## Editing

Run the API on 8000 and Vite on 5173 as shown in README. F5 can debug the backend through `.vscode/launch.json`. After frontend edits, run `npm --prefix web run build` before restarting the compiled demo. API changes require a server restart when running the demo launcher.
