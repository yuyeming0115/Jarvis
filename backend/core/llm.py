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


def generate_draft_outline(
    title: str,
    platform: str = "公众号",
    angle: str = "",
    target_audience: str = "",
    model: str = "deepseek-chat",
) -> dict[str, Any]:
    system_prompt = _load_prompt("draft-outline")
    user_content = f"""标题：{title}
平台：{platform}
切入角度：{angle or '通用角度'}
目标读者：{target_audience or '普通读者'}"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    try:
        content = chat_completion(messages, model=model, temperature=0.7, max_tokens=2000)
    except LLMClientError:
        raise
    json_str = _extract_json(content)
    try:
        result = json.loads(json_str)
    except json.JSONDecodeError as error:
        raise LLMClientError(f"大纲生成返回格式异常：{content}") from error
    return {
        "outline": result.get("outline", []),
        "hook": result.get("hook", ""),
        "suggested_title": result.get("suggested_title", title),
        "raw_response": content,
        "used_llm": True,
    }


def generate_draft_content(
    title: str,
    outline: list[dict[str, Any]],
    platform: str = "公众号",
    target_audience: str = "",
    hook: str = "",
    model: str = "deepseek-chat",
) -> dict[str, Any]:
    system_prompt = _load_prompt("draft-content")
    outline_str = json.dumps(outline, ensure_ascii=False, indent=2)
    user_content = f"""标题：{title}
平台：{platform}
目标读者：{target_audience or '普通读者'}
开头钩子：{hook or '自动生成吸引人的开头'}
大纲：
{outline_str}

请根据以上大纲写完整正文。"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    max_tokens_map = {
        "公众号": 4000,
        "小红书": 2000,
        "视频号脚本": 3000,
        "通用文章": 3000,
    }
    max_tokens = max_tokens_map.get(platform, 3000)
    try:
        content = chat_completion(messages, model=model, temperature=0.8, max_tokens=max_tokens)
    except LLMClientError:
        raise
    word_count = len(content.replace("\n", "").replace(" ", ""))
    return {
        "content": content,
        "word_count": word_count,
        "raw_response": content,
        "used_llm": True,
    }


def generate_cover_prompt(
    title: str,
    platform: str = "公众号",
    style: str = "",
    model: str = "deepseek-chat",
) -> dict[str, Any]:
    system_prompt = """你是专业的 AI 绘画提示词工程师，擅长为公众号、小红书、视频号创作封面图提示词。

输出格式（严格 JSON）：
```json
{
  "cover_prompt": "中文提示词，包含主体、场景、构图、光线、风格、画质",
  "cover_negative_prompt": "负面提示词",
  "style_description": "风格说明",
  "color_scheme": "配色建议",
  "composition_tip": "构图建议"
}
```

平台封面特点：
- 公众号封面：16:9 或 2.35:1，主体突出，文字留白区域，视觉冲击力强
- 小红书封面：3:4 竖版，吸睛标题感，色彩明快，emoji 风格或实拍风格
- 视频号封面：16:9 或 1:1，画面有故事感，能代表视频核心内容

规则：
1. 只输出 JSON，不要其他内容
2. 提示词用中文，符合 Midjourney/Stable Diffusion/即梦 通用格式
3. 包含画质关键词（4K, 高清, 细节丰富等）"""
    user_content = f"""标题：{title}
平台：{platform}
期望风格：{style or '现代简约、有设计感'}

请生成封面图提示词。"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    try:
        content = chat_completion(messages, model=model, temperature=0.8, max_tokens=1000)
    except LLMClientError:
        raise
    json_str = _extract_json(content)
    try:
        result = json.loads(json_str)
    except json.JSONDecodeError as error:
        raise LLMClientError(f"封面提示词返回格式异常：{content}") from error
    return {
        "cover_prompt": result.get("cover_prompt", ""),
        "cover_negative_prompt": result.get("cover_negative_prompt", ""),
        "style_description": result.get("style_description", ""),
        "color_scheme": result.get("color_scheme", ""),
        "composition_tip": result.get("composition_tip", ""),
        "raw_response": content,
        "used_llm": True,
    }


def generate_jimeng_shots(
    title: str,
    content: str = "",
    shot_count: int = 5,
    style: str = "",
    model: str = "deepseek-chat",
) -> dict[str, Any]:
    system_prompt = _load_prompt("jimeng-shot-prompt")
    user_content = f"""标题：{title}
内容摘要：{content[:500] if content else '根据标题创作'}
需要镜头数：{shot_count}
期望风格：{style or '写实电影感'}

请生成分镜提示词。"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    try:
        content_result = chat_completion(messages, model=model, temperature=0.8, max_tokens=3000)
    except LLMClientError:
        raise
    json_str = _extract_json(content_result)
    try:
        result = json.loads(json_str)
    except json.JSONDecodeError as error:
        raise LLMClientError(f"即梦分镜返回格式异常：{content_result}") from error
    return {
        "title": result.get("title", title),
        "prompts": result.get("prompts", []),
        "style_reference": result.get("style_reference", ""),
        "music_suggestion": result.get("music_suggestion", ""),
        "raw_response": content_result,
        "used_llm": True,
    }


def generate_inline_image_prompts(
    title: str,
    outline: list[dict[str, Any]],
    platform: str = "公众号",
    image_count: int = 3,
    model: str = "deepseek-chat",
) -> dict[str, Any]:
    system_prompt = """你是专业的 AI 绘画提示词工程师，擅长为文章正文配图创作提示词。

输出格式（严格 JSON）：
```json
{
  "images": [
    {
      "position": "插入位置说明（如：第一节开头/第二节案例配图）",
      "prompt": "中文提示词",
      "negative_prompt": "负面提示词",
      "description": "这张图的作用说明"
    }
  ]
}
```

配图原则：
- 公众号配图：16:9 或 4:3，配合文章段落，图文呼应
- 小红书配图：3:4 竖版，风格统一，有网感
- 配图数量根据章节数量合理分配
- 风格要统一，与封面风格协调

规则：
1. 只输出 JSON，不要其他内容
2. 提示词用中文
3. 包含画质关键词"""
    outline_str = json.dumps(outline, ensure_ascii=False, indent=2)
    user_content = f"""标题：{title}
平台：{platform}
需要配图数：{image_count}
大纲：
{outline_str}

请生成正文配图提示词。"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    try:
        content = chat_completion(messages, model=model, temperature=0.8, max_tokens=2000)
    except LLMClientError:
        raise
    json_str = _extract_json(content)
    try:
        result = json.loads(json_str)
    except json.JSONDecodeError as error:
        raise LLMClientError(f"配图提示词返回格式异常：{content}") from error
    return {
        "images": result.get("images", []),
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
