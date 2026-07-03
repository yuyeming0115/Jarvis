from __future__ import annotations

from typing import Any

from .store import append_log, backup_json, new_id, now, read_json, update_system_status, write_json


def list_tasks() -> list[dict[str, Any]]:
    return read_json("tasks")


def create_task(payload: dict[str, Any]) -> dict[str, Any]:
    backup_json("create-task")
    tasks = list_tasks()
    timestamp = now()
    task = {
        "task_id": new_id("task"),
        "title": payload.get("title", "").strip(),
        "description": payload.get("description", "").strip(),
        "project": payload.get("project", "Jarvis").strip() or "Jarvis",
        "source": payload.get("source", "local-api"),
        "due_at": payload.get("due_at", "").strip(),
        "priority": payload.get("priority", "P2"),
        "status": "未开始",
        "reminder_level": payload.get("reminder_level", "none"),
        "tags": payload.get("tags", []),
        "external_id": None,
        "sync_status": "local_only",
        "completed_at": None,
        "deleted_at": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    if not task["title"]:
        raise ValueError("任务标题不能为空")
    tasks.append(task)
    write_json("tasks", tasks)
    append_log("task_create", f"新增任务：{task['title']}", target=task["task_id"])
    update_system_status(backend_api="enabled")
    return task


def patch_task(task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    backup_json("patch-task")
    tasks = list_tasks()
    for task in tasks:
        if task.get("task_id") == task_id:
            for key in ["title", "description", "project", "due_at", "priority", "status", "reminder_level", "tags"]:
                if key in payload:
                    task[key] = payload[key]
            task["updated_at"] = now()
            write_json("tasks", tasks)
            append_log("task_update", f"更新任务：{task.get('title', task_id)}", target=task_id)
            update_system_status(backend_api="enabled")
            return task
    raise KeyError("任务不存在")


def complete_task(task_id: str) -> dict[str, Any]:
    backup_json("complete-task")
    tasks = list_tasks()
    for task in tasks:
        if task.get("task_id") == task_id:
            timestamp = now()
            task["status"] = "已完成"
            task["completed_at"] = timestamp
            task["updated_at"] = timestamp
            write_json("tasks", tasks)
            append_log("task_complete", f"完成任务：{task.get('title', task_id)}", target=task_id)
            update_system_status(backend_api="enabled")
            return task
    raise KeyError("任务不存在")
