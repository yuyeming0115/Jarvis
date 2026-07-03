#!/usr/bin/env bash
set -euo pipefail

LOG_DIR="$HOME/Jarvis/logs"
MAX_BYTES="${JARVIS_LOG_MAX_BYTES:-1048576}"
KEEP="${JARVIS_LOG_KEEP:-10}"

mkdir -p "$LOG_DIR"

rotate_one() {
  local file="$1"
  if [ ! -f "$file" ]; then
    return 0
  fi

  local size
  size="$(wc -c < "$file" | tr -d ' ')"
  if [ "$size" -lt "$MAX_BYTES" ]; then
    return 0
  fi

  local stamp
  stamp="$(date +%Y%m%d-%H%M%S)"
  mv "$file" "$file.$stamp"
  touch "$file"
  echo "Rotated log: $file"
}

rotate_one "$LOG_DIR/workbench.out.log"
rotate_one "$LOG_DIR/workbench.err.log"
rotate_one "$LOG_DIR/maintenance.log"

find "$LOG_DIR" -type f \( -name "*.log.*" -o -name "maintenance.log.*" \) \
  | sort -r \
  | awk -v keep="$KEEP" 'NR > keep { print }' \
  | while IFS= read -r old_log; do
      rm -f "$old_log"
      echo "Removed old rotated log: $old_log"
    done
