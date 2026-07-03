#!/usr/bin/env bash
set -euo pipefail

PORT="${JARVIS_FEISHU_RELAY_PORT:-18790}"
LOG_DIR="$HOME/Jarvis/logs"
PID_FILE="$LOG_DIR/feishu-tunnel.pid"
URL_FILE="$HOME/Jarvis/config/local/feishu-tunnel-url"
LOG_FILE="$LOG_DIR/feishu-tunnel.log"

mkdir -p "$LOG_DIR" "$HOME/Jarvis/config/local"

bash "$HOME/Jarvis/services/start-feishu-relay.sh" >/dev/null

if [ -f "$PID_FILE" ]; then
  OLD_PID="$(cat "$PID_FILE")"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Feishu tunnel already running with PID: $OLD_PID"
    bash "$HOME/Jarvis/services/show-feishu-callback-url.sh"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

rm -f "$URL_FILE"
: > "$LOG_FILE"

PID="$(
  PORT="$PORT" LOG_FILE="$LOG_FILE" python3 - <<'PY'
import os
import subprocess

port = os.environ["PORT"]
log_file = os.environ["LOG_FILE"]
log = open(log_file, "ab")
process = subprocess.Popen(
    ["npx", "--yes", "localtunnel", "--port", port, "--local-host", "127.0.0.1"],
    stdout=log,
    stderr=log,
    start_new_session=True,
    close_fds=True,
)
print(process.pid)
PY
)"
echo "$PID" > "$PID_FILE"

for _ in $(seq 1 45); do
  URL="$(sed -nE 's/.*(https:\/\/[^[:space:]]+).*/\1/p' "$LOG_FILE" | tail -n 1 || true)"
  if [ -n "$URL" ]; then
    echo "$URL" > "$URL_FILE"
    echo "Feishu tunnel started with PID: $PID"
    echo "Public callback URL:"
    bash "$HOME/Jarvis/services/show-feishu-callback-url.sh"
    exit 0
  fi
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "Feishu tunnel exited before URL was ready."
    cat "$LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
  fi
  sleep 1
done

echo "Feishu tunnel did not provide a URL in time."
cat "$LOG_FILE"
kill "$PID" 2>/dev/null || true
rm -f "$PID_FILE"
exit 1
