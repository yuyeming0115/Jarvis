#!/usr/bin/env bash
set -euo pipefail

LOG_DIR="$HOME/Jarvis/logs"
MAINTENANCE_LOG="$LOG_DIR/maintenance.log"

mkdir -p "$LOG_DIR"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Jarvis maintenance started"
  bash "$HOME/Jarvis/services/backup-db.sh"
  bash "$HOME/Jarvis/services/export-json.sh"
  bash "$HOME/Jarvis/services/rotate-logs.sh"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Jarvis maintenance completed"
} >> "$MAINTENANCE_LOG" 2>&1
