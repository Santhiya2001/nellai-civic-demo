"""Export the composed API and each installed module's documented routes."""

import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
from app.main import app
from app.modules import installed_manifests

schema = app.openapi()
(ROOT / "docs").mkdir(exist_ok=True)
(ROOT / "docs/openapi.json").write_text(json.dumps(schema, indent=2) + "\n")
tags = {
    "civic": "Civic",
    "green": "Green Nellai",
    "volunteer": "Volunteer Nellai",
    "water": "Neervalam",
    "flood-monitoring": "Community: flood monitoring",
}
for mid, manifest in installed_manifests().items():
    tag = tags.get(mid, manifest["name"])
    paths = {
        path: operations
        for path, operations in schema["paths"].items()
        if any(
            tag in operation.get("tags", [])
            for operation in operations.values()
            if isinstance(operation, dict)
        )
    }
    module_schema = {
        "openapi": schema["openapi"],
        "info": {"title": manifest["name"], "version": manifest["version"]},
        "paths": paths,
        "components": schema.get("components", {}),
    }
    (ROOT / "modules" / mid / "api.yaml").write_text(
        yaml.safe_dump(module_schema, sort_keys=False, allow_unicode=True)
    )
print(f"Exported {len(schema['paths'])} paths and {len(installed_manifests())} module API definitions.")
