#!/usr/bin/env bash
set -euo pipefail

PORT="${JARVIS_WORKBENCH_PORT:-8080}"
BACKEND_ENTRY="$HOME/Jarvis/backend/main.py"
LOG_DIR="$HOME/Jarvis/logs"
PID_FILE="$LOG_DIR/workbench.pid"

if [ ! -f "$BACKEND_ENTRY" ]; then
  echo "Backend entry not found: $BACKEND_ENTRY"
  exit 1
fi

mkdir -p "$LOG_DIR"
echo "$$" > "$PID_FILE"

export JARVIS_WORKBENCH_PORT="$PORT"
exec python3 "$BACKEND_ENTRY"
