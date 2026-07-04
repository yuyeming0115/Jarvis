from __future__ import annotations

import json
import re
from typing import Any

from .store import append_log, connect, ensure_initialized, new_id, now


WIKI_STATUSES = ["草稿", "已发布", "归档"]


def _slugify(title: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff\-]+", "-", title.lower().strip())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or f"page-{new_id('page')[-6:]}"


def list_wiki_pages(tag: str | None = None, status: str | None = None, query: str | None = None) -> list[dict[str, Any]]:
    ensure_initialized()
    sql = "SELECT * FROM wiki_pages WHERE COALESCE(deleted_at, '') = ''"
    params: list[Any] = []
    if status:
        sql += " AND status = ?"
        params.append(status)
    if tag:
        sql += " AND tags_json LIKE ?"
        params.append(f'%"{tag}"%')
    if query:
        sql += " AND (title LIKE ? OR content_md LIKE ? OR summary LIKE ?)"
        like_q = f"%{query}%"
        params.extend([like_q, like_q, like_q])
    sql += " ORDER BY updated_at DESC"
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["tags"] = json.loads(item.pop("tags_json", "[]") or "[]")
        item.pop("content_md", None)
        result.append(item)
    return result


def get_wiki_page(page_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM wiki_pages WHERE page_id = ?", (page_id,)).fetchone()
    if not row:
        return None
    item = dict(row)
    item["tags"] = json.loads(item.pop("tags_json", "[]") or "[]")
    return item


def get_wiki_page_by_slug(slug: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM wiki_pages WHERE slug = ? AND COALESCE(deleted_at, '') = ''", (slug,)).fetchone()
    if not row:
        return None
    item = dict(row)
    item["tags"] = json.loads(item.pop("tags_json", "[]") or "[]")
    return item


def create_wiki_page(payload: dict[str, Any]) -> dict[str, Any]:
    ensure_initialized()
    timestamp = now()
    page_id = new_id("wiki")
    title = payload.get("title", "").strip()
    if not title:
        raise ValueError("文章标题不能为空")
    slug = payload.get("slug", "").strip() or _slugify(title)
    content_md = payload.get("content_md", "")
    summary = payload.get("summary", "")
    tags = payload.get("tags", [])
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except (json.JSONDecodeError, TypeError):
            tags = []
    status = payload.get("status", "草稿")
    source_type = payload.get("source_type")
    source_id = payload.get("source_id")
    word_count = len(content_md.replace("\n", "").replace(" ", ""))

    with connect() as conn:
        existing = conn.execute("SELECT page_id FROM wiki_pages WHERE slug = ?", (slug,)).fetchone()
        if existing:
            slug = f"{slug}-{page_id[-6:]}"
        conn.execute(
            """
            INSERT INTO wiki_pages (
                page_id, title, slug, content_md, summary, tags_json,
                source_type, source_id, word_count, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                page_id, title, slug, content_md, summary,
                json.dumps(tags, ensure_ascii=False),
                source_type, source_id, word_count, status,
                timestamp, timestamp,
            ),
        )
    append_log("wiki_create", f"新建知识库文章：{title}", target=page_id)
    return get_wiki_page(page_id)


def patch_wiki_page(page_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    page = get_wiki_page(page_id)
    if not page:
        raise KeyError("文章不存在")
    fields = ["title", "slug", "content_md", "summary", "status", "source_type", "source_id"]
    updates: dict[str, Any] = {}
    for key in fields:
        if key in payload:
            updates[key] = payload[key]
    if "tags" in payload:
        updates["tags_json"] = json.dumps(payload["tags"], ensure_ascii=False)
    if "content_md" in payload:
        updates["word_count"] = len(payload["content_md"].replace("\n", "").replace(" ", ""))
    if "title" in payload and "slug" not in payload:
        new_slug = _slugify(payload["title"])
        with connect() as conn:
            existing = conn.execute(
                "SELECT page_id FROM wiki_pages WHERE slug = ? AND page_id != ?",
                (new_slug, page_id),
            ).fetchone()
            if not existing:
                updates["slug"] = new_slug
    updates["updated_at"] = now()
    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [page_id]
        with connect() as conn:
            conn.execute(f"UPDATE wiki_pages SET {set_clause} WHERE page_id = ?", values)
        append_log("wiki_update", f"更新知识库文章：{page.get('title', page_id)}", target=page_id)
    return get_wiki_page(page_id)


def delete_wiki_page(page_id: str) -> bool:
    with connect() as conn:
        conn.execute(
            "UPDATE wiki_pages SET deleted_at = ?, updated_at = ? WHERE page_id = ?",
            (now(), now(), page_id),
        )
    append_log("wiki_delete", f"删除知识库文章：{page_id}", target=page_id)
    return True


def search_wiki(query: str, limit: int = 20) -> list[dict[str, Any]]:
    return list_wiki_pages(query=query)[:limit]


def archive_draft_to_wiki(draft_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    from .drafts import get_draft
    draft = get_draft(draft_id)
    if not draft:
        raise KeyError("草稿不存在")
    wiki_payload = {
        "title": draft["title"],
        "content_md": draft.get("content", ""),
        "summary": f"从草稿归档：{draft['platform']} / {draft['content_type']}",
        "tags": ["草稿归档", draft.get("platform", "")],
        "status": "草稿",
        "source_type": "draft",
        "source_id": draft_id,
    }
    if payload:
        wiki_payload.update({k: v for k, v in payload.items() if v is not None})
    return create_wiki_page(wiki_payload)
