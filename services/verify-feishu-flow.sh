#!/usr/bin/env bash
set -euo pipefail

PORT="${JARVIS_WORKBENCH_PORT:-8080}"
BASE_URL="${JARVIS_BASE_URL:-http://127.0.0.1:$PORT}"
STAMP="$(date +%Y%m%d%H%M%S)"
TEXT="明天 10 点提醒我完成 Jarvis 飞书回归验证 $STAMP"
TMP_FILE="$(mktemp)"

cleanup() {
  rm -f "$TMP_FILE"
}
trap cleanup EXIT

curl -fsS -X POST "$BASE_URL/api/feishu/event" \
  -H "Content-Type: application/json" \
  -d "{\"schema\":\"2.0\",\"header\":{\"event_id\":\"evt_verify_$STAMP\",\"event_type\":\"im.message.receive_v1\"},\"event\":{\"sender\":{\"sender_id\":{\"open_id\":\"ou_verify_user\"}},\"message\":{\"message_id\":\"om_verify_$STAMP\",\"chat_id\":\"oc_verify_chat\",\"message_type\":\"text\",\"content\":\"{\\\"text\\\":\\\"$TEXT\\\"}\"}}}" \
  > "$TMP_FILE"

TASK_ID="$(python3 - "$TMP_FILE" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)

record = payload.get("record") or {}
if payload.get("status") != "processed":
    raise SystemExit(f"unexpected status: {payload.get('status')}")
if not record.get("task_id"):
    raise SystemExit("missing task_id")
if not record.get("due_at"):
    raise SystemExit("missing due_at")
print(record["task_id"])
PY
)"

curl -fsS -X POST "$BASE_URL/api/tasks/$TASK_ID/complete" \
  -H "Content-Type: application/json" \
  -d '{}' >/dev/null

echo "Feishu flow verified and test task completed: $TASK_ID"
