#!/usr/bin/env bash
set -euo pipefail

SRC="$HOME/Jarvis/apps/workbench/data"
DEST="$HOME/Jarvis/backups/json-$(date +%Y%m%d-%H%M%S)"

if [ ! -d "$SRC" ]; then
  echo "JSON data directory not found: $SRC"
  exit 1
fi

mkdir -p "$DEST"
cp "$SRC"/*.json "$DEST"/
echo "JSON backup created: $DEST"
