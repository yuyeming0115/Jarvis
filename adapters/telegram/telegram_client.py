from __future__ import annotations

import json
import os
import time
import urllib.request
from typing import Any, Callable
from urllib.error import HTTPError, URLError


class TelegramClientError(Exception):
    pass


class TelegramBot:
    def __init__(self, token: str, allowed_user_ids: set[int] | None = None):
        self.token = token
        self.allowed_user_ids = allowed_user_ids
        self.base_url = f"https://api.telegram.org/bot{token}"
        self._last_update_id = 0

    def _api_request(self, method: str, payload: dict | None = None) -> dict[str, Any]:
        url = f"{self.base_url}/{method}"
        data = json.dumps(payload).encode("utf-8") if payload else None
        headers = {"Content-Type": "application/json; charset=utf-8"}
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except (HTTPError, URLError, json.JSONDecodeError) as error:
            raise TelegramClientError(f"Telegram API 请求失败：{error}") from error

        if not result.get("ok"):
            raise TelegramClientError(f"Telegram API 返回错误：{result.get('description')} {result}")
        return result.get("result", {})

    def send_message(self, chat_id: int, text: str, reply_markup: dict | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self._api_request("sendMessage", payload)

    def get_updates(self, timeout: int = 30) -> list[dict[str, Any]]:
        payload = {
            "offset": self._last_update_id + 1,
            "timeout": timeout,
            "allowed_updates": ["message"],
        }
        try:
            updates = self._api_request("getUpdates", payload)
        except TelegramClientError:
            return []
        if updates:
            self._last_update_id = max(u["update_id"] for u in updates)
        return updates

    def is_user_allowed(self, user_id: int) -> bool:
        if self.allowed_user_ids is None:
            return True
        return user_id in self.allowed_user_ids


def is_configured() -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    return bool(token)


def get_bot() -> TelegramBot | None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return None

    allowed_ids_str = os.environ.get("TELEGRAM_ALLOWED_USER_IDS", "").strip()
    allowed_ids: set[int] | None = None
    if allowed_ids_str:
        allowed_ids = set()
        for uid_str in allowed_ids_str.split(","):
            uid_str = uid_str.strip()
            if uid_str:
                try:
                    allowed_ids.add(int(uid_str))
                except ValueError:
                    pass

    return TelegramBot(token, allowed_ids)
