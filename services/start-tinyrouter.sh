#!/usr/bin/env bash
set -euo pipefail

ROOT="${JARVIS_ROOT:-$HOME/Jarvis}"
PORT="${TINYROUTER_PORT:-20129}"
BIN="${TINYROUTER_BIN:-$HOME/.local/bin/tinyrouter}"
CONFIG_DIR="$ROOT/config/local/tinyrouter"
CONFIG_FILE="$CONFIG_DIR/config.yaml"
LOG_DIR="$ROOT/logs"
PID_FILE="$LOG_DIR/tinyrouter.pid"

mkdir -p "$CONFIG_DIR" "$LOG_DIR"

if [ ! -x "$BIN" ]; then
  echo "TinyRouter binary not found: $BIN"
  echo "Install it with: $ROOT/services/install-tinyrouter.sh"
  exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
  cat > "$CONFIG_FILE" <<EOF
port: $PORT
consoleLogMaxLines: 200
usageRingSize: 500
enablePlayground: true
rotation:
  strategy: "fill-first"
  stickyLimit: 3
  maxRetries: 5
  retryDelaySec: 5
  backoffMaxSec: 240
  state_persist: true
  state_path: "state.yaml"
providers: []
combos: []
EOF
  echo "Created TinyRouter config: $CONFIG_FILE"
fi

if [ -f "$PID_FILE" ]; then
  OLD_PID="$(cat "$PID_FILE")"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "TinyRouter already running with PID: $OLD_PID"
    echo "Open: http://127.0.0.1:$PORT/"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

EXISTING_PID="$(lsof -ti tcp:"$PORT" || true)"
if [ -n "$EXISTING_PID" ]; then
  echo "Port $PORT is already in use by PID: $EXISTING_PID"
  exit 1
fi

echo "Starting TinyRouter at http://127.0.0.1:$PORT/"
PID="$(
  BIN="$BIN" CONFIG_DIR="$CONFIG_DIR" CONFIG_FILE="$CONFIG_FILE" LOG_DIR="$LOG_DIR" python3 - <<'PY'
import os
import subprocess

stdout = open(os.path.join(os.environ["LOG_DIR"], "tinyrouter.out.log"), "ab")
stderr = open(os.path.join(os.environ["LOG_DIR"], "tinyrouter.err.log"), "ab")
process = subprocess.Popen(
    [os.environ["BIN"], "-config", os.environ["CONFIG_FILE"]],
    cwd=os.environ["CONFIG_DIR"],
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
  if curl -fsS "http://127.0.0.1:$PORT/" >/dev/null 2>&1; then
    echo "TinyRouter started with PID: $PID"
    echo "Open: http://127.0.0.1:$PORT/"
    exit 0
  fi
  sleep 1
done

echo "TinyRouter did not become ready in time."
echo "See logs:"
echo "  $LOG_DIR/tinyrouter.out.log"
echo "  $LOG_DIR/tinyrouter.err.log"
kill "$PID" 2>/dev/null || true
rm -f "$PID_FILE"
exit 1
