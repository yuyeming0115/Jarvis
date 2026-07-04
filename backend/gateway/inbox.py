from __future__ import annotations

from typing import Any

from backend.core.ideas import create_idea
from backend.core.llm import LLMClientError, classify_message, is_llm_configured
from backend.core.messages import create_message
from backend.core.reminders import parse_due_at_from_text
from backend.core.store import append_log, backup_json, new_id, now
from backend.core.tasks import create_task
from backend.core.topics import create_topic


def _rule_based_classify(text: str) -> dict[str, Any]:
    due_at = parse_due_at_from_text(text)
    intent = "idea"
    if due_at or any(word in text for word in ["提醒", "截止", "到期", "明天", "后天", "周", "星期", "今天", "今晚", "明早", "记得", "需要"]):
        intent = "task"
    if any(word in text for word in ["选题", "写一篇", "公众号", "小红书", "视频号", "做一期", "写个"]):
        intent = "topic"
    return {
        "intent": intent,
        "title": text[:50],
        "due_at": due_at,
        "confidence": 0.6,
        "reason": "规则匹配",
        "used_llm": False,
    }


def classify_text(text: str) -> dict[str, Any]:
    if is_llm_configured():
        try:
            result = classify_message(text)
            if result.get("intent") == "confirm" and result.get("confidence", 0) < 0.7:
                rule_result = _rule_based_classify(text)
                if rule_result["intent"] != "idea":
                    append_log(
                        "ai_classify_fallback",
                        f"AI 分类为 confirm，回退到规则分类：{rule_result['intent']}",
                        source="ai",
                    )
                    return rule_result
            append_log(
                "ai_classify_success",
                f"AI 分类：{result['intent']} (confidence={result.get('confidence', 0):.2f}) - {result.get('reason', '')}",
                source="ai",
            )
            return result
        except LLMClientError as error:
            append_log(
                "ai_classify_error",
                f"AI 分类失败，回退到规则：{error}",
                source="ai",
                status="failed",
            )
    return _rule_based_classify(text)


def normalize_message(raw_text: str, platform: str = "web", platform_user_id: str = "local_user", chat_id: str = "workbench") -> dict[str, Any]:
    text = raw_text.strip()
    classification = classify_text(text)

    intent = classification.get("intent", "idea")
    due_at = classification.get("due_at") or parse_due_at_from_text(text)
    title = classification.get("title", text[:50])

    normalized = {
        "message_id": new_id("msg"),
        "platform": platform,
        "platform_user_id": platform_user_id,
        "chat_id": chat_id,
        "raw_text": text,
        "message_type": "text",
        "received_at": now(),
        "normalized": {
            "intent": intent,
            "title": title,
            "due_at": due_at,
            "classification_source": "llm" if classification.get("used_llm") else "rule",
            "confidence": classification.get("confidence", 0),
        },
        "status": "processed" if intent != "confirm" else "needs_confirmation",
    }
    return normalized


def handle_inbox(payload: dict[str, Any]) -> dict[str, Any]:
    raw_text = payload.get("raw_text", "")
    if not raw_text.strip():
        raise ValueError("消息内容不能为空")

    platform = payload.get("platform", "web")
    platform_user_id = payload.get("platform_user_id", "local_user")
    chat_id = payload.get("chat_id", "workbench")

    backup_json("inbox-message")
    message = normalize_message(raw_text, platform=platform, platform_user_id=platform_user_id, chat_id=chat_id)

    intent = message["normalized"]["intent"]
    if intent == "confirm":
        create_message(
            {
                "message_id": message["message_id"],
                "platform": platform,
                "platform_user_id": platform_user_id,
                "chat_id": chat_id,
                "raw_text": raw_text,
                "message_type": message["message_type"],
                "normalized_intent": "confirm",
                "normalized_payload": message["normalized"],
                "source_event": payload,
                "status": "needs_confirmation",
                "received_at": message["received_at"],
                "processed_at": now(),
            }
        )
        append_log("inbox_confirm", f"消息需要确认：{raw_text[:50]}", target=message["message_id"])
        return {
            "message": message,
            "record": None,
            "reply": "我没太理解这是要记录任务、灵感还是选题，可以再说清楚一点吗？或者用 /add、/idea、/topic 命令告诉我。",
        }

    record = route_normalized_message(message)
    create_message(
        {
            "message_id": message["message_id"],
            "platform": platform,
            "platform_user_id": platform_user_id,
            "chat_id": chat_id,
            "raw_text": raw_text,
            "message_type": message["message_type"],
            "normalized_intent": intent,
            "normalized_payload": message["normalized"],
            "source_event": payload,
            "status": "processed",
            "received_at": message["received_at"],
            "processed_at": now(),
        }
    )
    append_log("inbox_process", f"Inbox 消息已处理为：{intent}", target=message["message_id"])
    return {"message": message, "record": record}


def route_normalized_message(message: dict[str, Any]) -> dict[str, Any]:
    intent = message["normalized"]["intent"]
    raw_text = message["raw_text"]
    title = message["normalized"].get("title") or raw_text[:50]
    due_at = message["normalized"].get("due_at")
    source = message.get("platform", "inbox")

    if intent == "task":
        return create_task(
            {
                "title": title,
                "description": raw_text if title != raw_text else f"来自 {source} 的任务。",
                "source": source,
                "due_at": due_at or "",
                "reminder_level": "due" if due_at else "none",
            }
        )
    if intent == "topic":
        return create_topic(
            {
                "title": title,
                "angle": raw_text if title != raw_text else f"来自 {source} 的选题。",
                "source": source,
            }
        )
    return create_idea(
        {
            "raw_text": raw_text,
            "type": source,
            "source": source,
        }
    )
