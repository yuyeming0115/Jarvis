#!/usr/bin/env bash
set -euo pipefail

PORT="${JARVIS_WORKBENCH_PORT:-8080}"
BASE_URL="http://127.0.0.1:$PORT"
MODE="${1:-task}"
STAMP="$(date +%Y%m%d%H%M%S)"

post_json() {
  curl -fsS -X POST "$BASE_URL/api/feishu/event" \
    -H "Content-Type: application/json" \
    -d "$1" | python3 -m json.tool
}

case "$MODE" in
  challenge)
    post_json '{"type":"url_verification","challenge":"jarvis-local-challenge"}'
    ;;
  task)
    post_json "{\"schema\":\"2.0\",\"header\":{\"event_id\":\"evt_local_task_$STAMP\",\"event_type\":\"im.message.receive_v1\"},\"event\":{\"sender\":{\"sender_id\":{\"open_id\":\"ou_local_user\"}},\"message\":{\"message_id\":\"om_local_task_$STAMP\",\"chat_id\":\"oc_local_chat\",\"message_type\":\"text\",\"content\":\"{\\\"text\\\":\\\"明天 10 点提醒我完成 Jarvis 飞书入口验收\\\"}\"}}}"
    ;;
  idea)
    post_json "{\"schema\":\"2.0\",\"header\":{\"event_id\":\"evt_local_idea_$STAMP\",\"event_type\":\"im.message.receive_v1\"},\"event\":{\"sender\":{\"sender_id\":{\"open_id\":\"ou_local_user\"}},\"message\":{\"message_id\":\"om_local_idea_$STAMP\",\"chat_id\":\"oc_local_chat\",\"message_type\":\"text\",\"content\":\"{\\\"text\\\":\\\"记录一个灵感：飞书入口应该先做规则分类，再接 AI 分类\\\"}\"}}}"
    ;;
  topic)
    post_json "{\"schema\":\"2.0\",\"header\":{\"event_id\":\"evt_local_topic_$STAMP\",\"event_type\":\"im.message.receive_v1\"},\"event\":{\"sender\":{\"sender_id\":{\"open_id\":\"ou_local_user\"}},\"message\":{\"message_id\":\"om_local_topic_$STAMP\",\"chat_id\":\"oc_local_chat\",\"message_type\":\"text\",\"content\":\"{\\\"text\\\":\\\"写一篇公众号：普通人如何搭建自己的 Jarvis\\\"}\"}}}"
    ;;
  *)
    echo "Usage: $0 [challenge|task|idea|topic]"
    exit 1
    ;;
esac
