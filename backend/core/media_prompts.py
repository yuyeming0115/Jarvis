from __future__ import annotations

import json
from typing import Any

from .store import append_log, connect, ensure_initialized, new_id, now


MEDIA_PROMPT_TYPES = ["封面图", "正文配图", "即梦分镜", "通用生图"]
MEDIA_STATUSES = ["已生成", "已使用", "归档"]


def list_media_prompts(
    prompt_type: str | None = None,
    draft_id: str | None = None,
    topic_id: str | None = None,
) -> list[dict[str, Any]]:
    ensure_initialized()
    sql = "SELECT * FROM media_prompts WHERE COALESCE(deleted_at, '') = ''"
    params: list[Any] = []
    if prompt_type:
        sql += " AND prompt_type = ?"
        params.append(prompt_type)
    if draft_id:
        sql += " AND draft_id = ?"
        params.append(draft_id)
    if topic_id:
        sql += " AND topic_id = ?"
        params.append(topic_id)
    sql += " ORDER BY updated_at DESC"
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["prompts"] = json.loads(item.pop("prompts_json", "[]") or "[]")
        result.append(item)
    return result


def get_media_prompt(prompt_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM media_prompts WHERE prompt_id = ?", (prompt_id,)).fetchone()
    if not row:
        return None
    item = dict(row)
    item["prompts"] = json.loads(item.pop("prompts_json", "[]") or "[]")
    return item


def create_media_prompt(payload: dict[str, Any]) -> dict[str, Any]:
    ensure_initialized()
    timestamp = now()
    prompt_id = new_id("media")
    title = payload.get("title", "").strip()
    if not title:
        raise ValueError("提示词标题不能为空")
    prompt_type = payload.get("prompt_type", "封面图")
    platform = payload.get("platform", "")
    prompts = payload.get("prompts", payload.get("prompts_json", []))
    if isinstance(prompts, str):
        try:
            prompts = json.loads(prompts)
        except (json.JSONDecodeError, TypeError):
            prompts = []
    style_reference = payload.get("style_reference", "")
    music_suggestion = payload.get("music_suggestion", "")
    ai_model = payload.get("ai_model", "")
    status = payload.get("status", "已生成")
    draft_id = payload.get("draft_id")
    topic_id = payload.get("topic_id")

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO media_prompts (
                prompt_id, draft_id, topic_id, title, prompt_type, platform,
                prompts_json, style_reference, music_suggestion, ai_model,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                prompt_id, draft_id, topic_id, title, prompt_type, platform,
                json.dumps(prompts, ensure_ascii=False),
                style_reference, music_suggestion, ai_model,
                status, timestamp, timestamp,
            ),
        )
    append_log("media_create", f"新建多媒体提示词：{title} ({prompt_type})", target=prompt_id)
    return get_media_prompt(prompt_id)


def patch_media_prompt(prompt_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    prompt = get_media_prompt(prompt_id)
    if not prompt:
        raise KeyError("提示词不存在")
    fields = ["title", "prompt_type", "platform", "style_reference", "music_suggestion", "ai_model", "status", "draft_id", "topic_id"]
    updates: dict[str, Any] = {}
    for key in fields:
        if key in payload:
            updates[key] = payload[key]
    if "prompts" in payload:
        updates["prompts_json"] = json.dumps(payload["prompts"], ensure_ascii=False)
    updates["updated_at"] = now()
    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [prompt_id]
        with connect() as conn:
            conn.execute(f"UPDATE media_prompts SET {set_clause} WHERE prompt_id = ?", values)
        append_log("media_update", f"更新多媒体提示词：{prompt.get('title', prompt_id)}", target=prompt_id)
    return get_media_prompt(prompt_id)


def delete_media_prompt(prompt_id: str) -> bool:
    with connect() as conn:
        conn.execute(
            "UPDATE media_prompts SET deleted_at = ?, updated_at = ? WHERE prompt_id = ?",
            (now(), now(), prompt_id),
        )
    append_log("media_delete", f"删除多媒体提示词：{prompt_id}", target=prompt_id)
    return True


def save_generated_cover(
    title: str,
    cover_result: dict[str, Any],
    platform: str = "公众号",
    draft_id: str | None = None,
    topic_id: str | None = None,
    model: str = "",
) -> dict[str, Any]:
    prompts = [
        {
            "shot_number": 1,
            "shot_name": "封面图",
            "prompt": cover_result.get("cover_prompt", ""),
            "negative_prompt": cover_result.get("cover_negative_prompt", ""),
            "shot_type": "封面",
        }
    ]
    return create_media_prompt({
        "title": f"{title} - 封面图",
        "prompt_type": "封面图",
        "platform": platform,
        "prompts": prompts,
        "style_reference": cover_result.get("style_description", ""),
        "music_suggestion": "",
        "ai_model": model,
        "draft_id": draft_id,
        "topic_id": topic_id,
    })


def save_generated_shots(
    title: str,
    shots_result: dict[str, Any],
    platform: str = "视频号",
    draft_id: str | None = None,
    topic_id: str | None = None,
    model: str = "",
) -> dict[str, Any]:
    return create_media_prompt({
        "title": shots_result.get("title", title),
        "prompt_type": "即梦分镜",
        "platform": platform,
        "prompts": shots_result.get("prompts", []),
        "style_reference": shots_result.get("style_reference", ""),
        "music_suggestion": shots_result.get("music_suggestion", ""),
        "ai_model": model,
        "draft_id": draft_id,
        "topic_id": topic_id,
    })


def save_generated_inline_images(
    title: str,
    images_result: dict[str, Any],
    platform: str = "公众号",
    draft_id: str | None = None,
    topic_id: str | None = None,
    model: str = "",
) -> dict[str, Any]:
    prompts = []
    for idx, img in enumerate(images_result.get("images", []), 1):
        prompts.append({
            "shot_number": idx,
            "shot_name": img.get("position", f"配图{idx}"),
            "prompt": img.get("prompt", ""),
            "negative_prompt": img.get("negative_prompt", ""),
            "description": img.get("description", ""),
            "shot_type": "正文配图",
        })
    return create_media_prompt({
        "title": f"{title} - 正文配图",
        "prompt_type": "正文配图",
        "platform": platform,
        "prompts": prompts,
        "style_reference": "",
        "music_suggestion": "",
        "ai_model": model,
        "draft_id": draft_id,
        "topic_id": topic_id,
    })
