# Running the demo elsewhere

The tested primary delivery is the local launcher in README. A Docker Compose configuration is included as an optional deployment recipe. It requires the Docker Compose v2 plugin (the current workstation originally had Docker Engine without that plugin).

## Optional fresh Docker installation

Use a fresh checkout to keep your prepared local `.env` and demo data separate. Generate a Docker configuration, then build:

```bash
python3 scripts/configure.py --docker --demo
docker compose up --build -d
docker compose exec backend python scripts/seed_demo.py
docker compose cp backend:/app/runtime/DEMO_CREDENTIALS.md ./DEMO_CREDENTIALS.private.md
```

Keep the copied credentials private and remove that copy before publishing source. The web app binds to localhost:8080. Database, Redis and uploads use named volumes. Do not run `docker compose down -v` when you want to retain data.

The AI service profile contains only the disabled provider contract; `docker compose --profile ai up` does not install a trained model.

## Public service: deferred

The user requested a simple local presentation demo and excluded Play Store release. Do not treat this as a finished production rollout. A public service needs an HTTPS domain, real verified authority data, contact verification/recovery, backup restoration tests, monitoring, privacy/retention review, security/performance review and configured notification delivery.

Set `ENVIRONMENT=production` only after configuring PostgreSQL, Redis, HTTPS `PUBLIC_URL`, HTTPS trusted origins and `DEMO_MODE=false`. Production validation rejects the demo/SQLite combination. Put TLS and request-size controls at a reverse proxy and configure trusted proxy addresses carefully; the reference local API intentionally ignores forwarded client IP headers to avoid spoofing.

No public deployment, email send, GitHub publication or Play Store submission was performed as part of this demo delivery.
