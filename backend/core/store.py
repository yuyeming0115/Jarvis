from __future__ import annotations

import json
import os
import shutil
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


def _detect_root() -> Path:
    env_root = os.environ.get("JARVIS_ROOT")
    if env_root:
        return Path(env_root).resolve()

    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        if (parent / "apps" / "workbench").is_dir() and (parent / "backend").is_dir():
            return parent
        if parent.name == "Jarvis" and (parent / "apps").is_dir():
            return parent

    return Path.home() / "Jarvis"


ROOT = _detect_root()
DATA_DIR = ROOT / "apps" / "workbench" / "data"
BACKUP_DIR = ROOT / "backups"
DB_DIR = ROOT / "backend" / "db"
DB_PATH = DB_DIR / "jarvis.sqlite3"
SCHEMA_PATH = DB_DIR / "schema.sql"

TASK_FIELDS = [
    "task_id",
    "title",
    "description",
    "project",
    "source",
    "due_at",
    "priority",
    "status",
    "reminder_level",
    "external_id",
    "sync_status",
    "completed_at",
    "deleted_at",
    "created_at",
    "updated_at",
]

IDEA_FIELDS = [
    "idea_id",
    "raw_text",
    "type",
    "status",
    "ai_summary",
    "source",
    "external_id",
    "sync_status",
    "created_at",
    "updated_at",
]

TOPIC_FIELDS = [
    "topic_id",
    "title",
    "angle",
    "platform",
    "content_type",
    "target_audience",
    "score",
    "status",
    "draft_status",
    "source",
    "external_id",
    "sync_status",
    "created_at",
    "updated_at",
]

LOG_FIELDS = [
    "log_id",
    "trace_id",
    "level",
    "event_type",
    "source",
    "target",
    "status",
    "message",
    "cost",
    "created_at",
]

MESSAGE_FIELDS = [
    "message_id",
    "platform",
    "platform_user_id",
    "chat_id",
    "raw_text",
    "message_type",
    "normalized_intent",
    "status",
    "error_message",
    "received_at",
    "processed_at",
    "created_at",
]

_INITIALIZED = False


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def new_id(prefix: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    suffix = uuid.uuid4().hex[:6]
    return f"{prefix}_{stamp}_{suffix}"


def data_path(name: str) -> Path:
    return DATA_DIR / f"{name}.json"


def connect() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        _apply_schema_upgrades(conn)


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def _add_column_if_missing(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
    definition: str,
) -> None:
    if column_name not in _table_columns(conn, table_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def _apply_schema_upgrades(conn: sqlite3.Connection) -> None:
    """Keep existing SQLite databases compatible with the latest app code."""
    draft_columns = {
        "source_message_id": "TEXT",
        "channel": "TEXT",
        "body": "TEXT",
        "summary": "TEXT",
        "review_status": "TEXT NOT NULL DEFAULT 'pending'",
        "prompt_version": "TEXT",
        "model_name": "TEXT",
        "generation_mode": "TEXT NOT NULL DEFAULT 'template'",
        "input_context_json": "TEXT",
        "output_metadata_json": "TEXT",
        "review_notes": "TEXT",
        "rejection_reason": "TEXT",
        "approved_at": "TEXT",
        "archived_at": "TEXT",
    }
    for column_name, definition in draft_columns.items():
        _add_column_if_missing(conn, "drafts", column_name, definition)

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS prompt_versions (
          prompt_id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          version TEXT NOT NULL,
          channel TEXT,
          content_type TEXT,
          file_path TEXT NOT NULL,
          description TEXT,
          is_active INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS content_reviews (
          review_id TEXT PRIMARY KEY,
          draft_id TEXT NOT NULL,
          action TEXT NOT NULL,
          review_notes TEXT,
          created_at TEXT NOT NULL,
          FOREIGN KEY (draft_id) REFERENCES drafts(draft_id)
        );

        CREATE TABLE IF NOT EXISTS settings (
          key TEXT PRIMARY KEY,
          value TEXT,
          is_secret INTEGER NOT NULL DEFAULT 0,
          description TEXT,
          group_name TEXT NOT NULL DEFAULT 'general',
          updated_at TEXT NOT NULL
        );

        UPDATE drafts SET channel = platform WHERE channel IS NULL;
        UPDATE drafts SET body = content WHERE body IS NULL;
        UPDATE drafts SET model_name = ai_model WHERE model_name IS NULL;
        UPDATE drafts SET review_status = 'approved'
          WHERE status IN ('定稿', '已发布', '已归档')
            AND review_status = 'pending';

        CREATE INDEX IF NOT EXISTS idx_drafts_channel ON drafts(channel);
        CREATE INDEX IF NOT EXISTS idx_drafts_review_status ON drafts(review_status);
        CREATE INDEX IF NOT EXISTS idx_drafts_generation_mode ON drafts(generation_mode);
        CREATE INDEX IF NOT EXISTS idx_prompt_versions_active ON prompt_versions(is_active);
        CREATE INDEX IF NOT EXISTS idx_content_reviews_draft_id ON content_reviews(draft_id);
        CREATE INDEX IF NOT EXISTS idx_settings_group ON settings(group_name);
        """
    )
    _seed_default_settings(conn)


def _seed_default_settings(conn: sqlite3.Connection) -> None:
    defaults = [
        ("tinytrouter_base_url", "http://127.0.0.1:20129/v1", 0, "LLM API 端点地址", "llm"),
        ("tinytrouter_api_key", "", 1, "LLM API 密钥（留空则不需要）", "llm"),
        ("tinytrouter_model_map", "deepseek-chat=SS/deepseek-v4-flash,deepseek-reasoner=SS/deepseek-v4-flash", 0, "模型别名映射（格式：别名=实际模型,...）", "llm"),
        ("default_llm_model", "deepseek-chat", 0, "默认 LLM 模型", "llm"),
        ("default_llm_temperature", "0.7", 0, "默认生成温度（0.0-2.0）", "llm"),
        ("default_llm_max_tokens", "4000", 0, "默认最大 token 数", "llm"),
        ("image_gen_base_url", "", 0, "图片生成 API 端点地址", "image"),
        ("image_gen_api_key", "", 1, "图片生成 API 密钥", "image"),
        ("image_gen_model", "", 0, "图片生成模型", "image"),
        ("jarvis_port", "8080", 0, "Workbench 服务端口", "system"),
        ("jarvis_safe_mode", "true", 0, "安全模式（只允许本机访问）", "system"),
        ("jarvis_public_access", "false", 0, "允许局域网访问", "system"),
        ("default_platform", "公众号", 0, "默认内容平台（公众号/小红书/视频号）", "content"),
        ("default_content_type", "文章", 0, "默认内容类型（文章/短文/脚本）", "content"),
        ("default_target_audience", "普通读者", 0, "默认目标读者", "content"),
    ]
    timestamp = now()
    conn.executemany(
        """
        INSERT OR IGNORE INTO settings
          (key, value, is_secret, description, group_name, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [(*entry, timestamp) for entry in defaults],
    )


def ensure_initialized() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return
    init_db()
    if _should_seed_from_json():
        seed_from_json()
    _INITIALIZED = True


def _should_seed_from_json() -> bool:
    with connect() as conn:
        counts = [
            conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0],
            conn.execute("SELECT COUNT(*) FROM ideas").fetchone()[0],
            conn.execute("SELECT COUNT(*) FROM topics").fetchone()[0],
            conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0],
        ]
    return all(count == 0 for count in counts) and any(DATA_DIR.glob("*.json"))


def seed_from_json() -> None:
    init_db()
    for name in ["tasks", "ideas", "topics", "logs", "messages", "system-status"]:
        path = data_path(name)
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        _replace_payload(name, payload)


def read_json(name: str) -> Any:
    ensure_initialized()
    if name == "tasks":
        return _read_table("tasks", TASK_FIELDS, "task_id")
    if name == "ideas":
        return _read_table("ideas", IDEA_FIELDS, "idea_id")
    if name == "topics":
        return _read_table("topics", TOPIC_FIELDS, "topic_id")
    if name == "logs":
        return _read_table("logs", LOG_FIELDS, "created_at")
    if name == "messages":
        return _read_messages()
    if name == "system-status":
        return _read_system_status()
    raise KeyError(f"未知数据集：{name}")


def write_json(name: str, payload: Any) -> None:
    ensure_initialized()
    _replace_payload(name, payload)


def _read_table(table: str, fields: list[str], order_by: str) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(f"SELECT * FROM {table} ORDER BY {order_by}").fetchall()
    records = []
    for row in rows:
        item = {field: row[field] for field in fields}
        if "tags_json" in row.keys():
            item["tags"] = json.loads(row["tags_json"] or "[]")
        records.append(item)
    return records


def _read_system_status() -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT payload_json FROM system_status WHERE id = 1").fetchone()
    if row:
        return json.loads(row["payload_json"])
    return {
        "workbench": "online",
        "backend_api": "enabled",
        "database": "sqlite",
        "feishu": "not_configured",
        "telegram": "reserved_not_configured",
        "wechat": "evaluation_only",
        "openclaw": "not_installed",
        "tinyrouter": "not_installed",
        "hermes": "not_installed",
        "last_sync_at": None,
        "safe_mode": True,
        "public_access": False,
    }


def _read_messages() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM messages ORDER BY received_at").fetchall()
    records = []
    for row in rows:
        item = {field: row[field] for field in MESSAGE_FIELDS}
        item["normalized_payload"] = json.loads(row["normalized_payload_json"] or "{}")
        item["source_event"] = json.loads(row["source_event_json"] or "{}")
        records.append(item)
    return records


def _replace_payload(name: str, payload: Any) -> None:
    if name == "tasks":
        _replace_records("tasks", "task_id", TASK_FIELDS, payload, tags=True)
    elif name == "ideas":
        _replace_records("ideas", "idea_id", IDEA_FIELDS, payload, tags=True)
    elif name == "topics":
        _replace_records("topics", "topic_id", TOPIC_FIELDS, payload, tags=False)
    elif name == "logs":
        _replace_records("logs", "log_id", LOG_FIELDS, payload, tags=False)
    elif name == "messages":
        _replace_messages(payload)
    elif name == "system-status":
        _replace_system_status(payload)
    else:
        raise KeyError(f"未知数据集：{name}")


def _replace_records(table: str, id_field: str, fields: list[str], records: list[dict[str, Any]], tags: bool) -> None:
    if not isinstance(records, list):
        raise ValueError(f"{table} 必须是数组")
    insert_fields = fields + (["tags_json"] if tags else [])
    placeholders = ", ".join("?" for _ in insert_fields)
    columns = ", ".join(insert_fields)
    values = []
    for record in records:
        row = [record.get(field) for field in fields]
        if tags:
            row.append(json.dumps(record.get("tags", []), ensure_ascii=False))
        values.append(row)
    with connect() as conn:
        conn.execute(f"DELETE FROM {table}")
        if values:
            conn.executemany(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", values)


def _replace_system_status(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("system-status 必须是对象")
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO system_status (id, payload_json)
            VALUES (1, ?)
            ON CONFLICT(id) DO UPDATE SET payload_json = excluded.payload_json
            """,
            (json.dumps(payload, ensure_ascii=False),),
        )


def _replace_messages(records: list[dict[str, Any]]) -> None:
    if not isinstance(records, list):
        raise ValueError("messages 必须是数组")
    values = []
    for record in records:
        values.append(
            [
                record.get("message_id"),
                record.get("platform"),
                record.get("platform_user_id"),
                record.get("chat_id"),
                record.get("raw_text"),
                record.get("message_type"),
                record.get("normalized_intent"),
                json.dumps(record.get("normalized_payload", {}), ensure_ascii=False),
                json.dumps(record.get("source_event", {}), ensure_ascii=False),
                record.get("status"),
                record.get("error_message"),
                record.get("received_at"),
                record.get("processed_at"),
                record.get("created_at"),
            ]
        )
    with connect() as conn:
        conn.execute("DELETE FROM messages")
        if values:
            conn.executemany(
                """
                INSERT INTO messages (
                  message_id, platform, platform_user_id, chat_id, raw_text,
                  message_type, normalized_intent, normalized_payload_json,
                  source_event_json, status, error_message, received_at,
                  processed_at, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )


def backup_json(reason: str) -> Path:
    ensure_initialized()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    safe_reason = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in reason)[:40]
    dest = BACKUP_DIR / f"auto-data-{stamp}-{safe_reason}"
    json_dest = dest / "json"
    dest.mkdir(parents=True, exist_ok=True)
    json_dest.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        shutil.copy2(DB_PATH, dest / DB_PATH.name)
    export_json(json_dest)
    return dest


def export_json(dest: Path | None = None) -> Path:
    ensure_initialized()
    target = dest or DATA_DIR
    target.mkdir(parents=True, exist_ok=True)
    for name in ["tasks", "ideas", "topics", "logs", "messages", "system-status"]:
        payload = read_json(name)
        path = target / f"{name}.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    return target


def append_log(
    event_type: str,
    message: str,
    status: str = "success",
    source: str = "local-api",
    target: str = "sqlite",
) -> dict[str, Any]:
    logs = read_json("logs")
    entry = {
        "log_id": new_id("log"),
        "trace_id": new_id("trace"),
        "level": "info" if status == "success" else "error",
        "event_type": event_type,
        "source": source,
        "target": target,
        "status": status,
        "message": message,
        "cost": 0,
        "created_at": now(),
    }
    logs.append(entry)
    write_json("logs", logs)
    return entry


def update_system_status(**changes: Any) -> dict[str, Any]:
    status = read_json("system-status")
    status.update(changes)
    status["database"] = "sqlite"
    status["last_sync_at"] = now()
    write_json("system-status", status)
    return status
