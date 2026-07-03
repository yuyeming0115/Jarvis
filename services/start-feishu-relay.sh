#!/usr/bin/env bash
set -euo pipefail

PORT="${JARVIS_FEISHU_RELAY_PORT:-18790}"
LOG_DIR="$HOME/Jarvis/logs"
PID_FILE="$LOG_DIR/feishu-relay.pid"
ENTRY="$HOME/Jarvis/services/feishu-relay.py"

mkdir -p "$LOG_DIR"

if [ -f "$PID_FILE" ]; then
  OLD_PID="$(cat "$PID_FILE")"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Feishu relay already running with PID: $OLD_PID"
    bash "$HOME/Jarvis/services/show-feishu-callback-url.sh" local
    exit 0
  fi
  rm -f "$PID_FILE"
fi

EXISTING_PID="$(lsof -ti tcp:"$PORT" || true)"
if [ -n "$EXISTING_PID" ]; then
  echo "Port $PORT is already in use by PID: $EXISTING_PID"
  exit 1
fi

PID="$(
  ENTRY="$ENTRY" LOG_DIR="$LOG_DIR" PORT="$PORT" python3 - <<'PY'
import os
import subprocess

entry = os.environ["ENTRY"]
log_dir = os.environ["LOG_DIR"]
port = os.environ["PORT"]

stdout = open(os.path.join(log_dir, "feishu-relay.out.log"), "ab")
stderr = open(os.path.join(log_dir, "feishu-relay.err.log"), "ab")
process = subprocess.Popen(
    ["python3", entry],
    env={**os.environ, "JARVIS_FEISHU_RELAY_PORT": port},
    stdout=stdout,
    stderr=stderr,
    start_new_session=True,
    close_fds=True,
)
print(process.pid)
PY
)"
echo "$PID" > "$PID_FILE"

for _ in 1 2 3 4 5; do
  if curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
    echo "Feishu relay started with PID: $PID"
    bash "$HOME/Jarvis/services/show-feishu-callback-url.sh" local
    exit 0
  fi
  sleep 1
done

echo "Feishu relay did not become ready in time."
cat "$LOG_DIR/feishu-relay.err.log" 2>/dev/null || true
kill "$PID" 2>/dev/null || true
rm -f "$PID_FILE"
exit 1
