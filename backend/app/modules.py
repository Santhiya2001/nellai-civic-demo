import importlib
import json
import re
from functools import lru_cache

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import ROOT
from app.db import get_db
from app.models import ModuleRecord


@lru_cache
def installed_manifests():
    result = {}
    for path in sorted((ROOT / "modules").glob("*/module.json")):
        manifest = json.loads(path.read_text())
        module_id = manifest["id"]
        if not re.fullmatch(r"[a-z][a-z0-9_-]{1,59}", module_id) or module_id != path.parent.name:
            raise ValueError(f"Invalid module id in {path}")
        if manifest["api_version"] != "v1" or not re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"]):
            raise ValueError(f"Unsupported module API or version: {module_id}")
        required = [
            "README.md",
            "backend/api.py",
            "backend/models.py",
            "database/README.md",
            "frontend/index.tsx",
            "tests/test_manifest.py",
            "api.yaml",
        ]
        if any(not (path.parent / entry).is_file() for entry in required):
            raise ValueError(f"Incomplete module: {module_id}")
        result[module_id] = manifest
    for manifest in result.values():
        if any(dep not in result for dep in manifest.get("dependencies", [])):
            raise ValueError(f"Missing dependency for {manifest['id']}")
    return result


def import_models():
    for module_id in installed_manifests():
        importlib.import_module(f"modules.{module_id}.backend.models")


def require_module(module_id):
    def check(db: Session = Depends(get_db)):
        module = db.get(ModuleRecord, module_id)
        if not module or not module.enabled:
            raise HTTPException(404, "Module is not enabled")

    return check


def mount_modules(app):
    for module_id in installed_manifests():
        module = importlib.import_module(f"modules.{module_id}.backend.api")
        app.include_router(module.router, prefix="/api/v1", dependencies=[Depends(require_module(module_id))])


def synchronize(db):
    for module_id, manifest in installed_manifests().items():
        record = db.get(ModuleRecord, module_id)
        if not record:
            db.add(
                ModuleRecord(
                    id=module_id,
                    version=manifest["version"],
                    enabled=manifest.get("enabled_by_default", True),
                )
            )
        else:
            record.version = manifest["version"]
    db.commit()
