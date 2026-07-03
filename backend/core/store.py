from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path.home() / "Jarvis"
DATA_DIR = ROOT / "apps" / "workbench" / "data"
BACKUP_DIR = ROOT / "backups"


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def new_id(prefix: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    suffix = uuid.uuid4().hex[:6]
    return f"{prefix}_{stamp}_{suffix}"


def data_path(name: str) -> Path:
    return DATA_DIR / f"{name}.json"


def read_json(name: str) -> Any:
    path = data_path(name)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(name: str, payload: Any) -> None:
    path = data_path(name)
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
      json.dump(payload, handle, ensure_ascii=False, indent=2)
      handle.write("\n")
    tmp.replace(path)


def backup_json(reason: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    safe_reason = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in reason)[:40]
    dest = BACKUP_DIR / f"auto-json-{stamp}-{safe_reason}"
    dest.mkdir(parents=True, exist_ok=True)
    for path in DATA_DIR.glob("*.json"):
        shutil.copy2(path, dest / path.name)
    return dest


def append_log(event_type: str, message: str, status: str = "success", source: str = "local-api", target: str = "json") -> dict[str, Any]:
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
    status["last_sync_at"] = now()
    write_json("system-status", status)
    return status
