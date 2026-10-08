#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ! -x .venv/bin/python ]]; then
  echo 'First run: setting up the demo dependencies.'
  bash setup.sh
fi
exec .venv/bin/python scripts/run_local.py "$@"
