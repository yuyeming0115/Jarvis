from __future__ import annotations

from typing import Any

from .store import append_log, backup_json, connect, new_id, now, read_json, update_system_status, write_json


def list_topics() -> list[dict[str, Any]]:
    return read_json("topics")


def get_topic(topic_id: str) -> dict[str, Any] | None:
    for topic in list_topics():
        if topic.get("topic_id") == topic_id:
            return topic
    return None


def create_topic(payload: dict[str, Any]) -> dict[str, Any]:
    backup_json("create-topic")
    topics = list_topics()
    timestamp = now()
    topic = {
        "topic_id": new_id("topic"),
        "title": payload.get("title", "").strip(),
        "angle": payload.get("angle", "").strip(),
        "platform": payload.get("platform", "公众号").strip() or "公众号",
        "content_type": payload.get("content_type", "文章").strip() or "文章",
        "target_audience": payload.get("target_audience", "").strip(),
        "score": int(payload.get("score", 60) or 60),
        "status": "候选",
        "draft_status": "未生成",
        "source": payload.get("source", "local-api"),
        "external_id": None,
        "sync_status": "local_only",
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    if not topic["title"]:
        raise ValueError("选题标题不能为空")
    topics.append(topic)
    write_json("topics", topics)
    append_log("topic_create", f"新增选题：{topic['title']}", target=topic["topic_id"])
    update_system_status(backend_api="enabled")
    return topic


def patch_topic(topic_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    backup_json("patch-topic")
    topics = list_topics()
    for topic in topics:
        if topic.get("topic_id") == topic_id:
            for key in ["title", "angle", "platform", "content_type", "target_audience", "score", "status", "draft_status"]:
                if key in payload:
                    topic[key] = payload[key]
            topic["updated_at"] = now()
            write_json("topics", topics)
            append_log("topic_update", f"更新选题：{topic.get('title', topic_id)}", target=topic_id)
            update_system_status(backend_api="enabled")
            return topic
    raise KeyError("选题不存在")
