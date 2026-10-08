# Demo delivery status

Latest agreed scope: a simple localhost web demo and an editable PowerPoint for an ME project. Play Store publication and production mobile work are out of the current scope. Presentation identity fields should remain editable placeholders.

Requested project folder: `/media/santhiya/svn/sandy_1`.

## Implemented so far

- FastAPI backend, SQLAlchemy models, Alembic migrations, PostgreSQL/PostGIS support.
- Registration, password login, JWT sessions, rotating refresh tokens and role checks.
- Private photo upload, complaint reporting, assignment, working-day deadlines, escalation, resolution evidence and citizen verification.
- GIS APIs, volunteer activities, tree records, water observations and independently enabled modules.
- React/TypeScript screens and styling for the above workflows.
- 15 backend/module tests passed using SQLite on 18 September 2026. PostgreSQL integration validation remains to be done.
- PostgreSQL/PostGIS container `nellai-postgis`, local port 55432, dedicated volume `nellai_postgis_data`.

## Completed on 19 September 2026

- Fixed module frontend resolution; TypeScript and the web build pass.
- Applied migrations, seeded the PostGIS demo, and passed all 15 backend/module tests on a separate disposable PostGIS database.
- Added start/stop/setup scripts and VS Code tasks/debug configuration.
- Passed both browser scenarios, including the full citizen → authority → citizen workflow and responsive pages.
- Created 21 editable PowerPoint slides, a 21-page PDF, speaker notes and a live demo guide.
- Added README, setup, API, architecture, module, security/privacy and testing documentation; MIT license and contribution files.
- Added optional Docker/CI configuration. See docs/verification.md for the exact validation scope.

The `mobile/` directory is only generated Flutter scaffolding, explicitly documented as deferred and unused by this demo. The AI service is a disabled provider interface and does not claim trained AI predictions.

## Build workspace and tools

Because the requested `/media` folder is outside the tool sandbox's allowed write roots, implementation is staged in `/home/santhiya/nellai-build/nellai-green-civic` and copied into the requested folder using approved `rsync -a` operations. The staging folder currently has the Python `.venv`, npm dependencies, generated private `.env`, and runtime files. These are intentionally not copied as public source.

Generated local demo passwords are in `runtime/DEMO_CREDENTIALS.md`. Never commit `.env`, runtime data, signing files or passwords.

Start with START_HERE.md for the demonstration. Native mobile, Play Store publication and production rollout are outside the agreed simplified scope.
