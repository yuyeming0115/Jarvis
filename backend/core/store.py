from __future__ import annotations

import json
import shutil
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path.home() / "Jarvis"
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
    for name in ["tasks", "ideas", "topics", "logs", "system-status"]:
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


def _replace_payload(name: str, payload: Any) -> None:
    if name == "tasks":
        _replace_records("tasks", "task_id", TASK_FIELDS, payload, tags=True)
    elif name == "ideas":
        _replace_records("ideas", "idea_id", IDEA_FIELDS, payload, tags=True)
    elif name == "topics":
        _replace_records("topics", "topic_id", TOPIC_FIELDS, payload, tags=False)
    elif name == "logs":
        _replace_records("logs", "log_id", LOG_FIELDS, payload, tags=False)
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
    for name in ["tasks", "ideas", "topics", "logs", "system-status"]:
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
