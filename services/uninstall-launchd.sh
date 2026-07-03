#!/usr/bin/env bash
set -euo pipefail

LAUNCH_DIR="$HOME/Library/LaunchAgents"
WORKBENCH_LABEL="com.local.jarvis.workbench"
MAINTENANCE_LABEL="com.local.jarvis.maintenance"
REMINDERS_LABEL="com.local.jarvis.reminders"
FEISHU_PUBLIC_MONITOR_LABEL="com.local.jarvis.feishu-public-monitor"

for label in "$WORKBENCH_LABEL" "$MAINTENANCE_LABEL" "$REMINDERS_LABEL" "$FEISHU_PUBLIC_MONITOR_LABEL"; do
  launchctl bootout "gui/$UID/$label" 2>/dev/null || true
  rm -f "$LAUNCH_DIR/$label.plist"
done

rm -f "$HOME/Jarvis/logs/workbench.pid"
rm -f "$HOME/Jarvis/logs/reminders.pid"
echo "Jarvis LaunchAgents removed."
