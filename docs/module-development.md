# Developing a module

Modules are trusted source packages reviewed before installation. The registry enables/disables packages already present on disk; it never installs arbitrary code from an HTTP request.

## Package contract

```text
modules/your-module/
  module.json
  README.md
  api.yaml
  backend/
    __init__.py
    models.py
    api.py
  frontend/
    index.tsx
  database/
    README.md
  tests/
    __init__.py
    test_manifest.py
```

Example manifest:

```json
{
  "id": "your-module",
  "name": "Your community module",
  "version": "1.0.0",
  "api_version": "v1",
  "description": "What this module adds",
  "author": "Your team",
  "permissions": ["read", "write"],
  "dependencies": [],
  "enabled_by_default": false,
  "navigation": {"label": "Your module", "path": "your-module"}
}
```

`id` must match the folder, use lowercase letters/digits/hyphens/underscores and begin with a letter. The loader validates the API version, semantic version string, dependency existence and required files. `permissions` documents capabilities; **it is not an automatic authorization policy**. Each route must use the core authentication/role dependencies itself.

## Backend API

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User
from app.security import current_user, admin_user

router = APIRouter(prefix="/your-module", tags=["Your module"])

@router.get("/records")
def records(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return []  # Replace with an authorized query of your module's models.
```

Use Pydantic input models with `extra='forbid'` and bounded inputs. Filter queries by the authenticated user's authorization. Mutations should create an `AuditLog` in the same transaction. Never trust role names or user IDs supplied by the browser.

The platform mounts `router` under `/api/v1` with a module-enabled dependency. Disabled modules return 404. Modules still execute trusted imports at startup; disabling is not sandboxing or uninstalling their Python code.

## Database model and migration

Use `app.db.Base` and prefix table names with your module ID. Add foreign keys explicitly and preserve existing core contracts. Create an Alembic revision under `database/versions`, manually review it, and test its upgrade/downgrade on a disposable database. Do not modify a released revision. PostgreSQL-only indexes/geometry operations must have a documented SQLite development fallback or declare PostgreSQL as required.

```bash
.venv/bin/python -m alembic revision --autogenerate -m add_your_module
.venv/bin/python -m alembic upgrade head
```

Review generated migration changes carefully: `complaints.location` and `boundaries.geom` are migration-owned computed PostGIS columns and are not ordinary ORM attributes. Do not delete them accidentally when generating revisions.

## Frontend component

The default export of `frontend/index.tsx` is a React component. Existing modules import `request`, `post` and reusable UI from `web/src/api.ts` and `web/src/ui.tsx`. `usePlatform()` exposes the user, configuration, navigation and notification functions. These are the demo's local extension interfaces; a separately versioned npm SDK is future work.

`web/src/main.tsx` discovers frontend entry points at build time and shows only enabled modules. Adding a module requires rebuilding the web application and restarting the backend; toggling an installed module does not require a rebuild. Core complaint pages continue to work with all optional modules disabled.

## Test and publish source

Copy the complete `flood-monitoring` package as a starting example. Give your tests a unique package path and add tests for unauthorized reads/writes, input validation, disabled behavior and migrations. Run backend tests, TypeScript/build checks and module validation. Regenerate the OpenAPI files after adding routes. Submit a pull request with migrations, screenshots, license/provenance of any datasets, and a description of configuration needs.

API compatibility uses `/api/v1`; breaking changes require a new API version. Module versions use semantic versioning. Module data is retained on disable. Before physically removing a module, disable it, review dependent packages, and plan data retention/migration separately.
