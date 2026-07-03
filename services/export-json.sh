#!/usr/bin/env bash
set -euo pipefail

DEST="${1:-$HOME/Jarvis/backups/export-json-$(date +%Y%m%d-%H%M%S)}"

cd "$HOME/Jarvis"
DEST="$DEST" python3 - <<'PY'
import os
from pathlib import Path

from backend.core.store import export_json

dest = Path(os.environ["DEST"])
export_json(dest)
print(f"JSON export created: {dest}")
PY
