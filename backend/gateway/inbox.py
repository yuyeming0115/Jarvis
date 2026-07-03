from __future__ import annotations

from typing import Any

from backend.core.ideas import create_idea
from backend.core.messages import create_message
from backend.core.reminders import parse_due_at_from_text
from backend.core.store import append_log, backup_json, new_id, now
from backend.core.tasks import create_task
from backend.core.topics import create_topic


def normalize_message(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    due_at = parse_due_at_from_text(text)
    intent = "idea"
    if due_at or any(word in text for word in ["提醒", "截止", "到期", "明天", "后天", "周", "星期", "今天", "今晚", "明早"]):
        intent = "task"
    if any(word in text for word in ["选题", "写一篇", "公众号", "小红书", "视频号"]):
        intent = "topic"
    normalized = {
        "message_id": new_id("msg"),
        "platform": "web",
        "platform_user_id": "local_user",
        "chat_id": "workbench",
        "raw_text": text,
        "message_type": "text",
        "received_at": now(),
        "normalized": {
            "intent": intent,
            "due_at": due_at,
        },
        "status": "processed",
    }
    return normalized


def handle_inbox(payload: dict[str, Any]) -> dict[str, Any]:
    raw_text = payload.get("raw_text", "")
    if not raw_text.strip():
        raise ValueError("消息内容不能为空")

    backup_json("inbox-message")
    message = normalize_message(raw_text)
    record = route_normalized_message(message)
    create_message(
        {
            "message_id": message["message_id"],
            "platform": message["platform"],
            "platform_user_id": message["platform_user_id"],
            "chat_id": message["chat_id"],
            "raw_text": raw_text,
            "message_type": message["message_type"],
            "normalized_intent": message["normalized"]["intent"],
            "normalized_payload": message["normalized"],
            "source_event": payload,
            "status": "processed",
            "received_at": message["received_at"],
            "processed_at": now(),
        }
    )
    intent = message["normalized"]["intent"]
    append_log("inbox_process", f"Inbox 消息已处理为：{intent}", target=message["message_id"])
    return {"message": message, "record": record}


def route_normalized_message(message: dict[str, Any]) -> dict[str, Any]:
    intent = message["normalized"]["intent"]
    raw_text = message["raw_text"]
    if intent == "task":
        return create_task(
            {
                "title": raw_text,
                "description": f"来自 {message.get('platform', 'inbox')} 的任务。",
                "source": message.get("platform", "inbox"),
                "due_at": message.get("normalized", {}).get("due_at", ""),
                "reminder_level": "due" if message.get("normalized", {}).get("due_at") else "none",
            }
        )
    if intent == "topic":
        return create_topic(
            {
                "title": raw_text,
                "angle": f"来自 {message.get('platform', 'inbox')} 的选题。",
                "source": message.get("platform", "inbox"),
            }
        )
    return create_idea(
        {
            "raw_text": raw_text,
            "type": message.get("platform", "Inbox"),
            "source": message.get("platform", "inbox"),
        }
    )
