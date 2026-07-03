#!/usr/bin/env bash
set -euo pipefail

LOG_DIR="$HOME/Jarvis/logs"
PID_FILE="$LOG_DIR/reminders.pid"

mkdir -p "$LOG_DIR"
echo "$$" > "$PID_FILE"

if [ -f "$HOME/Jarvis/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$HOME/Jarvis/.env"
  set +a
fi

cd "$HOME/Jarvis"
exec python3 -m backend.core.reminders
