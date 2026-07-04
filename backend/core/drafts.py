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

    fields = [
        "title",
        "platform",
        "content_type",
        "content",
        "status",
        "ai_model",
        "topic_id",
        "idea_id",
        "channel",
        "body",
        "summary",
        "review_status",
        "prompt_version",
        "model_name",
        "generation_mode",
        "input_context_json",
        "output_metadata_json",
        "review_notes",
        "rejection_reason",
        "approved_at",
        "archived_at",
    ]
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


def generate_draft_from_topic(topic_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """
    从选题生成草稿，支持 LLM 和模板降级
    
    Args:
        topic_id: 选题 ID
        payload: 包含 channel, content_type, generation_mode 等
        
    Returns:
        dict: 生成的草稿信息
    """
    # 1. 获取选题信息
    from .topics import get_topic
    topic = get_topic(topic_id)
    if not topic:
        raise KeyError(f"选题不存在: {topic_id}")
    
    # 2. 确定生成参数
    channel = payload.get("channel", "wechat")
    content_type = payload.get("content_type", "article")
    generation_mode = payload.get("generation_mode", "auto")
    
    # 映射 channel 到 platform
    channel_to_platform = {
        "wechat": "公众号",
        "xiaohongshu": "小红书",
        "video": "视频号脚本",
        "generic": "通用文章"
    }
    platform = channel_to_platform.get(channel, "公众号")
    
    # 3. 生成大纲
    from .llm import generate_draft_outline
    outline_result = generate_draft_outline(
        title=topic.get("title", ""),
        platform=platform,
        angle=topic.get("angle", ""),
        target_audience=topic.get("target_audience", ""),
        model=payload.get("model", "deepseek-chat"),
        topic=topic
    )
    
    # 4. 生成正文
    from .llm import generate_draft_content
    content_result = generate_draft_content(
        title=outline_result.get("suggested_title", topic.get("title", "")),
        outline=outline_result["outline"],
        platform=platform,
        target_audience=topic.get("target_audience", ""),
        hook=outline_result.get("hook", ""),
        model=payload.get("model", "deepseek-chat"),
        topic=topic
    )
    
    # 5. 保存草稿
    draft = create_draft({
        "title": outline_result.get("suggested_title", topic.get("title", "")),
        "topic_id": topic_id,
        "platform": platform,
        "content_type": content_type,
        "outline": outline_result["outline"],
        "content": content_result["content"],
        "word_count": content_result["word_count"],
        "status": "草稿",
        "ai_model": payload.get("model", "deepseek-chat") if content_result.get("used_llm") else "template",
        "source": "ai-generate",
        "generation_mode": content_result.get("generation_mode", "template"),
        "channel": channel,
        "prompt_version": payload.get("prompt_version", "default"),
        "model_name": payload.get("model", "deepseek-chat") if content_result.get("used_llm") else "template",
        "input_context_json": json.dumps({
            "topic_id": topic_id,
            "topic_title": topic.get("title", ""),
            "channel": channel,
            "content_type": content_type
        }, ensure_ascii=False)
    })
    
    # 6. 记录生成日志
    append_log("draft_generate", f"从选题生成草稿：{draft['title']}", target=draft["draft_id"])
    
    return draft


def submit_draft_for_review(draft_id: str, payload: dict[str, Any] = None) -> dict[str, Any]:
    """
    提交草稿进行审核
    
    Args:
        draft_id: 草稿 ID
        payload: 可选，包含提交备注
        
    Returns:
        dict: 更新后的草稿信息
    """
    draft = get_draft(draft_id)
    if not draft:
        raise KeyError(f"草稿不存在: {draft_id}")
    
    # 更新状态
    updates = {
        "status": "待审核",
        "review_status": "pending",
        "updated_at": now()
    }
    
    # 保存提交备注
    if payload and payload.get("submit_notes"):
        updates["review_notes"] = payload.get("submit_notes")
    
    # 更新数据库
    with connect() as conn:
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [draft_id]
        conn.execute(f"UPDATE drafts SET {set_clause} WHERE draft_id = ?", values)
        
        # 记录审核动作
        review_id = new_id("review")
        conn.execute("""
            INSERT INTO content_reviews (review_id, draft_id, action, review_notes, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (review_id, draft_id, "submit_review", updates.get("review_notes", ""), now()))
    
    append_log("draft_submit_review", f"提交审核：{draft.get('title', draft_id)}", target=draft_id)
    return get_draft(draft_id)


def approve_draft(draft_id: str, payload: dict[str, Any] = None) -> dict[str, Any]:
    """
    批准草稿
    
    Args:
        draft_id: 草稿 ID
        payload: 可选，包含审核备注
        
    Returns:
        dict: 更新后的草稿信息
    """
    draft = get_draft(draft_id)
    if not draft:
        raise KeyError(f"草稿不存在: {draft_id}")
    
    # 更新状态
    updates = {
        "status": "定稿",
        "review_status": "approved",
        "approved_at": now(),
        "updated_at": now()
    }
    
    # 保存审核备注
    if payload and payload.get("review_notes"):
        updates["review_notes"] = payload.get("review_notes")
    
    # 更新数据库
    with connect() as conn:
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [draft_id]
        conn.execute(f"UPDATE drafts SET {set_clause} WHERE draft_id = ?", values)
        
        # 记录审核动作
        review_id = new_id("review")
        conn.execute("""
            INSERT INTO content_reviews (review_id, draft_id, action, review_notes, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (review_id, draft_id, "approve", updates.get("review_notes", ""), now()))
    
    append_log("draft_approve", f"批准草稿：{draft.get('title', draft_id)}", target=draft_id)
    return get_draft(draft_id)


def reject_draft(draft_id: str, payload: dict[str, Any] = None) -> dict[str, Any]:
    """
    驳回草稿
    
    Args:
        draft_id: 草稿 ID
        payload: 包含驳回原因
        
    Returns:
        dict: 更新后的草稿信息
    """
    draft = get_draft(draft_id)
    if not draft:
        raise KeyError(f"草稿不存在: {draft_id}")
    
    # 检查是否提供了驳回原因
    if not payload or not payload.get("rejection_reason"):
        raise ValueError("驳回时必须提供驳回原因")
    
    # 更新状态
    updates = {
        "status": "修改中",
        "review_status": "rejected",
        "rejection_reason": payload.get("rejection_reason"),
        "updated_at": now()
    }
    
    # 保存审核备注
    if payload and payload.get("review_notes"):
        updates["review_notes"] = payload.get("review_notes")
    
    # 更新数据库
    with connect() as conn:
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [draft_id]
        conn.execute(f"UPDATE drafts SET {set_clause} WHERE draft_id = ?", values)
        
        # 记录审核动作
        review_id = new_id("review")
        conn.execute("""
            INSERT INTO content_reviews (review_id, draft_id, action, review_notes, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (review_id, draft_id, "reject", updates.get("review_notes", ""), now()))
    
    append_log("draft_reject", f"驳回草稿：{draft.get('title', draft_id)} - {updates['rejection_reason']}", target=draft_id)
    return get_draft(draft_id)


def rewrite_draft(draft_id: str, payload: dict[str, Any] = None) -> dict[str, Any]:
    """
    重写草稿（不覆盖原草稿，生成新版本）
    
    Args:
        draft_id: 原草稿 ID
        payload: 包含重写原因和反馈
        
    Returns:
        dict: 新生成的草稿信息
    """
    draft = get_draft(draft_id)
    if not draft:
        raise KeyError(f"草稿不存在: {draft_id}")
    
    # 获取原草稿信息
    title = draft.get("title", "")
    content = draft.get("content", "")
    topic_id = draft.get("topic_id")
    
    # 调用 LLM 或模板降级重新生成
    from .llm import generate_draft_content, is_llm_configured
    
    if is_llm_configured():
        # 使用 LLM 重写
        outline = json.loads(draft.get("outline_json", "[]") or "[]")
        result = generate_draft_content(
            title=title,
            outline=outline,
            platform=draft.get("platform", "公众号"),
            target_audience=draft.get("target_audience", ""),
            hook="",
            model=draft.get("ai_model", "deepseek-chat"),
            topic=draft
        )
        new_content = result["content"]
        generation_mode = result.get("generation_mode", "llm")
    else:
        # 模板降级
        from .prompts import get_template_fallback
        channel_map = {
            "公众号": ("wechat", "article"),
            "小红书": ("xiaohongshu", "short_post"),
            "视频号脚本": ("video", "script"),
            "通用文章": ("generic", "article")
        }
        channel, content_type = channel_map.get(draft.get("platform", "公众号"), ("generic", "article"))
        new_content = get_template_fallback(draft, channel, content_type)
        generation_mode = "template"
    
    # 创建新草稿（新版本）
    new_draft = create_draft({
        "title": title,
        "topic_id": topic_id,
        "platform": draft.get("platform", "公众号"),
        "content_type": draft.get("content_type", "文章"),
        "outline": json.loads(draft.get("outline_json", "[]") or "[]"),
        "content": new_content,
        "word_count": len(new_content),
        "status": "草稿",
        "ai_model": draft.get("ai_model", "template"),
        "source": "rewrite",
        "generation_mode": generation_mode,
        "input_context_json": json.dumps({
            "source_draft_id": draft_id,
            "rewrite_reason": payload.get("rewrite_reason", "") if payload else "",
            "feedback": payload.get("feedback", "") if payload else ""
        }, ensure_ascii=False)
    })
    
    # 记录审核动作
    with connect() as conn:
        review_id = new_id("review")
        conn.execute("""
            INSERT INTO content_reviews (review_id, draft_id, action, review_notes, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (review_id, draft_id, "rewrite", f"重写生成新草稿: {new_draft['draft_id']}", now()))
    
    append_log("draft_rewrite", f"重写草稿：{title} -> {new_draft['draft_id']}", target=draft_id)
    return new_draft
