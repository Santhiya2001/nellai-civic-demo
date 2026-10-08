import json
from pathlib import Path


def test_manifest_contract():
    root = Path(__file__).resolve().parents[1]
    m = json.loads((root / "module.json").read_text())
    assert m["id"] == root.name
    assert m["api_version"] == "v1"
    assert (root / "backend/api.py").exists()
