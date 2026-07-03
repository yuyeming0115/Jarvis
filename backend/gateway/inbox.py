from __future__ import annotations

from typing import Any

from backend.core.ideas import create_idea
from backend.core.store import append_log, backup_json, new_id, now
from backend.core.tasks import create_task
from backend.core.topics import create_topic


def normalize_message(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    intent = "idea"
    if any(word in text for word in ["提醒", "截止", "到期", "明天", "周五", "今天"]):
        intent = "task"
    if any(word in text for word in ["选题", "写一篇", "公众号", "小红书", "视频号"]):
        intent = "topic"
    return {
        "message_id": new_id("msg"),
        "platform": "web",
        "platform_user_id": "local_user",
        "chat_id": "workbench",
        "raw_text": text,
        "message_type": "text",
        "received_at": now(),
        "normalized": {
            "intent": intent
        },
        "status": "processed",
    }


def handle_inbox(payload: dict[str, Any]) -> dict[str, Any]:
    raw_text = payload.get("raw_text", "")
    if not raw_text.strip():
        raise ValueError("消息内容不能为空")

    backup_json("inbox-message")
    message = normalize_message(raw_text)
    intent = message["normalized"]["intent"]
    if intent == "task":
        record = create_task({"title": raw_text, "description": "来自本地 Inbox 的任务。"})
    elif intent == "topic":
        record = create_topic({"title": raw_text, "angle": "来自本地 Inbox 的选题。"})
    else:
        record = create_idea({"raw_text": raw_text, "type": "Inbox"})
    append_log("inbox_process", f"Inbox 消息已处理为：{intent}", target=message["message_id"])
    return {"message": message, "record": record}
