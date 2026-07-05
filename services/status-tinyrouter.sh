#!/usr/bin/env bash
set -euo pipefail

PORT="${TINYROUTER_PORT:-20129}"
PID_FILE="$HOME/Jarvis/logs/tinyrouter.pid"

if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE")"
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    echo "TinyRouter recorded PID: $PID"
  else
    echo "TinyRouter PID file exists but process is not running."
  fi
else
  echo "No TinyRouter PID file."
fi

if lsof -ti tcp:"$PORT" >/dev/null 2>&1; then
  echo "Port $PORT is listening."
else
  echo "Port $PORT is not listening."
fi

if curl -fsS "http://127.0.0.1:$PORT/" >/dev/null 2>&1; then
  echo "TinyRouter UI: http://127.0.0.1:$PORT/"
else
  echo "TinyRouter UI is not reachable."
fi
