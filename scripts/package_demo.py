"""Build a portable source/demo ZIP without local credentials, databases or caches."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {
    ".git", ".venv", ".tools", "node_modules", "runtime", "__pycache__", ".pytest_cache",
    ".ruff_cache", ".dart_tool", ".idea", "Pods", "build", "ephemeral", "test-results", "playwright-report", "dist-packages",
}
EXCLUDED_FILES = {"local.properties", "key.properties", "Generated.xcconfig", "flutter_export_environment.sh"}


def private_values():
    values = []
    for path in [ROOT / ".env", ROOT / "runtime/database.env"]:
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            key, sep, value = line.partition("=")
            value = value.strip().strip("\"'")
            if sep and ("PASSWORD" in key or "SECRET" in key) and len(value) >= 12:
                values.append(value.encode())
            if key == "DATABASE_URL":
                password = urlsplit(value).password
                if password:
                    values.append(unquote(password).encode())
    credentials = ROOT / "runtime/demo-credentials.json"
    if credentials.exists():
        values.extend(item["password"].encode() for item in json.loads(credentials.read_text()))
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist-packages/Nellai_Green_Civic_All_PCs.zip")
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    required = ["web/dist/index.html", "START_WINDOWS.bat", "START_LINUX.sh", "START_MAC.command",
                "RUN_ON_ANOTHER_PC.md", "presentation/demo-ready/Nellai_Green_Civic_Demo_Ready.pptx",
                "presentation/demo-ready/Nellai_Green_Civic_Demo_Ready.pdf"]
    for name in required:
        if not (ROOT / name).is_file():
            raise SystemExit(f"Missing required package file: {name}")
    secrets = private_values()
    files = []
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS for part in rel.parts) or path.is_symlink() or not path.is_file():
            continue
        if path.resolve() == output or path.name in EXCLUDED_FILES:
            continue
        if rel.parts[:2] == ("presentation", "screenshots") or path.name in {
            "Nellai_Green_Civic_ME_Demo.pptx", "Nellai_Green_Civic_ME_Demo.pdf",
        }:
            continue
        if (path.name.startswith(".env") and path.name != ".env.example") or path.name.startswith(".email-config-"):
            continue
        if path.suffix in {".pyc", ".pyo", ".db", ".log", ".pid", ".zip", ".tsbuildinfo", ".jks", ".keystore"} or path.name.endswith(".private.md"):
            continue
        data = path.read_bytes()
        if any(secret in data for secret in secrets):
            raise SystemExit(f"Private credential detected; package not written: {rel}")
        files.append((rel, data))
    manifest = {
        "project": "Nellai Green & Civic",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": "3.12 (64-bit)",
        "platforms": ["Windows", "Linux", "macOS"],
        "first_setup_requires_internet": True,
        "private_configuration_included": False,
        "files": {str(rel).replace("\\", "/"): hashlib.sha256(data).hexdigest() for rel, data in files},
    }
    temp = output.with_suffix(".zip.tmp")
    try:
        with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for rel, data in files:
                info = zipfile.ZipInfo("Nellai_Green_Civic/" + rel.as_posix())
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (0o100755 if rel.suffix in {".sh", ".command"} else 0o100644) << 16
                archive.writestr(info, data)
            archive.writestr("Nellai_Green_Civic/PACKAGE_MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
        with zipfile.ZipFile(temp) as archive:
            if archive.testzip() is not None:
                raise SystemExit("ZIP integrity check failed")
        temp.replace(output)
    finally:
        temp.unlink(missing_ok=True)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".zip.sha256").write_text(f"{digest}  {output.name}\n")
    print(f"Created {output}\nFiles: {len(files) + 1}\nSize: {output.stat().st_size / 1024 / 1024:.2f} MiB\nSHA-256: {digest}")


if __name__ == "__main__":
    main()
