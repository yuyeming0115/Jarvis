from __future__ import annotations

import json
import os
import urllib.request
from typing import Any
from urllib.error import HTTPError, URLError


class LLMClientError(Exception):
    pass


def is_llm_configured() -> bool:
    base_url = os.environ.get("TINYROUTER_BASE_URL", "").strip()
    api_key = os.environ.get("TINYROUTER_API_KEY", "").strip()
    return bool(base_url and api_key)


def _load_prompt(prompt_name: str) -> str:
    from .store import ROOT
    prompt_path = ROOT / "prompts" / f"{prompt_name}.md"
    if not prompt_path.exists():
        raise LLMClientError(f"Prompt 文件不存在：{prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def chat_completion(
    messages: list[dict[str, str]],
    model: str = "deepseek-chat",
    temperature: float = 0.1,
    max_tokens: int = 500,
    timeout: int = 30,
) -> str:
    base_url = os.environ.get("TINYROUTER_BASE_URL", "").strip().rstrip("/")
    api_key = os.environ.get("TINYROUTER_API_KEY", "").strip()
    if not base_url or not api_key:
        raise LLMClientError("TINYROUTER_BASE_URL 或 TINYROUTER_API_KEY 未配置")

    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json; charset=utf-8",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, json.JSONDecodeError) as error:
        raise LLMClientError(f"LLM API 请求失败：{error}") from error

    try:
        return result["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as error:
        raise LLMClientError(f"LLM 返回格式异常：{result}") from error


def classify_message(text: str) -> dict[str, Any]:
    system_prompt = _load_prompt("classify-message")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"请分类这条消息：{text}"},
    ]

    try:
        content = chat_completion(messages, temperature=0.0, max_tokens=300)
    except LLMClientError:
        raise

    json_str = _extract_json(content)
    try:
        result = json.loads(json_str)
    except json.JSONDecodeError as error:
        raise LLMClientError(f"LLM 返回不是有效 JSON：{content}") from error

    intent = result.get("intent", "confirm")
    if intent not in ("task", "idea", "topic", "confirm"):
        intent = "confirm"

    return {
        "intent": intent,
        "title": result.get("title", text[:50]),
        "due_at": result.get("due_at"),
        "confidence": float(result.get("confidence", 0.5)),
        "reason": result.get("reason", ""),
        "raw_response": content,
        "used_llm": True,
    }


def _extract_json(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        content = "\n".join(lines).strip()

    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        return content[start : end + 1]
    return content
