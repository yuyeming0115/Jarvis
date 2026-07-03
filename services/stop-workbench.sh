#!/usr/bin/env bash
set -euo pipefail

PORT="${JARVIS_WORKBENCH_PORT:-8080}"
LOG_DIR="$HOME/Jarvis/logs"
PID_FILE="$LOG_DIR/workbench.pid"

if [ ! -f "$PID_FILE" ]; then
  PID="$(lsof -ti tcp:"$PORT" || true)"
  if [ -n "$PID" ]; then
    echo "Port $PORT is in use by PID: $PID, but no Jarvis PID file was found."
    echo "Not stopping an unknown process automatically."
    exit 1
  fi
  echo "No Jarvis workbench process is recorded."
  exit 0
fi

PID="$(cat "$PID_FILE")"
if [ -z "$PID" ] || ! kill -0 "$PID" 2>/dev/null; then
  rm -f "$PID_FILE"
  echo "Recorded Jarvis process is not running."
  exit 0
fi

COMMAND="$(ps -p "$PID" -o command= || true)"
case "$COMMAND" in
  *"python3"*"Jarvis/backend/main.py"*|*"Python"*"Jarvis/backend/main.py"*|*"python3 -m http.server"*"$PORT"*|*"Python"*"-m http.server"*"$PORT"*)
    echo "Stopping Jarvis workbench PID: $PID"
    kill "$PID"
    rm -f "$PID_FILE"
    ;;
  *)
    echo "PID $PID does not look like the Jarvis workbench:"
    echo "$COMMAND"
    echo "Not stopping it automatically."
    exit 1
    ;;
esac
