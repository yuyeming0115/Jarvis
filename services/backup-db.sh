#!/usr/bin/env bash
set -euo pipefail

DEST="$HOME/Jarvis/backups/db-$(date +%Y%m%d-%H%M%S)"

cd "$HOME/Jarvis"
DEST="$DEST" python3 - <<'PY'
import os
import sqlite3
from pathlib import Path

from backend.core.store import DB_PATH, ensure_initialized

ensure_initialized()
dest = Path(os.environ["DEST"])
dest.mkdir(parents=True, exist_ok=True)
backup_path = dest / DB_PATH.name

source = sqlite3.connect(DB_PATH)
target = sqlite3.connect(backup_path)
try:
    source.backup(target)
finally:
    target.close()
    source.close()

print(f"SQLite backup created: {dest}")
PY
