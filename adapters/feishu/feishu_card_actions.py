from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from backend.core.ideas import list_ideas
from backend.core.store import append_log, now
from backend.core.tasks import complete_task, create_task, patch_task
from backend.core.topics import list_topics
from adapters.feishu.feishu_cards import build_action_result_card
from adapters.feishu.feishu_client import send_card_message


ACTION_LABELS = {
    "complete_task": "标记任务完成",
    "snooze_task": "稍后提醒",
    "list_tasks": "查看任务列表",
    "convert_to_topic": "灵感转选题",
    "convert_to_task": "灵感转任务",
    "complete_topic": "标记选题完成",
    "topic_to_task": "选题转任务",
}


def handle_card_action(payload: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
    action = payload.get("action", {})
    value = action.get("value", {}) if isinstance(action, dict) else {}
    action_type = value.get("action", "")
    open_id = payload.get("open_id", "")
    open_message_id = payload.get("open_message_id", "")

    if not action_type:
        return _error_response("未识别的按钮动作")

    append_log(
        "feishu_card_action",
        f"飞书卡片按钮点击：{action_type} {json.dumps(value, ensure_ascii=False)}",
        source="feishu",
        target=f"card:{open_message_id}",
    )

    handler = _ACTION_HANDLERS.get(action_type)
    if not handler:
        return _error_response(f"未支持的动作：{action_type}")

    try:
        result_card = handler(value)
    except Exception as error:
        append_log(
            "feishu_card_action_error",
            f"处理卡片动作失败：{error}",
            source="feishu",
            status="failed",
            target=f"card:{open_message_id}",
        )
        return _toast_response(f"操作失败：{error}", toast_type="error")

    chat_id = _extract_chat_id(payload)
    if chat_id and result_card:
        try:
            send_card_message(chat_id, result_card)
        except Exception as error:
            append_log("feishu_reply_error", f"发送飞书回复失败：{error}", source="feishu", status="failed")

    return _toast_response("操作成功")


def _extract_chat_id(payload: dict[str, Any]) -> str:
    context = payload.get("context", {}) if isinstance(payload.get("context"), dict) else {}
    open_chat_id = context.get("open_chat_id", "")
    return open_chat_id


def _handle_complete_task(value: dict[str, Any]) -> dict[str, Any]:
    task_id = value.get("task_id", "")
    if not task_id:
        raise ValueError("缺少 task_id")
    task = complete_task(task_id)
    return build_action_result_card(
        "✅ 任务已完成",
        f"**{task.get('title', '')}** 已标记为完成。",
        template="green",
    )


def _handle_snooze_task(value: dict[str, Any]) -> dict[str, Any]:
    task_id = value.get("task_id", "")
    minutes = int(value.get("minutes", 60))
    if not task_id:
        raise ValueError("缺少 task_id")

    new_due = datetime.now() + timedelta(minutes=minutes)
    new_due_str = new_due.strftime("%Y-%m-%d %H:%M")
    task = patch_task(task_id, {"due_at": new_due_str, "reminder_level": "due"})

    if minutes >= 60 * 24:
        label = f"{minutes // 60 // 24} 天后"
    elif minutes >= 60:
        label = f"{minutes // 60} 小时后"
    else:
        label = f"{minutes} 分钟后"

    return build_action_result_card(
        "⏰ 提醒已延后",
        f"**{task.get('title', '')}** 将在 {label}（{new_due_str}）再次提醒。",
        template="blue",
    )


def _handle_list_tasks(value: dict[str, Any]) -> dict[str, Any]:
    from backend.core.tasks import list_tasks
    tasks = list_tasks()
    pending = [t for t in tasks if t.get("status") not in ("已完成", "完成", "done")]
    lines = []
    for t in pending[:5]:
        due = f" ⏰ {t.get('due_at', '')}" if t.get("due_at") else ""
        lines.append(f"- {t.get('title', '')}{due}")
    more = f"\n...还有 {len(pending) - 5} 个任务" if len(pending) > 5 else ""
    content = "\n".join(lines) if lines else "当前没有待办任务 🎉"
    return build_action_result_card(
        f"📋 当前待办（{len(pending)}）",
        content + more,
        template="blue",
    )


def _handle_convert_to_topic(value: dict[str, Any]) -> dict[str, Any]:
    idea_id = value.get("idea_id", "")
    ideas = [i for i in list_ideas() if i.get("idea_id") == idea_id]
    if not ideas:
        raise ValueError("灵感不存在")
    idea = ideas[0]
    from backend.core.topics import create_topic
    topic = create_topic(
        {
            "title": idea.get("raw_text", "")[:50],
            "angle": f"从灵感转化：{idea.get('raw_text', '')}",
            "source": "feishu_card",
        }
    )
    return build_action_result_card(
        "📰 已转为选题",
        f"**{topic.get('title', '')}** 已创建为选题。",
        template="green",
    )


def _handle_convert_to_task(value: dict[str, Any]) -> dict[str, Any]:
    idea_id = value.get("idea_id", "")
    ideas = [i for i in list_ideas() if i.get("idea_id") == idea_id]
    if not ideas:
        raise ValueError("灵感不存在")
    idea = ideas[0]
    task = create_task(
        {
            "title": idea.get("raw_text", "")[:50],
            "description": f"从灵感转化：{idea.get('raw_text', '')}",
            "source": "feishu_card",
            "priority": "P2",
        }
    )
    return build_action_result_card(
        "📋 已转为任务",
        f"**{task.get('title', '')}** 已创建为任务。",
        template="green",
    )


def _handle_complete_topic(value: dict[str, Any]) -> dict[str, Any]:
    topic_id = value.get("topic_id", "")
    if not topic_id:
        raise ValueError("缺少 topic_id")
    topics = [t for t in list_topics() if t.get("topic_id") == topic_id]
    if not topics:
        raise ValueError("选题不存在")
    from backend.core.topics import patch_topic
    topic = patch_topic(topic_id, {"status": "已完成"})
    return build_action_result_card(
        "✅ 选题已完成",
        f"**{topic.get('title', '')}** 已标记为完成。",
        template="green",
    )


def _handle_topic_to_task(value: dict[str, Any]) -> dict[str, Any]:
    topic_id = value.get("topic_id", "")
    topics = [t for t in list_topics() if t.get("topic_id") == topic_id]
    if not topics:
        raise ValueError("选题不存在")
    topic = topics[0]
    task = create_task(
        {
            "title": topic.get("title", "")[:50],
            "description": f"从选题转化：{topic.get('angle', '')}",
            "source": "feishu_card",
            "priority": "P2",
        }
    )
    return build_action_result_card(
        "📋 已转为任务",
        f"**{task.get('title', '')}** 已创建为任务。",
        template="green",
    )


_ACTION_HANDLERS = {
    "complete_task": _handle_complete_task,
    "snooze_task": _handle_snooze_task,
    "list_tasks": _handle_list_tasks,
    "convert_to_topic": _handle_convert_to_topic,
    "convert_to_task": _handle_convert_to_task,
    "complete_topic": _handle_complete_topic,
    "topic_to_task": _handle_topic_to_task,
}


def _toast_response(message: str, toast_type: str = "info") -> dict[str, Any]:
    return {
        "toast": {"type": toast_type, "content": message},
    }


def _error_response(message: str) -> dict[str, Any]:
    append_log("feishu_card_action_error", message, source="feishu", status="failed")
    return _toast_response(message, toast_type="error")
