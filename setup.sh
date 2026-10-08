#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
command -v node >/dev/null || { echo 'Install Node.js 20.19+ or 22 LTS first.'; exit 1; }
command -v npm >/dev/null || { echo 'npm is required.'; exit 1; }
if command -v uv >/dev/null; then
  NELLAI_UV=uv
else
  if [[ ! -x .tools/bin/uv ]]; then
    python3 -m pip install --target .tools uv
  fi
  NELLAI_UV="$PWD/.tools/bin/uv"
fi
if [[ ! -x .venv/bin/python ]]; then
  "$NELLAI_UV" python install 3.12
  "$NELLAI_UV" venv --python 3.12 --relocatable .venv
fi
"$NELLAI_UV" pip sync --python .venv/bin/python backend/requirements.lock
if [[ ! -f .env ]]; then
  .venv/bin/python scripts/configure.py --demo
fi
.venv/bin/python -m alembic upgrade head
.venv/bin/python scripts/seed_demo.py
npm --prefix web ci --no-audit --no-fund
npm --prefix web run build
echo 'Ready. Run ./start.sh, then open http://localhost:8080'
echo 'Generated logins are in runtime/DEMO_CREDENTIALS.md'
