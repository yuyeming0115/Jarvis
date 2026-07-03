#!/usr/bin/env bash
set -euo pipefail

PID_FILE="$HOME/Jarvis/logs/feishu-tunnel.pid"

if [ ! -f "$PID_FILE" ]; then
  echo "No Feishu tunnel process is recorded."
  exit 0
fi

PID="$(cat "$PID_FILE")"
if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
  echo "Stopping Feishu tunnel PID: $PID"
  kill "$PID"
fi
rm -f "$PID_FILE"
