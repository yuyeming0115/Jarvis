#!/usr/bin/env bash
set -euo pipefail

PORT="${JARVIS_WORKBENCH_PORT:-8080}"
APP_DIR="$HOME/Jarvis/apps/workbench"
BACKEND_ENTRY="$HOME/Jarvis/backend/main.py"
LOG_DIR="$HOME/Jarvis/logs"
PID_FILE="$LOG_DIR/workbench.pid"

if [ ! -d "$APP_DIR" ]; then
  echo "Workbench directory not found: $APP_DIR"
  exit 1
fi

if [ ! -f "$BACKEND_ENTRY" ]; then
  echo "Backend entry not found: $BACKEND_ENTRY"
  exit 1
fi

mkdir -p "$LOG_DIR"

if [ -f "$PID_FILE" ]; then
  OLD_PID="$(cat "$PID_FILE")"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Jarvis workbench already appears to be running with PID: $OLD_PID"
    echo "Open: http://127.0.0.1:$PORT/"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

EXISTING_PID="$(lsof -ti tcp:"$PORT" || true)"
if [ -n "$EXISTING_PID" ]; then
  echo "Port $PORT is already in use by PID: $EXISTING_PID"
  echo "Jarvis will not stop unknown processes automatically."
  echo "Choose another port with: JARVIS_WORKBENCH_PORT=8081 bash $HOME/Jarvis/services/start-workbench.sh"
  exit 1
fi

echo "Starting Jarvis workbench at http://127.0.0.1:$PORT/"
SERVER_PID="$(
  BACKEND_ENTRY="$BACKEND_ENTRY" LOG_DIR="$LOG_DIR" PORT="$PORT" python3 - <<'PY'
import os
import subprocess

backend_entry = os.environ["BACKEND_ENTRY"]
log_dir = os.environ["LOG_DIR"]
port = os.environ["PORT"]

stdout_path = os.path.join(log_dir, "workbench.out.log")
stderr_path = os.path.join(log_dir, "workbench.err.log")

stdout = open(stdout_path, "ab")
stderr = open(stderr_path, "ab")
process = subprocess.Popen(
    ["python3", backend_entry],
    env={**os.environ, "JARVIS_WORKBENCH_PORT": port},
    stdout=stdout,
    stderr=stderr,
    start_new_session=True,
    close_fds=True,
)
print(process.pid)
PY
)"
echo "$SERVER_PID" > "$PID_FILE"
echo "Jarvis workbench started with PID: $SERVER_PID"

for _ in 1 2 3 4 5; do
  if curl -fsS "http://127.0.0.1:$PORT/" >/dev/null 2>&1; then
    echo "Jarvis workbench is ready: http://127.0.0.1:$PORT/"
    exit 0
  fi
  sleep 1
done

echo "Jarvis workbench did not become ready in time."
echo "See logs:"
echo "  $LOG_DIR/workbench.out.log"
echo "  $LOG_DIR/workbench.err.log"
kill "$SERVER_PID" 2>/dev/null || true
rm -f "$PID_FILE"
exit 1
