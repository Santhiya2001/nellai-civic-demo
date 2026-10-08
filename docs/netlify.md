# Deploy the web dashboard on Netlify

Netlify hosts the React dashboard. The current FastAPI backend, PostgreSQL/PostGIS database, uploaded photos and escalation worker need a separate server. Uploading `web/dist` alone does not provide login or complaint storage.

```text
Browser -> Netlify: React dashboard
           /api/* -> HTTPS FastAPI backend
                      -> PostgreSQL/PostGIS
                      -> Redis
                      -> persistent photo storage
                    Separate worker -> same database
```

The repository now includes `netlify.toml` and a build script that creates Netlify API proxy rules. Localhost development continues to use the existing launcher. No hosting account or online service has been created by adding these files.

## 1. Put the source on GitHub

Publish the project source, keeping `web`, `modules`, `scripts` and `netlify.toml` together at the repository root. The dashboard imports frontend components from `modules`, so publishing only the `web` source is insufficient.

Use the supplied `.gitignore`. Do not upload `.env`, `runtime`, demo credentials, `.venv`, `node_modules`, or database backups. Git respects `.gitignore`; manually dragging files into GitHub may not. Review the files before publishing.

## 2. Prepare an online backend

Use a host that runs Python or Docker, such as Render or your own VM. `localhost:8080` is your computer and cannot serve as Netlify's backend origin.

For a Render Python web service using this repository, keep the service root at the repository root and use:

| Setting | Value |
|---|---|
| Python version | Python 3.12; set `PYTHON_VERSION=3.12.14` |
| Build command | `pip install -r backend/requirements.lock` |
| Pre-deploy command | `python -m alembic upgrade head` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT --no-proxy-headers` |
| Health check | `/health` |

Run migrations once before starting the service if your plan has no pre-deploy command. Do not run `start.sh` on Render: it is the local demonstration launcher.

Configure these environment variables on the **backend host**, replacing the example values:

```dotenv
PYTHONPATH=backend:.
ENVIRONMENT=production
DEMO_MODE=false
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@DB_HOST:5432/DB_NAME
REDIS_URL=redis://REDIS_HOST:6379/0
JWT_SECRET=REPLACE_WITH_A_NEW_RANDOM_SECRET_OF_AT_LEAST_32_CHARACTERS
PUBLIC_URL=https://YOUR-SITE.netlify.app
CORS_ORIGINS=https://YOUR-SITE.netlify.app
UPLOAD_DIR=/var/data/uploads
DISTRICT_NAME=Tirunelveli
TIMEZONE=Asia/Kolkata
```

Copy database and Redis connection details from your provider, including any required TLS options. Use the `postgresql+psycopg://` driver prefix with the PostgreSQL connection details; this project installs Psycopg 3. Generate the JWT secret privately with `python -c "import secrets; print(secrets.token_urlsafe(48))"` and store it only in the backend environment.

Use PostgreSQL with the PostGIS extension available. The migration enables PostGIS, so the migration database account needs permission to create the extension, or a database administrator must enable it first. Attach a persistent disk at `/var/data` for photos. Render's default filesystem is temporary; its persistent disks require a paid service. Back up both the database and uploaded files.

Start a separate background worker from the same repository with the same database, Redis, JWT, URL and environment settings:

```bash
python -m app.worker
```

It needs the same Python dependencies and `PYTHONPATH`. Without this worker, scheduled escalation and configured email delivery do not run. SMTP settings are optional for in-app notifications but required for email.

A fresh database starts empty. Local demo logins and records are not copied to the host. Register your own account through the website, then have the server/database administrator grant that verified account `SUPER_ADMIN` for initial administration; configure authorities, calendars and assignment rules through the dashboard. The demo seeding command intentionally refuses to run in production. See [deployment.md](deployment.md) for the remaining public-service requirements. These hosting instructions do not change the project's local-demo readiness status.

Keep `--no-proxy-headers` until your hosting provider's trusted proxy addresses are configured correctly. With this conservative setting, requests behind a proxy may share a rate-limit bucket. Do not fix this by trusting arbitrary internet-supplied forwarding headers; assess this before admitting real traffic.

Confirm `https://YOUR-BACKEND/health` returns JSON with `"status":"ok"`. The backend's `/docs` page provides its API documentation.

## 3. Connect Netlify

1. In Netlify, choose **Add new project -> Import an existing project**, connect GitHub and select this repository.
2. Keep **Base directory** at the repository root (`.` or blank). Do not set it to `web`.
3. The root `netlify.toml` supplies the settings below. If the UI proposes different settings, use these.

| Setting | Value |
|---|---|
| Build command | `npm --prefix web ci && npm --prefix web run build && node scripts/netlify-redirects.mjs` |
| Publish directory | `web/dist` |
| Node version | `22` |

4. Add a Netlify environment variable, available to builds:

```dotenv
NETLIFY_API_ORIGIN=https://YOUR-BACKEND.onrender.com
```

Use your actual backend's HTTPS origin, without `/api/v1`. This is a public address, not a secret. Do not put `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, or demo passwords into Netlify's frontend build environment.

5. Deploy. Once your Netlify site address is known, set backend `PUBLIC_URL` and `CORS_ORIGINS` to that exact HTTPS address and restart the backend and worker. Origins have no trailing slash. Add additional trusted domains as comma-separated values if needed.

The build creates `web/dist/_redirects` so `/api/v1/...` on the Netlify site reaches `/api/v1/...` on FastAPI. Existing relative API calls and refresh cookies use the website's origin. No frontend API-key or authentication rewrite is required. Hash-based routes such as `/#dashboard` already work without a catch-all redirect.

Deploy previews have different domains. Do not expect session refresh to work on a preview unless its exact origin has also been deliberately allowed on an appropriate backend. Test the main site URL first.

## 4. Check the online website

1. Open `https://YOUR-SITE.netlify.app/health`; check for the backend's JSON response.
2. Open `https://YOUR-SITE.netlify.app/api/v1/config`; confirm it returns JSON, not HTML.
3. Register and log in. Reload the page to check cookie-based session refresh.
4. Submit a complaint with a small photograph and location. Confirm it persists after signing out and back in.
5. Check assignment, authority resolution, citizen verification and worker escalation with your configured staff accounts.
6. Restart the backend and confirm records and photographs still exist.

The configuration and frontend build have been checked locally. A hosted end-to-end test requires your real Netlify site and backend URL.

## Troubleshooting

| Problem | What to check |
|---|---|
| Build says `NETLIFY_API_ORIGIN` is missing | Add the backend HTTPS origin to Netlify build environment variables, then redeploy. |
| API request returns HTML or 404 | Deploy the full repository using the supplied command; inspect `web/dist/_redirects` in the build output. |
| Login works but reloading signs out | Backend `CORS_ORIGINS` must contain the exact Netlify HTTPS origin, without a trailing slash. |
| API returns 502/504 | Check backend health and logs. Netlify proxy requests time out after 26 seconds; a sleeping backend may need warming or an always-on plan. |
| API returns 503 | Check backend database and Redis connectivity. |
| API returns 429 | Wait for the rate-limit window; inspect proxy/client-IP configuration if several visitors share a limit. |
| Photographs disappear after restart | Set `UPLOAD_DIR` inside a persistent mounted disk. |
| Old demo credentials do not work | Local data is not automatically transferred; create accounts on the hosted instance. |

## Official references

- [Netlify monorepo build settings](https://docs.netlify.com/build/configure-builds/monorepos/)
- [Netlify API proxy rules and timeouts](https://docs.netlify.com/manage/routing/redirects/rewrites-proxies/)
- [Render FastAPI web services](https://render.com/docs/deploy-fastapi)
- [Render persistent disks](https://render.com/docs/disks)
