from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .store import connect, append_log

SETTINGS_GROUPS = {
    "llm": {"label": "LLM 配置", "icon": "🤖"},
    "image": {"label": "图片生成配置", "icon": "🖼️"},
    "system": {"label": "系统设置", "icon": "⚙️"},
    "content": {"label": "内容生成默认值", "icon": "📝"},
}


def get_setting(key: str, default: Any = None) -> Any:
    """读取设置值，同时检查数据库和 os.environ"""
    db_val = _get_from_db(key)
    if db_val is not None:
        return db_val
    env_val = os.environ.get(key.upper(), os.environ.get(key, None))
    if env_val is not None:
        return env_val
    return default


def get_setting_int(key: str, default: int = 0) -> int:
    """读取整数设置"""
    val = get_setting(key, default)
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def get_setting_bool(key: str, default: bool = False) -> bool:
    """读取布尔设置"""
    val = get_setting(key, default)
    if isinstance(val, bool):
        return val
    return str(val).lower() in ("true", "1", "yes", "on")


def set_setting(
    key: str,
    value: Any,
    is_secret: int = 0,
    description: str = "",
    group_name: str = "general",
) -> None:
    """设置值，同时写入数据库和 os.environ"""
    str_value = str(value) if value is not None else ""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with connect() as conn:
        existing = conn.execute(
            "SELECT key FROM settings WHERE key = ?", (key,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE settings SET value = ?, is_secret = ?, description = ?, group_name = ?, updated_at = ? WHERE key = ?",
                (str_value, is_secret, description, group_name, now, key),
            )
        else:
            conn.execute(
                "INSERT INTO settings (key, value, is_secret, description, group_name, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (key, str_value, is_secret, description, group_name, now),
            )

    # 同步到 os.environ，让依赖 os.environ 的代码也能工作
    os.environ[key.upper()] = str_value
    append_log("setting_update", f"更新设置 {key}={str_value[:20]}..." if len(str_value) > 20 else f"更新设置 {key}={str_value}")


def list_settings(group: str | None = None, include_secrets: bool = False) -> list[dict]:
    """列出所有设置（默认脱敏密钥）"""
    with connect() as conn:
        if group:
            rows = conn.execute(
                "SELECT key, value, is_secret, description, group_name, updated_at FROM settings WHERE group_name = ? ORDER BY key",
                (group,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT key, value, is_secret, description, group_name, updated_at FROM settings ORDER BY group_name, key"
            ).fetchall()

    result = []
    for row in rows:
        key, value, is_secret, description, group_name, updated_at = row
        entry = {
            "key": key,
            "value": _mask_secret(value) if (is_secret and not include_secrets) else value,
            "is_secret": bool(is_secret),
            "description": description or "",
            "group_name": group_name or "general",
            "updated_at": updated_at or "",
        }
        result.append(entry)
    return result


def list_settings_by_group() -> dict[str, list[dict]]:
    """按分组列出设置"""
    all_settings = list_settings(include_secrets=False)
    grouped: dict[str, list[dict]] = {}
    for s in all_settings:
        grp = s["group_name"]
        if grp not in grouped:
            grouped[grp] = []
        grouped[grp].append(s)
    return grouped


def delete_setting(key: str) -> bool:
    """删除设置（同时从 os.environ 清除）"""
    with connect() as conn:
        cursor = conn.execute("DELETE FROM settings WHERE key = ?", (key,))
        if cursor.rowcount > 0:
            env_key = key.upper()
            if env_key in os.environ:
                del os.environ[env_key]
            append_log("setting_delete", f"删除设置：{key}")
            return True
    return False


def init_settings_from_env() -> None:
    """从 .env 文件和环境变量初始化 settings 表"""
    mapping = [
        ("TINYROUTER_BASE_URL", "tinytrouter_base_url", 0, "LLM API 端点地址", "llm"),
        ("TINYROUTER_API_KEY", "tinytrouter_api_key", 1, "LLM API 密钥", "llm"),
        ("TINYROUTER_MODEL_MAP", "tinytrouter_model_map", 0, "模型别名映射", "llm"),
        ("IMAGE_GEN_BASE_URL", "image_gen_base_url", 0, "图片生成 API 端点", "image"),
        ("IMAGE_GEN_API_KEY", "image_gen_api_key", 1, "图片生成 API 密钥", "image"),
        ("JARVIS_WORKBENCH_PORT", "jarvis_port", 0, "Workbench 服务端口", "system"),
        ("JARVIS_SAFE_MODE", "jarvis_safe_mode", 0, "安全模式", "system"),
        ("JARVIS_PUBLIC_ACCESS", "jarvis_public_access", 0, "允许局域网访问", "system"),
    ]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with connect() as conn:
        for env_key, db_key, is_secret, desc, grp in mapping:
            env_val = os.environ.get(env_key, "")
            existing = conn.execute(
                "SELECT key FROM settings WHERE key = ?", (db_key,)
            ).fetchone()
            if not existing and env_val:
                conn.execute(
                    "INSERT INTO settings (key, value, is_secret, description, group_name, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (db_key, env_val, is_secret, desc, grp, now),
                )


def test_llm_connection(base_url: str, api_key: str = "", model: str = "deepseek-chat") -> dict:
    """测试 LLM API 连接"""
    import json as _json
    import urllib.request
    import urllib.error

    if not base_url:
        return {"ok": False, "error": "base_url 不能为空"}

    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "你好"}],
        "max_tokens": 10,
        "stream": False,
    }
    data = _json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = _json.loads(resp.read().decode("utf-8"))
            return {
                "ok": True,
                "model": result.get("model", model),
                "usage": result.get("usage", {}),
            }
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _get_from_db(key: str) -> str | None:
    """从数据库读取设置值"""
    try:
        with connect() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
            return row[0] if row else None
    except Exception:
        return None


def _mask_secret(value: str) -> str:
    """对密钥脱敏（只显示前 4 和后 4 位）"""
    if not value or len(value) <= 8:
        return "****"
    return value[:4] + "****" + value[-4:]
