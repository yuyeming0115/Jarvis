from __future__ import annotations

from typing import Any

from .store import new_id, now, read_json, write_json


def list_messages() -> list[dict[str, Any]]:
    return read_json("messages")


def create_message(payload: dict[str, Any]) -> dict[str, Any]:
    messages = list_messages()
    timestamp = now()
    message = {
        "message_id": payload.get("message_id") or new_id("msg"),
        "platform": payload.get("platform", "unknown"),
        "platform_user_id": payload.get("platform_user_id", ""),
        "chat_id": payload.get("chat_id", ""),
        "raw_text": payload.get("raw_text", "").strip(),
        "message_type": payload.get("message_type", "text"),
        "normalized_intent": payload.get("normalized_intent", "unknown"),
        "normalized_payload": payload.get("normalized_payload", {}),
        "source_event": payload.get("source_event", {}),
        "status": payload.get("status", "processed"),
        "error_message": payload.get("error_message"),
        "received_at": payload.get("received_at") or timestamp,
        "processed_at": payload.get("processed_at") or timestamp,
        "created_at": payload.get("created_at") or timestamp,
    }
    if not message["raw_text"]:
        raise ValueError("消息内容不能为空")
    messages.append(message)
    write_json("messages", messages)
    return message
