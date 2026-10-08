from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
from app.modules import installed_manifests

for module_id, manifest in installed_manifests().items():
    print(f"OK {module_id} {manifest['version']} ({manifest['api_version']})")
