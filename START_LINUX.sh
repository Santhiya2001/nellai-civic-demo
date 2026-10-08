#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if command -v python3.12 >/dev/null; then
  exec python3.12 scripts/portable_demo.py "$@"
elif command -v python3 >/dev/null; then
  exec python3 scripts/portable_demo.py "$@"
else
  echo 'Install Python 3.12 first. See RUN_ON_ANOTHER_PC.md.'
  exit 1
fi
