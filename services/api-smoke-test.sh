#!/usr/bin/env bash
set -euo pipefail

PORT="${JARVIS_WORKBENCH_PORT:-8080}"
BASE_URL="http://127.0.0.1:$PORT"
MODE="${1:-readonly}"

echo "Checking Jarvis API at $BASE_URL"

curl -fsS "$BASE_URL/" >/dev/null
curl -fsS "$BASE_URL/api/system-status" | python3 -m json.tool >/dev/null
curl -fsS "$BASE_URL/api/tasks" | python3 -m json.tool >/dev/null
curl -fsS "$BASE_URL/api/ideas" | python3 -m json.tool >/dev/null
curl -fsS "$BASE_URL/api/topics" | python3 -m json.tool >/dev/null
curl -fsS "$BASE_URL/api/logs" | python3 -m json.tool >/dev/null

echo "Read-only API checks passed."

DATABASE="$(
  curl -fsS "$BASE_URL/api/system-status" | python3 -c '
import json
import sys

print(json.load(sys.stdin).get("database", "unknown"))
'
)"
echo "Current database mode: $DATABASE"

if [ "$MODE" != "--write" ]; then
  echo "Skipped write test. Run with --write to create and complete a test task."
  exit 0
fi

TMP_FILE="$(mktemp)"
curl -fsS -X POST "$BASE_URL/api/tasks" \
  -H "Content-Type: application/json" \
  -d '{"title":"API 写入测试任务","description":"由 api-smoke-test.sh 创建，可在工作台中查看。","project":"Jarvis","priority":"P3"}' \
  > "$TMP_FILE"

TASK_ID="$(python3 - "$TMP_FILE" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    print(json.load(handle)["task_id"])
PY
)"

curl -fsS -X POST "$BASE_URL/api/tasks/$TASK_ID/complete" \
  -H "Content-Type: application/json" \
  -d '{}' >/dev/null

rm -f "$TMP_FILE"
echo "Write API checks passed. Created and completed task: $TASK_ID"
