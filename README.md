# Nellai Green & Civic

A working **localhost web demonstration** of a modular civic and environmental platform for Tirunelveli, built for an ME project presentation. React + TypeScript, FastAPI, and PostgreSQL/PostGIS. A SQLite adapter supports a simpler installation without Docker.

**This delivery is the demo scope agreed for this project.** It is not a certified government service or a Play Store release. All seeded complaints, authorities, photographs, events, and boundaries are clearly marked demonstration data. No government API, trained AI model, or live sensor is claimed.

## Open and run in VS Code

1. Choose **File → Open Folder → `/home/santhiya/nellai-build/nellai-green-civic`**.
2. Open **Terminal → New Terminal**.
3. Run:

```bash
bash start.sh
```

4. Open **http://localhost:8080** in your browser.
5. Open **`runtime/DEMO_CREDENTIALS.md`** in VS Code for your generated citizen, authority, and administrator logins. Passwords are generated for this installation and are not part of the public source.

API documentation: **http://localhost:8080/docs**. Press **Ctrl+C** in the terminal to stop. Alternatively, use **Terminal → Run Task → Nellai: start demo**.

For a detached server:

```bash
bash start.sh --background
bash stop.sh
```

The database and uploads survive a restart. Do not delete `runtime/`, `.env`, or the Docker data volume when you want to keep your demo records.

## ZIP installation on another computer

Extract the complete package and follow **[RUN_ON_ANOTHER_PC.md](RUN_ON_ANOTHER_PC.md)**.
Install 64-bit Python 3.12, then use `START_WINDOWS.bat` on Windows,
`bash START_LINUX.sh` on Linux, or `bash START_MAC.command` on macOS. First setup
needs internet. The built website and SQLite sample-data generator are included;
Node.js and Docker are not needed for this path. Gmail requires private setup on
each new PC. Fresh passwords are generated in `runtime/DEMO_CREDENTIALS.md`.

## Development installation from source

Requirements: Linux/macOS shell, Python with pip, Node.js 20.19+ or a supported Node.js LTS, and internet for dependency installation. These development shell scripts are tested on Ubuntu. Windows developers can use WSL2 or Docker; the ZIP demo also has the native Windows launcher above.

```bash
git clone https://github.com/Santhiya2001/nellai-civic-demo.git nellai-green-civic
cd nellai-green-civic
bash setup.sh
bash start.sh
```

`setup.sh` installs an isolated Python 3.12 environment, installs pinned dependencies, generates private secrets, applies migrations, creates sample records, and builds the web app. A new checkout uses SQLite for an easy demo. To use PostGIS, with Docker running:

```bash
bash scripts/local_database.sh
bash start.sh
```

This creates a separate PostGIS demo database; it does not transfer SQLite records. Detailed instructions and troubleshooting are in [docs/installation.md](docs/installation.md).

## Demonstrate these workflows

- Register a citizen and report an issue with a photograph and GPS coordinates.
- See a configured authority receive the complaint and a working-day deadline.
- Acknowledge the complaint, start work, and submit a resolution photograph.
- Sign in as the reporting citizen to confirm closure or reopen the complaint.
- Review possible duplicates, administrator assignment, classifications and escalation.
- Explore approximate public issue locations, clustering, heatmaps, trees, water resources and boundaries.
- Register as a volunteer, join an activity, register trees and update tree condition.
- Enable the example flood module and enter a manual gauge reading without changing core code.

See [docs/demo-guide.md](docs/demo-guide.md) for the presentation sequence and [presentation/README.md](presentation/README.md) for the editable PowerPoint.

## Repository

```text
backend/app/          Authentication, complaint engine, GIS, audit and API
web/src/             React application and reusable UI
modules/             Civic, green, volunteer, water, flood-monitoring
database/versions/   Frozen Alembic migrations and PostGIS indexes
ai/                  Disabled AI provider contract and tests
tests/               API, permissions, workflow and security tests
scripts/             Setup, demo seed, startup, verification and PPT generation
docs/                Architecture, APIs, developer and demo documentation
presentation/        Editable slides, PDF and speaking notes
.vscode/             Editor settings and run/debug tasks
mobile/              Deferred Flutter scaffold; not used by this web demo
```

## Development

```bash
# Terminal 1: API, port 8000
PYTHONPATH=backend:. .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: React development server, port 5173
npm --prefix web run dev

# Optional third terminal: automatic escalation and email outbox
PYTHONPATH=backend:. .venv/bin/python -m app.worker
```

Web requests use the Vite proxy in development. The compiled demo serves web and API from the same origin on port 8080. In-app updates refresh every 15 seconds; the escalation worker checks every 30 seconds.

To email every new complaint to a configured authority mailbox, run
`.venv/bin/python scripts/configure_email.py` in your terminal, then restart the
app. This saves Gmail SMTP settings privately and adds `COMPLAINT_ALERT_EMAIL`.
The background worker sends queued alerts and retries delivery failures. See
[email setup and delivery details](docs/installation.md#email-every-new-complaint-to-an-authority).

## Verify

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check backend modules ai database scripts tests
npm --prefix web run build
# Optional: creates and removes a disposable test database
.venv/bin/python scripts/test_postgis.py
```

Browser tests use the running demo and create labelled test reports. See [docs/testing.md](docs/testing.md).

## Extending the platform

Every installed module has a manifest, backend router and models, frontend entry point, migration guidance, API definition and tests. Routes are mounted at startup, and the administrator can enable/disable them. Arbitrary uploaded Python or JavaScript is never executed by an installation API. See [docs/module-development.md](docs/module-development.md).

## Limits of this demonstration

- There is no trained image classifier, predictive flood model, IoT feed, OTP/SMS verification, or connected government system.
- Email delivery needs real SMTP settings; in-app notifications work locally. Mobile push delivery is deferred.
- Maps use OpenStreetMap tiles and need internet for the basemap. Records, forms and workflow APIs remain local.
- Tree species are entered by contributors. There is no automatic land ownership or tree suitability decision.
- The Flutter directory is unfinished scaffolding; Android/iOS release work was excluded from the simplified demo.
- This has automated tests, but has not undergone a production security audit, performance certification or legal/privacy review.

MIT licensed. See [LICENSE](LICENSE), [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [docs/privacy.md](docs/privacy.md).
