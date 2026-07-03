#!/usr/bin/env bash
set -euo pipefail

LAUNCH_DIR="$HOME/Library/LaunchAgents"
WORKBENCH_LABEL="com.local.jarvis.workbench"
MAINTENANCE_LABEL="com.local.jarvis.maintenance"
WORKBENCH_PLIST="$HOME/Jarvis/config/launchd/$WORKBENCH_LABEL.plist"
MAINTENANCE_PLIST="$HOME/Jarvis/config/launchd/$MAINTENANCE_LABEL.plist"

mkdir -p "$LAUNCH_DIR"

bash "$HOME/Jarvis/services/stop-workbench.sh" || true

for label in "$WORKBENCH_LABEL" "$MAINTENANCE_LABEL"; do
  launchctl bootout "gui/$UID/$label" 2>/dev/null || true
done

cp "$WORKBENCH_PLIST" "$LAUNCH_DIR/"
cp "$MAINTENANCE_PLIST" "$LAUNCH_DIR/"

launchctl bootstrap "gui/$UID" "$LAUNCH_DIR/$WORKBENCH_LABEL.plist"
launchctl enable "gui/$UID/$WORKBENCH_LABEL"
launchctl kickstart -k "gui/$UID/$WORKBENCH_LABEL"

launchctl bootstrap "gui/$UID" "$LAUNCH_DIR/$MAINTENANCE_LABEL.plist"
launchctl enable "gui/$UID/$MAINTENANCE_LABEL"

echo "LaunchAgents installed:"
echo "  $LAUNCH_DIR/$WORKBENCH_LABEL.plist"
echo "  $LAUNCH_DIR/$MAINTENANCE_LABEL.plist"
echo "Workbench: http://127.0.0.1:${JARVIS_WORKBENCH_PORT:-8080}/"
