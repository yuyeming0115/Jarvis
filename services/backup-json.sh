#!/usr/bin/env bash
set -euo pipefail

DEST="$HOME/Jarvis/backups/json-$(date +%Y%m%d-%H%M%S)"

bash "$HOME/Jarvis/services/export-json.sh" "$DEST"
