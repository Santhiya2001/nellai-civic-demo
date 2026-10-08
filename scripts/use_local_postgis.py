"""Connect this local installation to its isolated project database."""

from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
values = dict(
    line.split("=", 1) for line in (root / "runtime/database.env").read_text().splitlines() if "=" in line
)
url = f"postgresql+psycopg://nellai:{values['POSTGRES_PASSWORD']}@127.0.0.1:55432/nellai"
path = root / ".env"
lines = path.read_text().splitlines()
path.write_text(
    "\n".join("DATABASE_URL=" + url if line.startswith("DATABASE_URL=") else line for line in lines) + "\n"
)
path.chmod(0o600)
subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=root, check=True)
subprocess.run([sys.executable, "scripts/seed_demo.py"], cwd=root, check=True)
