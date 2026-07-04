from __future__ import annotations

from typing import Any


INTENT_LABELS = {
    "task": "📋 任务",
    "idea": "💡 灵感",
    "topic": "📰 选题",
}


def build_task_confirmation_card(task: dict[str, Any], normalized: dict[str, Any]) -> dict[str, Any]:
    task_id = task["task_id"]
    due_at = task.get("due_at", "")
    due_label = f"⏰ 到期：{due_at}" if due_at else "⏰ 无截止时间"

    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "📋 任务已记录"},
            "template": "blue",
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{task.get('title', '未命名任务')}**\n{due_label}",
                },
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "✅ 完成"},
                        "type": "primary",
                        "value": {"action": "complete_task", "task_id": task_id},
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "⏰ 稍后提醒"},
                        "type": "default",
                        "value": {"action": "snooze_task", "task_id": task_id},
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📋 查看列表"},
                        "type": "default",
                        "value": {"action": "list_tasks", "task_id": task_id},
                    },
                ],
            },
        ],
    }
    return card


def build_idea_confirmation_card(idea: dict[str, Any]) -> dict[str, Any]:
    idea_id = idea["idea_id"]
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "💡 灵感已记录"},
            "template": "purple",
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{idea.get('raw_text', '')[:100]}**",
                },
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📰 转为选题"},
                        "type": "primary",
                        "value": {"action": "convert_to_topic", "idea_id": idea_id},
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📋 转为任务"},
                        "type": "default",
                        "value": {"action": "convert_to_task", "idea_id": idea_id},
                    },
                ],
            },
        ],
    }
    return card


def build_topic_confirmation_card(topic: dict[str, Any]) -> dict[str, Any]:
    topic_id = topic["topic_id"]
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "📰 选题已记录"},
            "template": "green",
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{topic.get('title', '')}**",
                },
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "✅ 完成"},
                        "type": "primary",
                        "value": {"action": "complete_topic", "topic_id": topic_id},
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📋 转为任务"},
                        "type": "default",
                        "value": {"action": "topic_to_task", "topic_id": topic_id},
                    },
                ],
            },
        ],
    }
    return card


def build_task_reminder_card(task: dict[str, Any]) -> dict[str, Any]:
    task_id = task["task_id"]
    due_at = task.get("due_at", "")
    priority = task.get("priority", "P2")
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "⏰ 任务到期提醒"},
            "template": "red",
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{task.get('title', '未命名任务')}**\n⏰ 到期：{due_at}\n🏷️ 优先级：{priority}",
                },
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "✅ 已完成"},
                        "type": "primary",
                        "value": {"action": "complete_task", "task_id": task_id},
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "⏰ 1小时后提醒"},
                        "type": "default",
                        "value": {"action": "snooze_task", "task_id": task_id, "minutes": 60},
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "⏰ 明天再提醒"},
                        "type": "default",
                        "value": {"action": "snooze_task", "task_id": task_id, "minutes": 60 * 24},
                    },
                ],
            },
        ],
    }
    return card


def build_action_result_card(title: str, content: str, template: str = "green") -> dict[str, Any]:
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": template,
        },
        "elements": [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": content},
            },
        ],
    }
