"""Set up and run the packaged demo on Windows, Linux or macOS with Python 3.12."""

import argparse
import hashlib
import os
from pathlib import Path
import signal
import socket
import struct
import subprocess
import sys
import time
from urllib.request import urlopen
import venv

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
PYTHON = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
LOCK = ROOT / "backend/requirements.lock"


def run(arguments, env):
    subprocess.run([str(PYTHON), *arguments], cwd=ROOT, env=env, check=True)


def prepare(port):
    if sys.version_info[:2] != (3, 12) or struct.calcsize("P") != 8:
        raise SystemExit("Install Python 3.12 (64-bit), then run the launcher again. See RUN_ON_ANOTHER_PC.md.")
    if not (ROOT / "web/dist/index.html").is_file():
        raise SystemExit("The bundled web build is missing. Extract the complete ZIP before starting.")
    RUNTIME.mkdir(exist_ok=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "backend"), str(ROOT)])
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"
    stamp = RUNTIME / "portable-dependencies.sha256"
    digest = hashlib.sha256(LOCK.read_bytes() + str(PYTHON).encode() + sys.version.encode()).hexdigest()
    if not PYTHON.is_file():
        print("Creating a private Python environment...", flush=True)
        try:
            venv.EnvBuilder(with_pip=True).create(ROOT / ".venv")
        except Exception:
            raise SystemExit("Could not create the environment. On Ubuntu install python3.12-venv. See RUN_ON_ANOTHER_PC.md.") from None
    if not stamp.exists() or stamp.read_text().strip() != digest:
        print("Installing pinned dependencies (internet required on first setup)...", flush=True)
        run(["-m", "pip", "install", "--disable-pip-version-check", "-r", str(LOCK)], env)
        stamp.write_text(digest + "\n")
    if not (ROOT / ".env").exists():
        run(["scripts/configure.py", "--demo"], env)
        run(["-c", "from dotenv import set_key; import sys; "
             "set_key('.env', 'COMPLAINT_ALERT_EMAIL', 'sandymuthukutti@gmail.com'); "
             "set_key('.env', 'PUBLIC_URL', 'http://localhost:' + sys.argv[1]); "
             "set_key('.env', 'CORS_ORIGINS', 'http://localhost:' + sys.argv[1] + ',http://127.0.0.1:' + sys.argv[1])",
             str(port)], env)
    run(["-m", "alembic", "upgrade", "head"], env)
    run(["scripts/seed_demo.py"], env)
    print("Demo logins (open privately):", RUNTIME / "DEMO_CREDENTIALS.md", flush=True)
    return env


def serve(env, port):
    children = []
    stopping = False

    def stop_requested(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, stop_requested)
    signal.signal(signal.SIGTERM, stop_requested)
    options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    try:
        api = subprocess.Popen(
            [str(PYTHON), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port), "--no-proxy-headers"],
            cwd=ROOT, env=env, **options,
        )
        children.append(api)
        for _ in range(60):
            if stopping or api.poll() is not None:
                raise SystemExit("Startup stopped. Check the error above; demo records were retained.")
            try:
                with urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.5)
        else:
            raise SystemExit("The app did not become ready. Check the startup messages above.")
        children.append(subprocess.Popen([str(PYTHON), "-m", "app.worker"], cwd=ROOT, env=env, **options))
        print(f"\nREADY: http://localhost:{port}\nKeep this terminal open. Press Ctrl+C to stop.\n", flush=True)
        while not stopping and all(child.poll() is None for child in children):
            time.sleep(0.5)
        if not stopping:
            raise SystemExit("A demo process exited. Check its error above, then restart the launcher.")
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        print("Demo stopped. Saved records are retained.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup-only", action="store_true", help="Install and seed without starting the server")
    parser.add_argument("--email", action="store_true", help="Configure Gmail privately, then exit")
    parser.add_argument("--port", type=int, default=8080, help="Local port; default 8080")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    os.chdir(ROOT)
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", args.port)) == 0:
            raise SystemExit(f"Port {args.port} is already in use. Stop the running demo before setup or email configuration.")
    try:
        env = prepare(args.port)
        if args.email:
            run(["scripts/configure_email.py"], env)
            print("Start the demo again using your platform launcher to activate these settings.")
        elif args.setup_only:
            print("Setup complete. Run your platform launcher to start the demo.")
        else:
            serve(env, args.port)
    except subprocess.CalledProcessError:
        raise SystemExit("A setup command failed. Read the error above and rerun the launcher after fixing it.") from None


if __name__ == "__main__":
    main()
