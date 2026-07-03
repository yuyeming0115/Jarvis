#!/usr/bin/env bash
set -euo pipefail

DB="$HOME/Jarvis/backend/db/jarvis.sqlite3"
DEST="$HOME/Jarvis/backups/db-$(date +%Y%m%d-%H%M%S)"

if [ ! -f "$DB" ]; then
  echo "SQLite database not found: $DB"
  echo "Run: bash $HOME/Jarvis/services/init-sqlite.sh"
  exit 1
fi

mkdir -p "$DEST"
cp "$DB" "$DEST/"
for suffix in "-wal" "-shm"; do
  if [ -f "$DB$suffix" ]; then
    cp "$DB$suffix" "$DEST/"
  fi
done

echo "SQLite backup created: $DEST"
