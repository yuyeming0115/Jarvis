from __future__ import annotations

import json
from typing import Any

from .store import append_log, backup_json, connect, ensure_initialized, new_id, now, read_json, update_system_status, write_json


DRAFT_STATUSES = ["大纲", "草稿", "修改中", "待审核", "定稿", "已发布"]
CONTENT_PLATFORMS = ["公众号", "小红书", "视频号脚本", "通用文章"]


def list_drafts() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM drafts WHERE COALESCE(deleted_at, '') = '' ORDER BY updated_at DESC"
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["outline"] = json.loads(item.pop("outline_json", "[]") or "[]")
        item["generation_params"] = json.loads(item.pop("generation_params_json", "{}") or "{}")
        result.append(item)
    return result


def get_draft(draft_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM drafts WHERE draft_id = ?", (draft_id,)).fetchone()
    if not row:
        return None
    item = dict(row)
    item["outline"] = json.loads(item.pop("outline_json", "[]") or "[]")
    item["generation_params"] = json.loads(item.pop("generation_params_json", "{}") or "{}")
    return item


def create_draft(payload: dict[str, Any]) -> dict[str, Any]:
    ensure_initialized()
    timestamp = now()
    draft_id = new_id("draft")
    title = payload.get("title", "").strip()
    platform = payload.get("platform", "公众号").strip() or "公众号"
    content_type = payload.get("content_type", "文章").strip() or "文章"
    topic_id = payload.get("topic_id")
    idea_id = payload.get("idea_id")
    outline = payload.get("outline", payload.get("outline_json", []))
    if isinstance(outline, str):
        try:
            outline = json.loads(outline)
        except (json.JSONDecodeError, TypeError):
            outline = []
    content = payload.get("content", "")
    status = payload.get("status", "大纲")

    if not title:
        raise ValueError("草稿标题不能为空")

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO drafts (
                draft_id, topic_id, idea_id, title, platform, content_type,
                outline_json, content, word_count, status, ai_model,
                generation_params_json, source, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                draft_id,
                topic_id,
                idea_id,
                title,
                platform,
                content_type,
                json.dumps(outline, ensure_ascii=False),
                content,
                len(content),
                status,
                payload.get("ai_model", ""),
                json.dumps(payload.get("generation_params", {}), ensure_ascii=False),
                payload.get("source", "local-api"),
                timestamp,
                timestamp,
            ),
        )
    append_log("draft_create", f"新建草稿：{title}", target=draft_id)
    update_system_status(backend_api="enabled")
    return get_draft(draft_id)


def patch_draft(draft_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    draft = get_draft(draft_id)
    if not draft:
        raise KeyError("草稿不存在")

    fields = ["title", "platform", "content_type", "content", "status", "ai_model", "topic_id", "idea_id"]
    updates = {}
    for key in fields:
        if key in payload:
            updates[key] = payload[key]

    if "outline" in payload:
        updates["outline_json"] = json.dumps(payload["outline"], ensure_ascii=False)
    if "generation_params" in payload:
        updates["generation_params_json"] = json.dumps(payload["generation_params"], ensure_ascii=False)
    if "content" in payload:
        updates["word_count"] = len(payload["content"] or "")
    updates["updated_at"] = now()

    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [draft_id]
        with connect() as conn:
            conn.execute(f"UPDATE drafts SET {set_clause} WHERE draft_id = ?", values)
        append_log("draft_update", f"更新草稿：{draft.get('title', draft_id)}", target=draft_id)
    return get_draft(draft_id)


def delete_draft(draft_id: str) -> bool:
    from .store import new_id as _
    with connect() as conn:
        conn.execute("UPDATE drafts SET deleted_at = ?, updated_at = ? WHERE draft_id = ?", (now(), now(), draft_id))
    append_log("draft_delete", f"删除草稿：{draft_id}", target=draft_id)
    return True
