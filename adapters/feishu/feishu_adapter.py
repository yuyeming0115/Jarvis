from __future__ import annotations

import json
import os
from typing import Any

from backend.core.messages import create_message
from backend.core.reminders import parse_due_at_from_text
from backend.core.store import append_log, backup_json, now, update_system_status
from backend.gateway.inbox import route_normalized_message
from adapters.feishu.feishu_cards import (
    build_idea_confirmation_card,
    build_task_confirmation_card,
    build_topic_confirmation_card,
)
from adapters.feishu.feishu_card_actions import handle_card_action
from adapters.feishu.feishu_client import is_configured, send_card_message


class FeishuAdapterError(Exception):
    pass


def handle_feishu_event(payload: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
    headers = headers or {}
    if "encrypt" in payload:
        raise FeishuAdapterError("V2.2 暂不处理加密事件；请先不要在飞书事件订阅中配置 Encrypt Key。")

    if _is_card_action(payload):
        return handle_card_action(payload, headers)

    if _is_url_verification(payload):
        _verify_token(payload)
        append_log("feishu_url_verification", "飞书 URL 验证通过", source="feishu", target="feishu_adapter")
        update_system_status(feishu="callback_verified")
        return {"challenge": payload.get("challenge")}

    _verify_token(payload)
    text = _extract_text(payload)
    if not text:
        append_log("feishu_skip", "飞书事件未包含可处理文本", source="feishu", status="skipped", target="feishu_adapter")
        return {"status": "skipped", "reason": "no_text"}

    backup_json("feishu-message")
    normalized = _normalize_feishu_payload(payload, text)
    record = route_normalized_message(normalized)
    message = create_message(
        {
            "message_id": normalized["message_id"],
            "platform": "feishu",
            "platform_user_id": normalized.get("platform_user_id", ""),
            "chat_id": normalized.get("chat_id", ""),
            "raw_text": text,
            "message_type": normalized.get("message_type", "text"),
            "normalized_intent": normalized["normalized"]["intent"],
            "normalized_payload": normalized["normalized"],
            "source_event": payload,
            "status": "processed",
            "received_at": normalized.get("received_at"),
            "processed_at": now(),
        }
    )
    append_log(
        "feishu_message_process",
        f"飞书消息已处理为：{normalized['normalized']['intent']}",
        source="feishu",
        target=message["message_id"],
    )
    update_system_status(feishu="local_callback_ready")

    _send_confirmation_card(normalized, record)

    return {"status": "processed", "message": message, "record": record}


def _send_confirmation_card(normalized: dict[str, Any], record: dict[str, Any]) -> None:
    if not is_configured():
        return
    chat_id = normalized.get("chat_id", "")
    intent = normalized["normalized"].get("intent", "")
    if not chat_id:
        return

    try:
        if intent == "task":
            card = build_task_confirmation_card(record, normalized["normalized"])
        elif intent == "topic":
            card = build_topic_confirmation_card(record)
        else:
            card = build_idea_confirmation_card(record)
        send_card_message(chat_id, card)
    except Exception as error:
        append_log(
            "feishu_card_send_failed",
            f"发送飞书确认卡片失败：{error}",
            source="feishu",
            status="failed",
            target="feishu_adapter",
        )


def _is_card_action(payload: dict[str, Any]) -> bool:
    return payload.get("type") == "card.action.trigger" or "action" in payload and "value" in payload.get("action", {})


def _is_url_verification(payload: dict[str, Any]) -> bool:
    return payload.get("type") == "url_verification" and "challenge" in payload


def _verify_token(payload: dict[str, Any]) -> None:
    expected = os.environ.get("FEISHU_VERIFICATION_TOKEN", "").strip()
    if not expected:
        return
    actual = payload.get("token") or payload.get("header", {}).get("token") or ""
    if actual != expected:
        raise FeishuAdapterError("飞书 Verification Token 校验失败")


def _extract_text(payload: dict[str, Any]) -> str:
    event = payload.get("event", {})
    message = event.get("message", {})
    content = message.get("content")
    if isinstance(content, str):
        try:
            content_obj = json.loads(content)
        except json.JSONDecodeError:
            return content.strip()
        return str(content_obj.get("text", "")).strip()
    if isinstance(content, dict):
        return str(content.get("text", "")).strip()

    text = event.get("text") or payload.get("text")
    if isinstance(text, str):
        return text.strip()
    return ""


def _normalize_feishu_payload(payload: dict[str, Any], text: str) -> dict[str, Any]:
    event = payload.get("event", {})
    header = payload.get("header", {})
    message = event.get("message", {})
    sender = event.get("sender", {})
    sender_id = sender.get("sender_id", {}) if isinstance(sender, dict) else {}

    normalized = _classify_text(text)
    return {
        "message_id": message.get("message_id") or header.get("event_id") or f"feishu_{now().replace(' ', '_')}",
        "platform": "feishu",
        "platform_user_id": sender_id.get("open_id") or sender_id.get("user_id") or "",
        "chat_id": message.get("chat_id", ""),
        "raw_text": text,
        "message_type": message.get("message_type", "text"),
        "received_at": now(),
        "normalized": normalized,
        "status": "processed",
    }


def _classify_text(text: str) -> dict[str, Any]:
    intent = "idea"
    due_at = parse_due_at_from_text(text)
    if due_at or any(word in text for word in ["提醒", "截止", "到期", "明天", "后天", "周", "星期", "今天", "今晚", "明早"]):
        intent = "task"
    if any(word in text for word in ["选题", "写一篇", "公众号", "小红书", "视频号"]):
        intent = "topic"
    return {"intent": intent, "title": text, "due_at": due_at}
