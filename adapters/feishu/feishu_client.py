from __future__ import annotations

import json
import os
import time
import urllib.request
from typing import Any
from urllib.error import HTTPError, URLError


_FEISHU_BASE = "https://open.feishu.cn/open-apis"
_token_cache: dict[str, Any] = {"token": None, "expires_at": 0}


class FeishuClientError(Exception):
    pass


def _get_app_credentials() -> tuple[str, str]:
    app_id = os.environ.get("FEISHU_APP_ID", "").strip()
    app_secret = os.environ.get("FEISHU_APP_SECRET", "").strip()
    return app_id, app_secret


def is_configured() -> bool:
    app_id, app_secret = _get_app_credentials()
    return bool(app_id and app_secret)


def get_tenant_access_token(force_refresh: bool = False) -> str:
    now_ts = time.time()
    if not force_refresh and _token_cache["token"] and _token_cache["expires_at"] > now_ts + 60:
        return _token_cache["token"]

    app_id, app_secret = _get_app_credentials()
    if not app_id or not app_secret:
        raise FeishuClientError("FEISHU_APP_ID / FEISHU_APP_SECRET 未配置")

    url = f"{_FEISHU_BASE}/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, json.JSONDecodeError) as error:
        raise FeishuClientError(f"获取飞书 Token 失败：{error}") from error

    if result.get("code") != 0:
        raise FeishuClientError(f"获取飞书 Token 返回错误：{result.get('msg')} {result}")

    token = result["tenant_access_token"]
    expire = result.get("expire", 7200)
    _token_cache["token"] = token
    _token_cache["expires_at"] = now_ts + expire
    return token


def _api_request(method: str, path: str, payload: dict | None = None) -> dict[str, Any]:
    token = get_tenant_access_token()
    url = f"{_FEISHU_BASE}{path}"
    data = json.dumps(payload).encode("utf-8") if payload else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise FeishuClientError(f"飞书 API HTTP {error.code}：{body}") from error
    except (URLError, json.JSONDecodeError) as error:
        raise FeishuClientError(f"飞书 API 请求失败：{error}") from error


def send_card_message(chat_id: str, card: dict[str, Any]) -> dict[str, Any]:
    if not is_configured():
        return {"skipped": True, "reason": "feishu_not_configured"}

    path = "/im/v1/messages?receive_id_type=chat_id"
    payload = {
        "receive_id": chat_id,
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False),
    }
    result = _api_request("POST", path, payload)
    if result.get("code") != 0:
        raise FeishuClientError(f"发送飞书消息失败：{result.get('msg')} {result}")
    return result


def send_text_message(chat_id: str, text: str) -> dict[str, Any]:
    if not is_configured():
        return {"skipped": True, "reason": "feishu_not_configured"}

    path = "/im/v1/messages?receive_id_type=chat_id"
    payload = {
        "receive_id": chat_id,
        "msg_type": "text",
        "content": json.dumps({"text": text}, ensure_ascii=False),
    }
    result = _api_request("POST", path, payload)
    if result.get("code") != 0:
        raise FeishuClientError(f"发送飞书消息失败：{result.get('msg')} {result}")
    return result
