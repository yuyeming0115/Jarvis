#!/usr/bin/env bash
set -euo pipefail

for label in com.local.jarvis.workbench com.local.jarvis.maintenance com.local.jarvis.reminders com.local.jarvis.feishu-public-monitor; do
  echo "== $label =="
  if launchctl print "gui/$UID/$label" >/dev/null 2>&1; then
    launchctl print "gui/$UID/$label" | sed -n '1,80p'
  else
    echo "Not loaded"
  fi
done
