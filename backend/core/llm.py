from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Any
from urllib.error import HTTPError, URLError


class LLMClientError(Exception):
    pass


_MODEL_ALIASES: dict[str, str] = {}


# ============================================================
# TinyRouter 模型组（Model Groups / Combos）
# 文本和图片统一通过模型组路由，TinyRouter 自动做失败切换
# ============================================================

# 文本任务默认使用模型组（fallback 策略：自动按顺序尝试）
_DEFAULT_TEXT_MODEL_GROUP = "text-smart-fallback"

# 图片生成默认使用模型组
_DEFAULT_IMAGE_MODEL_GROUP = "image-smart-fallback"


def _resolve_model(model: str) -> str:
    """
    解析模型名：
    1. 如果包含 "/" → 已是完整模型名（如 SS/deepseek-v4-flash），直接返回
    2. 如果匹配已知别名 → 返回映射后的模型名
    3. 如果是模型组名 → 直接返回（TinyRouter 会解析）
    4. 其他 → 使用默认文本模型组
    """
    if not model:
        return _DEFAULT_TEXT_MODEL_GROUP

    # 完整模型名（含服务商前缀），直接透传
    if "/" in model:
        return model

    # 模型组名称，直接透传给 TinyRouter 解析
    if model in ("text-smart-fallback", "image-smart-fallback",
                 "text-fast", "text-quality", "image-fast"):
        return model

    # 传统别名映射（兼容旧配置）
    from .settings import get_setting
    alias_str = get_setting("tinytrouter_model_map", "")
    _MODEL_ALIASES = {}
    if alias_str:
        for pair in alias_str.split(","):
            if "=" in pair:
                alias, target = pair.split("=", 1)
                _MODEL_ALIASES[alias.strip()] = target.strip()

    # 内置别名
    builtin_aliases = {
        "deepseek-chat": _DEFAULT_TEXT_MODEL_GROUP,
        "deepseek-reasoner": _DEFAULT_TEXT_MODEL_GROUP,
        "agnes-image-2.1-flash": _DEFAULT_IMAGE_MODEL_GROUP,
    }
    builtin_aliases.update(_MODEL_ALIASES)
    return builtin_aliases.get(model, _DEFAULT_TEXT_MODEL_GROUP)


def _strip_think(text: str) -> str:
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    if "<think>" in cleaned:
        cleaned = cleaned.split("<think>")[0]
    return cleaned.strip()


def is_llm_configured() -> bool:
    return bool(_get_llm_base_url())


def _load_prompt(prompt_name: str) -> str:
    from .store import ROOT
    prompt_path = ROOT / "prompts" / f"{prompt_name}.md"
    if not prompt_path.exists():
        raise LLMClientError(f"Prompt 文件不存在：{prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def chat_completion(
    messages: list[dict[str, str]],
    model: str = "text-smart-fallback",
    temperature: float = 0.1,
    max_tokens: int = 500,
    timeout: int = 60,
) -> str:
    base_url = _get_llm_base_url()
    api_key = _get_llm_api_key()
    if not base_url:
        raise LLMClientError("API 未配置（请在设置中填写 API 地址）")

    actual_model = _resolve_model(model)
    url = f"{base_url}/chat/completions"
    payload = {
        "model": actual_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json; charset=utf-8",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            result = json.loads(raw.decode("utf-8", errors="replace"))
    except HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise LLMClientError(f"LLM API 请求失败：HTTP {error.code} {error_body[:300]}") from error
    except (URLError, json.JSONDecodeError) as error:
        raise LLMClientError(f"LLM API 请求失败：{error}") from error

    try:
        msg = result["choices"][0]["message"]
        content = msg.get("content", "").strip()
        if not content and msg.get("reasoning_content"):
            content = msg["reasoning_content"].strip()
    except (KeyError, IndexError) as error:
        raise LLMClientError(f"LLM 返回格式异常：{result}") from error

    content = _strip_think(content)
    return content


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
    model: str = "text-smart-fallback",
    topic: dict = None,
) -> dict[str, Any]:
    """
    生成草稿大纲，支持 LLM 和模板降级
    
    Args:
        title: 标题
        platform: 平台
        angle: 切入角度
        target_audience: 目标读者
        model: LLM 模型
        topic: 选题信息（用于模板降级）
        
    Returns:
        dict: 包含 outline, hook, suggested_title 等
    """
    # 尝试使用 LLM
    if is_llm_configured():
        try:
            system_prompt = _load_prompt("draft-outline")
            user_content = f"""标题：{title}
平台：{platform}
切入角度：{angle or '通用角度'}
目标读者：{target_audience or '普通读者'}"""
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]
            content = chat_completion(messages, model=model, temperature=0.7, max_tokens=2000, timeout=120)
            json_str = _extract_json(content)
            result = json.loads(json_str)
            return {
                "outline": result.get("outline", []),
                "hook": result.get("hook", ""),
                "suggested_title": result.get("suggested_title", title),
                "raw_response": content,
                "used_llm": True,
                "generation_mode": "llm",
            }
        except (LLMClientError, json.JSONDecodeError) as e:
            print(f"LLM 生成大纲失败，使用模板降级: {e}")
            # 降级到模板
    
    # 模板降级：生成简单大纲
    template_outline = [
        {
            "section": "引言",
            "key_points": ["引入话题", "提出核心问题"],
            "estimated_words": 200
        },
        {
            "section": "主体部分",
            "key_points": ["观点一", "观点二", "观点三"],
            "estimated_words": 800
        },
        {
            "section": "总结",
            "key_points": ["总结全文", "行动建议"],
            "estimated_words": 200
        }
    ]
    
    return {
        "outline": template_outline,
        "hook": f"你有没有想过，{title}？",
        "suggested_title": title,
        "raw_response": "",
        "used_llm": False,
        "generation_mode": "template",
    }


def generate_draft_content(
    title: str,
    outline: list[dict[str, Any]],
    platform: str = "公众号",
    target_audience: str = "",
    hook: str = "",
    model: str = "text-smart-fallback",
    topic: dict = None,
) -> dict[str, Any]:
    """
    生成草稿正文，支持 LLM 和模板降级
    
    Args:
        title: 标题
        outline: 大纲
        platform: 平台
        target_audience: 目标读者
        hook: 开头钩子
        model: LLM 模型
        topic: 选题信息（用于模板降级）
        
    Returns:
        dict: 包含 content, word_count 等
    """
    # 尝试使用 LLM
    if is_llm_configured():
        try:
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
            content = chat_completion(messages, model=model, temperature=0.8, max_tokens=max_tokens, timeout=120)
            word_count = len(content.replace("\n", "").replace(" ", ""))
            return {
                "content": content,
                "word_count": word_count,
                "raw_response": content,
                "used_llm": True,
                "generation_mode": "llm",
            }
        except LLMClientError as e:
            print(f"LLM 生成失败，使用模板降级: {e}")
            # 降级到模板
    
    # 模板降级
    from .prompts import get_template_fallback
    
    # 确定 channel 和 content_type
    channel_map = {
        "公众号": ("wechat", "article"),
        "小红书": ("xiaohongshu", "short_post"),
        "视频号脚本": ("video", "script"),
        "通用文章": ("generic", "article"),
    }
    channel, content_type = channel_map.get(platform, ("generic", "article"))
    
    # 准备 topic 信息供模板使用
    topic_info = topic or {}
    topic_info['title'] = title
    topic_info['summary'] = topic_info.get('summary', '')
    
    content = get_template_fallback(topic_info, channel, content_type)
    word_count = len(content.replace("\n", "").replace(" ", ""))
    
    return {
        "content": content,
        "word_count": word_count,
        "raw_response": "",
        "used_llm": False,
        "generation_mode": "template",
    }


def generate_cover_prompt(
    title: str,
    platform: str = "公众号",
    style: str = "",
    model: str = "text-smart-fallback",
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
        content = chat_completion(messages, model=model, temperature=0.8, max_tokens=1000, timeout=60)
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
    model: str = "text-smart-fallback",
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
        content_result = chat_completion(messages, model=model, temperature=0.8, max_tokens=3000, timeout=120)
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
    model: str = "text-smart-fallback",
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
        content = chat_completion(messages, model=model, temperature=0.8, max_tokens=2000, timeout=120)
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


def generate_topic_from_idea(
    idea_text: str,
    model: str = "text-smart-fallback",
) -> dict[str, Any]:
    system_prompt = """你是一位资深内容策划，擅长从零散的灵感中提炼出有价值的选题。

分析用户提供的灵感文本，输出结构化选题信息。要求：
1. 标题要吸引人，适合公众号/自媒体传播
2. 切入角度要独特，避免泛泛而谈
3. 评估选题价值（0-100分）

输出格式（严格 JSON）：
```json
{
  "title": "选题标题（简洁有力，30字以内）",
  "angle": "切入角度（独特视角，说明为什么这个角度好）",
  "platform": "推荐平台（公众号/小红书/视频号）",
  "content_type": "内容类型（文章/图文/短视频）",
  "target_audience": "目标读者画像",
  "score": 80,
  "tags": ["标签1", "标签2"],
  "reasoning": "为什么这是个好选题"
}
```"""
    user_content = f"""灵感原文：
{idea_text}

请分析并生成选题建议。"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    try:
        content = chat_completion(messages, model=model, temperature=0.8, max_tokens=1000, timeout=60)
    except LLMClientError:
        raise
    json_str = _extract_json(content)
    try:
        result = json.loads(json_str)
    except json.JSONDecodeError as error:
        raise LLMClientError(f"选题分析返回格式异常：{content}") from error
    return {
        "title": result.get("title", idea_text[:40]),
        "angle": result.get("angle", ""),
        "platform": result.get("platform", "公众号"),
        "content_type": result.get("content_type", "文章"),
        "target_audience": result.get("target_audience", ""),
        "score": result.get("score", 60),
        "tags": result.get("tags", []),
        "reasoning": result.get("reasoning", ""),
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


def _get_llm_base_url() -> str:
    """统一 API 入口：文本和图片共用同一个 base_url"""
    from .settings import get_setting
    url = get_setting("tinytrouter_base_url", "").strip().rstrip("/")
    if not url:
        url = os.environ.get("TINYROUTER_BASE_URL", "").strip().rstrip("/")
    return url


def _get_llm_api_key() -> str:
    """统一 API Key：文本和图片共用同一个 key"""
    from .settings import get_setting
    key = get_setting("tinytrouter_api_key", "").strip()
    if not key:
        key = os.environ.get("TINYROUTER_API_KEY", "").strip()
    return key


def _get_image_gen_base_url() -> str:
    """图片生成 API 地址（独立配置，不共用 TinyRouter 文本接口）"""
    from .settings import get_setting
    url = get_setting("image_gen_base_url", "").strip().rstrip("/")
    if not url:
        url = os.environ.get("IMAGE_GEN_BASE_URL", "").strip().rstrip("/")
    return url


def _get_image_gen_api_key() -> str:
    """图片生成 API Key（独立配置）"""
    from .settings import get_setting
    key = get_setting("image_gen_api_key", "").strip()
    if not key:
        key = os.environ.get("IMAGE_GEN_API_KEY", "").strip()
    return key


# ============================================================
# 图片生成提示词清洗 + 自动重试（内容安全策略容错）
# ============================================================

# Agnes AI 内容审核敏感词（触发 content_policy_violation 的常见词）
_SENSITIVE_PATTERNS = [
    # 人像/身份/年龄相关（最容易触发审核）
    r"(数字人|真人|肖像|人物形象|人物形态)",
    r"\d+\s*[岁岁](的)?(男|女|老|少|中|青)(人|性)?",
    r"(证件照|身份证|护照|驾照|名片)",
    # 政治/敏感话题
    r"(政治|政府|国家领导|国旗|国徽|党派|领导人|主席|总理|总统|国王)",
    # 暴力/危险
    r"(暴力|血腥|杀人|死亡|尸体|恐怖|武器|枪支|炸弹|刀剑|战争|打架)",
    # 色情/成人
    r"(裸体|色情|情色|成人内容|性行为|性感|暴露|诱惑|撩人|火辣)",
    # 违法
    r"(赌博|毒品|吸毒|违禁品|假币|诈骗)",
    # 负面情绪词（可能被误判）
    r"(仇恨|歧视|种族|侮辱|谩骂|反动|颠覆)",
    # 儿童保护
    r"(儿童|未成年).*?(不雅|色情|暴露|裸)",
    # 过度具体的技术参数（Agnes 对长提示词容易误判）
    r"8k[,，]?\s*(超高清|分辨率|画质)?",
]


def _clean_image_prompt(prompt: str) -> tuple[str, list[str]]:
    """
    清洗图片生成提示词，移除可能触发内容安全策略的内容。

    Returns:
        (cleaned_prompt, removed_parts): 清洗后的提示词和被移除的内容列表
    """
    import re as _re

    cleaned = prompt
    removed = []

    for pattern in _SENSITIVE_PATTERNS:
        matches = _re.findall(pattern, cleaned, _re.IGNORECASE)
        if matches:
            for m in matches:
                if isinstance(m, tuple):
                    m = "".join(m)
                if m and len(m) >= 2:
                    cleaned = _re.sub(pattern, "", cleaned, flags=_re.IGNORECASE)
                    removed.append(m.strip())

    # 二次清理：去掉多余空格、标点残留
    cleaned = _re.sub(r"[,，]{2,}", ",", cleaned)
    cleaned = _re.sub(r"\s{2,}", " ", cleaned)
    cleaned = _re.sub(r"[,，]\s*$", "", cleaned)
    cleaned = _re.sub(r"^[,，]\s*", "", cleaned)
    cleaned = cleaned.strip(" ,，。")

    return cleaned, removed


def _simplify_prompt(prompt: str) -> str:
    """激进简化：只保留核心画面描述，丢弃所有技术参数和负面约束"""
    import re as _re

    # 只提取核心画面元素（中文/英文关键词）
    # 保留：名词、形容词、风格词
    # 去掉：尺寸参数、质量参数、负面描述、技术术语

    # 截断过长提示词（Agnes 免费模型对长中文提示词容易触发审核）
    if len(prompt) > 200:
        # 尝试按句号/逗号截取前半部分
        for sep in ["。", "，", ","]:
            idx = prompt.rfind(sep, 0, 200)
            if idx > 50:
                prompt = prompt[:idx]
                break
        else:
            prompt = prompt[:180]

    return prompt.strip()


# 图片生成默认使用模型组（TinyRouter 自动 fallback 到可用图片模型）
_DEFAULT_IMAGE_MODEL = "image-smart-fallback"


def is_image_gen_configured() -> bool:
    return bool(_get_image_gen_base_url())


def generate_image(
    prompt: str,
    size: str = "1024x1024",
    n: int = 1,
    model: str = "",
    negative_prompt: str = "",
    max_retries: int = 2,
) -> dict[str, Any]:
    base_url = _get_image_gen_base_url()
    if not base_url:
        raise LLMClientError("图片生成 API 未配置（请在设置中填写图片生成 API 地址）")
    api_key = _get_image_gen_api_key()
    if not model:
        model = _DEFAULT_IMAGE_MODEL

    url = f"{base_url}/images/generations"

    import base64, time as _time

    # 重试循环：处理 content_policy_violation
    current_prompt = prompt
    current_negative = negative_prompt
    cleaned_parts: list[str] = []
    simplified = False
    last_error = ""

    for attempt in range(max_retries + 1):
        payload: dict[str, Any] = {
            "model": model,
            "prompt": current_prompt,
            "n": n,
            "size": size,
        }
        if current_negative:
            payload["negative_prompt"] = current_negative

        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json; charset=utf-8",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        t0 = _time.time()
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            # 成功！构建返回结果
            elapsed = _time.time() - t0
            images = []
            for img in result.get("data", []):
                entry: dict[str, Any] = {"revised_prompt": img.get("revised_prompt", "")}
                if img.get("url"):
                    entry["url"] = img["url"]
                if img.get("b64_json"):
                    entry["b64_json"] = img["b64_json"]
                images.append(entry)

            response = {
                "images": images,
                "model": model,
                "size": size,
                "elapsed_seconds": round(elapsed, 1),
                "used_llm": True,
            }

            # 附加提示词处理信息（方便前端展示）
            meta: dict[str, Any] = {}
            if cleaned_parts:
                meta["cleaned"] = True
                meta["removed_parts"] = cleaned_parts[:5]  # 最多展示 5 条被移除内容
            if simplified:
                meta["simplified"] = True
            if attempt > 0:
                meta["retried"] = True
                meta["retry_count"] = attempt
            if meta:
                response["prompt_meta"] = meta

            return response

        except HTTPError as error:
            error_body = error.read().decode("utf-8", errors="replace")
            last_error = f"HTTP {error.code} {error_body[:300]}"

            # 判断是否是内容安全策略错误 → 自动清洗重试
            is_content_violation = False
            try:
                err_json = json.loads(error_body)
                err_msg = str(err_json.get("message", "")).lower()
                err_code = str(err_json.get("code", "")).lower()
                err_type = str(err_json.get("type", "")).lower()
                if ("content_policy" in err_msg or "content_policy" in err_type or
                    "invalid_request" in err_code or "modify your prompt" in err_msg):
                    is_content_violation = True
            except (json.JSONDecodeError, AttributeError):
                pass

            if is_content_violation and attempt < max_retries:
                print(f"[ImageGen] 内容安全策略拦截 (attempt {attempt+1}), 自动清洗重试...")
                if attempt == 0:
                    # 第 1 次重试：清洗敏感词
                    current_prompt, removed = _clean_image_prompt(current_prompt)
                    if removed:
                        cleaned_parts.extend(removed)
                        # 同时清理负面提示词中的敏感词
                        current_negative, neg_removed = _clean_image_prompt(current_negative)
                    if not current_prompt or len(current_prompt) < 5:
                        current_prompt = prompt  # 清洗过度，回退到原始但简化版
                else:
                    # 后续重试：激进简化（截断、去掉技术参数）
                    current_prompt = _simplify_prompt(current_prompt)
                    current_negative = ""  # 去掉负面提示词（可能含敏感词）
                    simplified = True
                continue

            # 非内容安全错误 或 重试次数耗尽 → 抛出异常
            raise LLMClientError(f"图片生成 API 失败：{last_error}") from error

        except (URLError, json.JSONDecodeError) as error:
            raise LLMClientError(f"图片生成请求失败：{error}") from error

    # 理论上不会到这里（循环内一定会 return 或 raise），保险起见
    raise LLMClientError(f"图片生成失败（已重试 {max_retries} 次）：{last_error}")
