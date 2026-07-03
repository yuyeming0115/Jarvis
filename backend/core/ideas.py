from __future__ import annotations

from typing import Any

from .store import append_log, backup_json, new_id, now, read_json, update_system_status, write_json


def list_ideas() -> list[dict[str, Any]]:
    return read_json("ideas")


def create_idea(payload: dict[str, Any]) -> dict[str, Any]:
    backup_json("create-idea")
    ideas = list_ideas()
    timestamp = now()
    idea = {
        "idea_id": new_id("idea"),
        "raw_text": payload.get("raw_text", "").strip(),
        "type": payload.get("type", "灵感").strip() or "灵感",
        "tags": payload.get("tags", []),
        "status": "已记录",
        "ai_summary": payload.get("ai_summary", "").strip() or "V1.1 本地记录，暂未启用 AI 摘要。",
        "source": "local-api",
        "external_id": None,
        "sync_status": "local_only",
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    if not idea["raw_text"]:
        raise ValueError("灵感内容不能为空")
    ideas.append(idea)
    write_json("ideas", ideas)
    append_log("idea_create", "新增灵感记录", target=idea["idea_id"])
    update_system_status(backend_api="enabled", database="json_api")
    return idea
