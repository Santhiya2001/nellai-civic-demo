"""Start/stop the local web/API demo and its escalation worker as one process group."""

import argparse
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
RUNTIME.mkdir(exist_ok=True)
PIDFILE = RUNTIME / "demo.pid"
parser = argparse.ArgumentParser()
parser.add_argument("--background", action="store_true")
parser.add_argument("--stop", action="store_true")
parser.add_argument("--port", type=int, default=8080)
args = parser.parse_args()


def existing_pid():
    if not PIDFILE.exists():
        return None
    try:
        pid = int(PIDFILE.read_text())
        command = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ")
        if b"scripts/run_local.py" in command and Path(f"/proc/{pid}/cwd").resolve() == ROOT:
            return pid
    except (ValueError, OSError):
        pass
    return None


if args.stop:
    pid = existing_pid()
    if pid:
        os.kill(pid, signal.SIGTERM)
        for _ in range(200):
            if existing_pid() != pid:
                print("Local demo stopped. Database and uploaded records are retained.")
                break
            time.sleep(0.1)
        else:
            raise SystemExit("The demo is still stopping. Wait before restarting; records are retained.")
    else:
        print("No running local demo was found.")
    raise SystemExit(0)

if existing_pid():
    raise SystemExit("The demo is already running. Open http://localhost:8080 or run ./stop.sh first.")
if not (ROOT / "web/dist/index.html").exists():
    raise SystemExit("Web build missing. Run ./setup.sh or: cd web && npm run build")
if not (ROOT / ".env").exists():
    raise SystemExit("Configuration missing. Run ./setup.sh first.")

with socket.socket() as probe:
    if probe.connect_ex(("127.0.0.1", args.port)) == 0:
        raise SystemExit(f"Port {args.port} is already in use. Stop its server or pass --port NUMBER.")

if args.background:
    with (RUNTIME / "demo.log").open("a") as log:
        child = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--port", str(args.port)],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    time.sleep(1)
    if child.poll() is not None:
        raise SystemExit("Startup failed. Read runtime/demo.log.")
    print(f"Demo starting at http://localhost:{args.port}\nLog: runtime/demo.log\nStop: ./stop.sh")
    raise SystemExit(0)

os.chdir(ROOT)
os.environ["PYTHONPATH"] = str(ROOT / "backend") + os.pathsep + str(ROOT)
sys.path[:0] = [str(ROOT / "backend"), str(ROOT)]
from app.config import settings

cfg = settings()
if "127.0.0.1:55432" in cfg.database_url:
    check = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", "nellai-postgis"], capture_output=True, text=True
    )
    if check.returncode != 0:
        raise SystemExit(
            "The local PostGIS container is unavailable. See docs/installation.md or run scripts/local_database.sh."
        )
    if check.stdout.strip() != "true":
        subprocess.run(["docker", "start", "nellai-postgis"], check=True)
    for attempt in range(30):
        result = subprocess.run(
            ["docker", "exec", "nellai-postgis", "pg_isready", "-U", "nellai", "-d", "nellai"],
            capture_output=True,
        )
        if result.returncode == 0:
            break
        time.sleep(1)

subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
PIDFILE.write_text(str(os.getpid()))
children = []


def stop(signum=None, frame=None):
    for child in children:
        if child.poll() is None:
            child.terminate()
    for child in children:
        try:
            child.wait(timeout=8)
        except subprocess.TimeoutExpired:
            child.kill()
    PIDFILE.unlink(missing_ok=True)
    raise SystemExit(0)


signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
children.append(
    subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(args.port),
            "--no-proxy-headers",
        ]
    )
)
children.append(subprocess.Popen([sys.executable, "-m", "app.worker"]))
print(
    f"\nNellai Green & Civic: http://localhost:{args.port}\nAPI documentation: http://localhost:{args.port}/docs\nDemo logins: runtime/DEMO_CREDENTIALS.md\nPress Ctrl+C to stop.\n",
    flush=True,
)
try:
    while all(c.poll() is None for c in children):
        time.sleep(1)
finally:
    stop()
