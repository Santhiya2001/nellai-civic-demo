#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
if [[ ! -f runtime/database.env ]]; then
  .venv/bin/python -c 'from pathlib import Path; import secrets; p=Path("runtime/database.env"); p.parent.mkdir(exist_ok=True); p.write_text("POSTGRES_USER=nellai\nPOSTGRES_DB=nellai\nPOSTGRES_PASSWORD="+secrets.token_urlsafe(32)+"\n"); p.chmod(0o600)'
fi
if ! docker inspect nellai-postgis >/dev/null 2>&1; then
  docker run -d --name nellai-postgis --env-file runtime/database.env -p 127.0.0.1:55432:5432 -v nellai_postgis_data:/var/lib/postgresql/data postgis/postgis:16-3.5
else
  docker start nellai-postgis
fi
for attempt in {1..30}; do
  if docker exec nellai-postgis pg_isready -U nellai -d nellai >/dev/null; then
    exec .venv/bin/python scripts/use_local_postgis.py
  fi
  sleep 1
done
echo 'Database did not become ready. Inspect: docker logs nellai-postgis'
exit 1
