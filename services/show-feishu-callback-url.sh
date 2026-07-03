#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-public}"
PORT="${JARVIS_FEISHU_RELAY_PORT:-18790}"
TOKEN_FILE="$HOME/Jarvis/config/local/feishu-callback-token"
TUNNEL_URL_FILE="$HOME/Jarvis/config/local/feishu-tunnel-url"

if [ ! -f "$TOKEN_FILE" ]; then
  curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null
fi

TOKEN="$(cat "$TOKEN_FILE")"
PATH_PART="/feishu/$TOKEN/event"

if [ "$MODE" = "local" ]; then
  echo "Local relay URL: http://127.0.0.1:$PORT$PATH_PART"
  exit 0
fi

if [ ! -f "$TUNNEL_URL_FILE" ]; then
  echo "No public tunnel URL recorded yet."
  echo "Run: bash $HOME/Jarvis/services/start-feishu-tunnel.sh"
  exit 1
fi

BASE_URL="$(cat "$TUNNEL_URL_FILE")"
echo "$BASE_URL$PATH_PART"
