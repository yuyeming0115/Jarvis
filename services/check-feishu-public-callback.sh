#!/usr/bin/env bash
set -euo pipefail

PORT="${JARVIS_FEISHU_RELAY_PORT:-18790}"
TUNNEL_PID_FILE="$HOME/Jarvis/logs/feishu-tunnel.pid"

if ! curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
  bash "$HOME/Jarvis/services/start-feishu-relay.sh"
fi

if [ ! -f "$TUNNEL_PID_FILE" ]; then
  bash "$HOME/Jarvis/services/start-feishu-tunnel.sh"
  exit 0
fi

TUNNEL_PID="$(cat "$TUNNEL_PID_FILE")"
if [ -z "$TUNNEL_PID" ] || ! kill -0 "$TUNNEL_PID" 2>/dev/null; then
  rm -f "$TUNNEL_PID_FILE"
  bash "$HOME/Jarvis/services/start-feishu-tunnel.sh"
fi
