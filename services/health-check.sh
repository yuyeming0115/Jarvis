#!/usr/bin/env bash
set -euo pipefail

PORT="${JARVIS_WORKBENCH_PORT:-8080}"
URL="http://127.0.0.1:$PORT/"

curl -fsS "$URL" >/dev/null
echo "Jarvis workbench is online: $URL"
