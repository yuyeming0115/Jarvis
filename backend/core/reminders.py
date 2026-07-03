from __future__ import annotations

import argparse
import re
import subprocess
import time
from datetime import datetime, timedelta
from typing import Any

from .store import append_log, connect, ensure_initialized, now, update_system_status


DATE_TIME_FORMAT = "%Y-%m-%d %H:%M"
CHECK_INTERVAL_SECONDS = 60

WEEKDAY_INDEX = {
    "一": 0,
    "二": 1,
    "三": 2,
    "四": 3,
    "五": 4,
    "六": 5,
    "日": 6,
    "天": 6,
}


def parse_due_at_from_text(text: str, base: datetime | None = None) -> str:
    base = base or datetime.now()
    clean_text = text.strip()
    if not clean_text:
        return ""

    target_date = _parse_date(clean_text, base)
    target_time = _parse_time(clean_text)
    if not target_date and not target_time:
        return ""

    if not target_date:
        target_date = base.date()
    if not target_time:
        target_time = _default_time_for_text(clean_text)

    due_at = datetime.combine(target_date, target_time)
    if due_at <= base and not _has_explicit_date(clean_text):
        due_at += timedelta(days=1)
    return due_at.strftime(DATE_TIME_FORMAT)


def due_at_to_datetime(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in [DATE_TIME_FORMAT, "%Y-%m-%d %H:%M:%S"]:
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def get_due_tasks(reference: datetime | None = None) -> list[dict[str, Any]]:
    ensure_initialized()
    reference = reference or datetime.now()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT task_id, title, due_at, priority, source, reminder_level
            FROM tasks
            WHERE COALESCE(due_at, '') != ''
              AND COALESCE(status, '') NOT IN ('已完成', '完成', 'done')
              AND COALESCE(deleted_at, '') = ''
              AND task_id NOT IN (
                SELECT task_id
                FROM reminder_notifications
                WHERE status = 'sent'
              )
            ORDER BY due_at ASC
            """
        ).fetchall()

    due_tasks: list[dict[str, Any]] = []
    for row in rows:
        due_time = due_at_to_datetime(row["due_at"])
        if due_time and due_time <= reference:
            due_tasks.append(dict(row))
    return due_tasks


def mark_notified(task_id: str, due_at: str, channel: str = "macos") -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO reminder_notifications (
              task_id, due_at, notified_at, channel, status
            )
            VALUES (?, ?, ?, ?, 'sent')
            ON CONFLICT(task_id) DO UPDATE SET
              due_at = excluded.due_at,
              notified_at = excluded.notified_at,
              channel = excluded.channel,
              status = excluded.status
            """,
            (task_id, due_at, now(), channel),
        )


def send_macos_notification(task: dict[str, Any]) -> None:
    title = "Jarvis 提醒"
    due_at = task.get("due_at") or ""
    body = f"{task.get('title', '未命名任务')}\n到期时间：{due_at}"
    script = """
on run argv
  display notification (item 2 of argv) with title (item 1 of argv) sound name "Glass"
end run
"""
    subprocess.run(["osascript", "-e", script, title, body], check=True)


def process_due_reminders(dry_run: bool = False) -> list[dict[str, Any]]:
    due_tasks = get_due_tasks()
    for task in due_tasks:
        if not dry_run:
            send_macos_notification(task)
            mark_notified(task["task_id"], task.get("due_at", ""))
        append_log(
            "reminder_sent" if not dry_run else "reminder_due",
            f"提醒任务：{task.get('title', task['task_id'])}",
            source="reminder",
            target=task["task_id"],
        )
    return due_tasks


def run_loop() -> None:
    ensure_initialized()
    update_system_status(reminders="enabled")
    append_log("reminder_service_start", "Jarvis 提醒服务已启动", source="reminder", target="macos")
    while True:
        try:
            process_due_reminders()
        except Exception as error:
            append_log("reminder_service_error", str(error), status="failed", source="reminder", target="macos")
        time.sleep(CHECK_INTERVAL_SECONDS)


def _parse_date(text: str, base: datetime):
    if "后天" in text:
        return (base + timedelta(days=2)).date()
    if "明天" in text or "明日" in text or "明早" in text or "明晚" in text:
        return (base + timedelta(days=1)).date()
    if "今天" in text or "今日" in text or "今晚" in text or "今早" in text:
        return base.date()

    month_day = re.search(r"(?P<month>\d{1,2})\s*月\s*(?P<day>\d{1,2})\s*[日号]?", text)
    if month_day:
        month = int(month_day.group("month"))
        day = int(month_day.group("day"))
        year = base.year
        candidate = datetime(year, month, day).date()
        if candidate < base.date():
            candidate = datetime(year + 1, month, day).date()
        return candidate

    weekday = re.search(r"(?:周|星期|礼拜)(?P<weekday>[一二三四五六日天])", text)
    if weekday:
        target = WEEKDAY_INDEX[weekday.group("weekday")]
        delta = (target - base.weekday()) % 7
        if delta == 0:
            delta = 7
        return (base + timedelta(days=delta)).date()
    return None


def _parse_time(text: str):
    colon_time = re.search(r"(?P<hour>\d{1,2})\s*[:：]\s*(?P<minute>\d{1,2})", text)
    if colon_time:
        return _normalize_time(text, int(colon_time.group("hour")), int(colon_time.group("minute")))

    point_time = re.search(r"(?P<hour>\d{1,2})\s*[点时](?P<half>半)?(?:(?P<minute>\d{1,2})\s*分?)?", text)
    if point_time:
        minute = 30 if point_time.group("half") else int(point_time.group("minute") or 0)
        return _normalize_time(text, int(point_time.group("hour")), minute)
    return None


def _normalize_time(text: str, hour: int, minute: int):
    if any(word in text for word in ["下午", "晚上", "今晚", "傍晚"]) and hour < 12:
        hour += 12
    if any(word in text for word in ["中午"]) and hour < 11:
        hour += 12
    hour = max(0, min(hour, 23))
    minute = max(0, min(minute, 59))
    return datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0).time()


def _default_time_for_text(text: str):
    if "明早" in text or "早上" in text or "上午" in text:
        hour = 9
    elif "今晚" in text or "明晚" in text or "晚上" in text:
        hour = 21
    else:
        hour = 9
    return datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0).time()


def _has_explicit_date(text: str) -> bool:
    return any(word in text for word in ["今天", "今日", "今晚", "今早", "明天", "明日", "明早", "明晚", "后天"]) or bool(
        re.search(r"\d{1,2}\s*月\s*\d{1,2}\s*[日号]?", text)
    ) or bool(re.search(r"(?:周|星期|礼拜)[一二三四五六日天]", text))


def main() -> None:
    parser = argparse.ArgumentParser(description="Jarvis reminder scheduler")
    parser.add_argument("--once", action="store_true", help="run one scan and exit")
    parser.add_argument("--dry-run", action="store_true", help="do not send notifications or mark tasks")
    parser.add_argument("--parse", help="parse a text reminder and print due_at")
    args = parser.parse_args()

    if args.parse:
        print(parse_due_at_from_text(args.parse))
        return
    if args.once:
        due_tasks = process_due_reminders(dry_run=args.dry_run)
        print(f"due_tasks={len(due_tasks)}")
        return
    run_loop()


if __name__ == "__main__":
    main()
