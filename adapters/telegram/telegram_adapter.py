from __future__ import annotations

import threading
import time
from typing import Any

from backend.core.ideas import create_idea, list_ideas
from backend.core.messages import create_message
from backend.core.reminders import parse_due_at_from_text
from backend.core.store import append_log, backup_json, now, read_json, update_system_status
from backend.core.tasks import complete_task, create_task, list_tasks
from backend.core.topics import create_topic, list_topics
from backend.gateway.inbox import route_normalized_message
from adapters.telegram.telegram_client import TelegramBot, TelegramClientError, get_bot, is_configured

HELP_TEXT = """
🤖 *Jarvis 命令帮助*

/add <内容> - 新增任务，支持自然语言时间
  例：`/add 明天 10 点提醒我交方案`

/idea <内容> - 记录灵感
  例：`/idea 做一个 AI Agent 日常管理视频`

/topic <内容> - 记录选题
  例：`/topic 写一篇普通人如何用 Agent 的文章`

/today - 查看今日待办
/status - 查看系统状态
/help - 显示此帮助
"""


class TelegramAdapter:
    def __init__(self, bot: TelegramBot):
        self.bot = bot
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="telegram-bot")
        self._thread.start()
        append_log("telegram_start", "Telegram Bot 已启动", source="telegram", target="telegram_adapter")

    def stop(self) -> None:
        self._running = False

    def _run_loop(self) -> None:
        update_system_status(telegram="running")
        while self._running:
            try:
                updates = self.bot.get_updates(timeout=30)
                for update in updates:
                    self._process_update(update)
            except Exception as error:
                append_log(
                    "telegram_error",
                    f"Telegram Bot 出错：{error}",
                    source="telegram",
                    status="failed",
                    target="telegram_adapter",
                )
                time.sleep(5)
        update_system_status(telegram="stopped")

    def _process_update(self, update: dict[str, Any]) -> None:
        message = update.get("message", {})
        if not message:
            return

        user = message.get("from", {})
        user_id = user.get("id", 0)
        chat_id = message.get("chat", {}).get("id", 0)
        text = message.get("text", "").strip()

        if not text:
            return

        if not self.bot.is_user_allowed(user_id):
            self.bot.send_message(chat_id, "⛔️ 你没有权限使用此 Bot。请在 `.env` 中配置 `TELEGRAM_ALLOWED_USER_IDS`。")
            return

        append_log(
            "telegram_message",
            f"Telegram 消息：{text[:50]}",
            source="telegram",
            target=f"tg:{user_id}",
        )

        try:
            reply = self._handle_command(text, user_id, chat_id)
            if reply:
                self.bot.send_message(chat_id, reply)
        except Exception as error:
            self.bot.send_message(chat_id, f"❌ 处理失败：{error}")
            append_log(
                "telegram_command_error",
                f"命令处理失败：{error}",
                source="telegram",
                status="failed",
                target=f"tg:{user_id}",
            )

    def _handle_command(self, text: str, user_id: int, chat_id: int) -> str:
        if text.startswith("/start") or text.startswith("/help"):
            return HELP_TEXT.strip()

        if text.startswith("/today"):
            return self._cmd_today()

        if text.startswith("/status"):
            return self._cmd_status()

        if text.startswith("/add"):
            content = text[4:].strip()
            return self._cmd_add(content, user_id)

        if text.startswith("/idea"):
            content = text[5:].strip()
            return self._cmd_idea(content, user_id)

        if text.startswith("/topic"):
            content = text[6:].strip()
            return self._cmd_topic(content, user_id)

        return (
            "未识别的命令。直接发送文本我也会帮你分类入库，或者发送 /help 查看命令列表。\n\n"
            "提示：不带命令直接发内容，我会自动判断是任务/灵感/选题～"
        )

    def _cmd_today(self) -> str:
        tasks = list_tasks()
        pending = [t for t in tasks if t.get("status") not in ("已完成", "完成", "done")]
        if not pending:
            return "🎉 今天没有待办任务，太棒了！"

        due_tasks = []
        no_due_tasks = []
        for t in pending:
            if t.get("due_at"):
                due_tasks.append(t)
            else:
                no_due_tasks.append(t)

        due_tasks.sort(key=lambda x: x.get("due_at", ""))

        lines = [f"📋 *当前待办（共 {len(pending)} 项）*\n"]
        if due_tasks:
            lines.append("⏰ *有截止时间：*")
            for t in due_tasks[:8]:
                priority = t.get("priority", "P2")
                lines.append(f"  • `{priority}` {t['title']}  _{t.get('due_at', '')}_")
            if len(due_tasks) > 8:
                lines.append(f"  ...还有 {len(due_tasks) - 8} 项")
        if no_due_tasks:
            lines.append("\n📝 *无截止时间：*")
            for t in no_due_tasks[:5]:
                lines.append(f"  • {t['title']}")
            if len(no_due_tasks) > 5:
                lines.append(f"  ...还有 {len(no_due_tasks) - 5} 项")
        return "\n".join(lines)

    def _cmd_status(self) -> str:
        try:
            status = read_json("system-status")
        except Exception:
            return "⚠️ 系统状态读取失败"

        tasks = list_tasks()
        ideas = list_ideas()
        topics = list_topics()
        pending_tasks = len([t for t in tasks if t.get("status") not in ("已完成", "完成", "done")])

        lines = ["🖥️ *Jarvis 系统状态*\n"]
        lines.append(f"  工作台：{'✅ 在线' if status.get('workbench') == 'online' else '❌ 离线'}")
        lines.append(f"  飞书：{'✅ 已配置' if status.get('feishu') not in ('not_configured', None) else '⚪️ 未配置'}")
        lines.append(f"  Telegram：✅ 运行中")
        lines.append(f"  数据库：SQLite")
        lines.append("")
        lines.append(f"  📋 待办任务：{pending_tasks}")
        lines.append(f"  💡 灵感记录：{len(ideas)}")
        lines.append(f"  📰 选题记录：{len(topics)}")
        lines.append(f"  🕐 时间：{now()}")
        return "\n".join(lines)

    def _cmd_add(self, content: str, user_id: int) -> str:
        if not content:
            return "⚠️ 请输入任务内容，例：`/add 明天 10 点提醒我交方案`"

        backup_json("telegram-add-task")
        normalized = {
            "message_id": f"tg_{now().replace(' ', '_')}_{user_id}",
            "platform": "telegram",
            "platform_user_id": str(user_id),
            "chat_id": "telegram",
            "raw_text": content,
            "message_type": "text",
            "received_at": now(),
            "normalized": {
                "intent": "task",
                "title": content,
                "due_at": parse_due_at_from_text(content),
            },
            "status": "processed",
        }
        record = route_normalized_message(normalized)
        create_message(
            {
                "message_id": normalized["message_id"],
                "platform": "telegram",
                "platform_user_id": str(user_id),
                "chat_id": "telegram",
                "raw_text": content,
                "message_type": "text",
                "normalized_intent": "task",
                "normalized_payload": normalized["normalized"],
                "source_event": {"command": "/add"},
                "status": "processed",
                "received_at": normalized["received_at"],
                "processed_at": now(),
            }
        )
        due_at = record.get("due_at", "")
        due_text = f"\n⏰ 到期：{due_at}" if due_at else ""
        return f"✅ *任务已记录*\n{record.get('title', '')}{due_text}"

    def _cmd_idea(self, content: str, user_id: int) -> str:
        if not content:
            return "⚠️ 请输入灵感内容，例：`/idea 做一个 AI Agent 视频`"

        backup_json("telegram-add-idea")
        record = create_idea(
            {
                "raw_text": content,
                "type": "Telegram",
                "source": "telegram",
            }
        )
        create_message(
            {
                "message_id": f"tg_idea_{now().replace(' ', '_')}_{user_id}",
                "platform": "telegram",
                "platform_user_id": str(user_id),
                "chat_id": "telegram",
                "raw_text": content,
                "message_type": "text",
                "normalized_intent": "idea",
                "normalized_payload": {"intent": "idea"},
                "source_event": {"command": "/idea"},
                "status": "processed",
                "received_at": now(),
                "processed_at": now(),
            }
        )
        return f"💡 *灵感已记录*\n{record.get('raw_text', '')[:100]}"

    def _cmd_topic(self, content: str, user_id: int) -> str:
        if not content:
            return "⚠️ 请输入选题内容，例：`/topic 写一篇 Agent 文章`"

        backup_json("telegram-add-topic")
        record = create_topic(
            {
                "title": content[:50],
                "angle": f"来自 Telegram：{content}",
                "source": "telegram",
            }
        )
        create_message(
            {
                "message_id": f"tg_topic_{now().replace(' ', '_')}_{user_id}",
                "platform": "telegram",
                "platform_user_id": str(user_id),
                "chat_id": "telegram",
                "raw_text": content,
                "message_type": "text",
                "normalized_intent": "topic",
                "normalized_payload": {"intent": "topic"},
                "source_event": {"command": "/topic"},
                "status": "processed",
                "received_at": now(),
                "processed_at": now(),
            }
        )
        return f"📰 *选题已记录*\n{record.get('title', '')}"


_telegram_adapter: TelegramAdapter | None = None


def start_telegram_bot() -> bool:
    global _telegram_adapter
    if _telegram_adapter is not None:
        return True
    if not is_configured():
        update_system_status(telegram="not_configured")
        return False
    try:
        bot = get_bot()
        if not bot:
            return False
        _telegram_adapter = TelegramAdapter(bot)
        _telegram_adapter.start()
        return True
    except Exception as error:
        append_log(
            "telegram_start_failed",
            f"Telegram Bot 启动失败：{error}",
            source="telegram",
            status="failed",
            target="telegram_adapter",
        )
        update_system_status(telegram="start_failed")
        return False


def stop_telegram_bot() -> None:
    global _telegram_adapter
    if _telegram_adapter:
        _telegram_adapter.stop()
        _telegram_adapter = None
