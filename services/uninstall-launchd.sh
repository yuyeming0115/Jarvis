#!/usr/bin/env bash
set -euo pipefail

LAUNCH_DIR="$HOME/Library/LaunchAgents"
WORKBENCH_LABEL="com.local.jarvis.workbench"
MAINTENANCE_LABEL="com.local.jarvis.maintenance"

for label in "$WORKBENCH_LABEL" "$MAINTENANCE_LABEL"; do
  launchctl bootout "gui/$UID/$label" 2>/dev/null || true
  rm -f "$LAUNCH_DIR/$label.plist"
done

rm -f "$HOME/Jarvis/logs/workbench.pid"
echo "Jarvis LaunchAgents removed."
