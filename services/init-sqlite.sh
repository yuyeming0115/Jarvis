#!/usr/bin/env bash
set -euo pipefail

cd "$HOME/Jarvis"
python3 - <<'PY'
from backend.core.store import DB_PATH, ensure_initialized, update_system_status

ensure_initialized()
update_system_status(workbench="online", backend_api="enabled", database="sqlite", public_access=False)
print(f"SQLite database is ready: {DB_PATH}")
PY
