from __future__ import annotations

import json
import mimetypes
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


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
STATIC_DIR = ROOT / "apps" / "workbench"
BACKEND_DIR = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.ideas import create_idea, list_ideas
from backend.core.messages import list_messages
from backend.core.store import append_log, ensure_initialized, read_json, update_system_status
from backend.core.tasks import complete_task, create_task, list_tasks, patch_task
from backend.core.topics import create_topic, list_topics
from backend.core.drafts import create_draft, delete_draft, get_draft, list_drafts, patch_draft
from backend.core.wiki import archive_draft_to_wiki, create_wiki_page, delete_wiki_page, get_wiki_page, get_wiki_page_by_slug, list_wiki_pages, patch_wiki_page, search_wiki
from backend.core.media_prompts import create_media_prompt, delete_media_prompt, get_media_prompt, list_media_prompts, patch_media_prompt, save_generated_cover, save_generated_inline_images, save_generated_shots
from backend.core.llm import (
    LLMClientError,
    generate_cover_prompt,
    generate_draft_content,
    generate_draft_outline,
    generate_inline_image_prompts,
    generate_jimeng_shots,
    is_llm_configured,
)
from adapters.feishu.feishu_adapter import handle_feishu_event
from backend.gateway.inbox import handle_inbox


class ApiError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.status = status


class JarvisHandler(BaseHTTPRequestHandler):
    server_version = "JarvisWorkbench/2.0"

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        try:
            path = urlparse(self.path).path
            if path.startswith("/api/"):
                self.handle_api_get(path)
            else:
                self.serve_static(path)
        except Exception as error:
            self.send_error_json(error)

    def do_POST(self) -> None:
        try:
            self.handle_api_write("POST")
        except Exception as error:
            self.send_error_json(error)

    def do_PATCH(self) -> None:
        try:
            self.handle_api_write("PATCH")
        except Exception as error:
            self.send_error_json(error)

    def handle_api_get(self, path: str) -> None:
        from urllib.parse import parse_qs, urlparse
        parsed = urlparse(self.path)
        req_path = parsed.path
        query = parse_qs(parsed.query)

        def get_query(name: str, default: str | None = None) -> str | None:
            values = query.get(name)
            return values[0] if values else default

        if req_path == "/api/tasks":
            return self.send_json(list_tasks())
        if req_path == "/api/ideas":
            return self.send_json(list_ideas())
        if req_path == "/api/topics":
            return self.send_json(list_topics())
        if req_path == "/api/messages":
            return self.send_json(list_messages())
        if req_path == "/api/drafts":
            return self.send_json(list_drafts())
        if req_path == "/api/wiki":
            tag = get_query("tag")
            status = get_query("status")
            q = get_query("q")
            return self.send_json(list_wiki_pages(tag=tag, status=status, query=q))
        if req_path == "/api/wiki/search":
            q = get_query("q", "")
            limit = int(get_query("limit", "20"))
            return self.send_json(search_wiki(q, limit=limit))
        if req_path == "/api/media-prompts":
            ptype = get_query("type")
            draft_id = get_query("draft_id")
            topic_id = get_query("topic_id")
            return self.send_json(list_media_prompts(prompt_type=ptype, draft_id=draft_id, topic_id=topic_id))
        if req_path == "/api/system-status":
            return self.send_json(read_json("system-status"))
        if req_path == "/api/logs":
            return self.send_json(read_json("logs"))
        if req_path == "/api/llm/status":
            return self.send_json({"configured": is_llm_configured()})

        if req_path.startswith("/api/drafts/"):
            parts = req_path.strip("/").split("/")
            if len(parts) >= 3:
                draft_id = parts[2]
                draft = get_draft(draft_id)
                if not draft:
                    raise ApiError("草稿不存在", HTTPStatus.NOT_FOUND)
                return self.send_json(draft)

        if req_path.startswith("/api/wiki/slug/"):
            slug = req_path[len("/api/wiki/slug/"):]
            page = get_wiki_page_by_slug(slug)
            if not page:
                raise ApiError("文章不存在", HTTPStatus.NOT_FOUND)
            return self.send_json(page)

        if req_path.startswith("/api/wiki/"):
            parts = req_path.strip("/").split("/")
            if len(parts) >= 3 and parts[2] != "search":
                page_id = parts[2]
                page = get_wiki_page(page_id)
                if not page:
                    raise ApiError("文章不存在", HTTPStatus.NOT_FOUND)
                return self.send_json(page)

        if req_path.startswith("/api/media-prompts/"):
            parts = req_path.strip("/").split("/")
            if len(parts) >= 3:
                prompt_id = parts[2]
                prompt = get_media_prompt(prompt_id)
                if not prompt:
                    raise ApiError("提示词不存在", HTTPStatus.NOT_FOUND)
                return self.send_json(prompt)

        raise ApiError(f"接口不存在: {req_path}", HTTPStatus.NOT_FOUND)

    def handle_api_write(self, method: str) -> None:
        path = urlparse(self.path).path
        payload = self.read_payload()
        result = None

        if method == "POST" and path == "/api/tasks":
            result = create_task(payload)
        elif method == "POST" and path == "/api/ideas":
            result = create_idea(payload)
        elif method == "POST" and path == "/api/topics":
            result = create_topic(payload)
        elif method == "POST" and path == "/api/inbox":
            result = handle_inbox(payload)
        elif method == "POST" and path == "/api/feishu/event":
            result = handle_feishu_event(payload, dict(self.headers.items()))
        elif method == "POST" and path.startswith("/api/tasks/") and path.endswith("/complete"):
            task_id = path.split("/")[3]
            result = complete_task(task_id)
        elif method == "PATCH" and path.startswith("/api/tasks/"):
            task_id = path.split("/")[3]
            result = patch_task(task_id, payload)

        elif method == "POST" and path == "/api/drafts":
            result = create_draft(payload)
        elif method == "POST" and path == "/api/drafts/generate-outline":
            result = self._handle_generate_outline(payload)
        elif method == "POST" and path == "/api/drafts/generate-content":
            result = self._handle_generate_content(payload)
        elif method == "POST" and path.startswith("/api/drafts/") and path.endswith("/archive-wiki"):
            draft_id = path.split("/")[3]
            result = archive_draft_to_wiki(draft_id, payload or None)
        elif method == "PATCH" and path.startswith("/api/drafts/"):
            draft_id = path.split("/")[3]
            result = patch_draft(draft_id, payload)
        elif method == "DELETE" and path.startswith("/api/drafts/"):
            draft_id = path.split("/")[3]
            delete_draft(draft_id)
            result = {"deleted": True}

        elif method == "POST" and path == "/api/wiki":
            result = create_wiki_page(payload)
        elif method == "PATCH" and path.startswith("/api/wiki/"):
            page_id = path.split("/")[3]
            result = patch_wiki_page(page_id, payload)
        elif method == "DELETE" and path.startswith("/api/wiki/"):
            page_id = path.split("/")[3]
            delete_wiki_page(page_id)
            result = {"deleted": True}

        elif method == "POST" and path == "/api/media-prompts":
            result = create_media_prompt(payload)
        elif method == "POST" and path == "/api/media/generate-cover":
            result = self._handle_generate_cover(payload)
        elif method == "POST" and path == "/api/media/generate-jimeng":
            result = self._handle_generate_jimeng(payload)
        elif method == "POST" and path == "/api/media/generate-inline-images":
            result = self._handle_generate_inline_images(payload)
        elif method == "PATCH" and path.startswith("/api/media-prompts/"):
            prompt_id = path.split("/")[3]
            result = patch_media_prompt(prompt_id, payload)
        elif method == "DELETE" and path.startswith("/api/media-prompts/"):
            prompt_id = path.split("/")[3]
            delete_media_prompt(prompt_id)
            result = {"deleted": True}

        else:
            raise ApiError("接口不存在", HTTPStatus.NOT_FOUND)

        status = HTTPStatus.OK if path == "/api/feishu/event" else HTTPStatus.CREATED if method == "POST" else HTTPStatus.OK
        self.send_json(result, status)

    def _handle_generate_outline(self, payload: dict) -> dict:
        if not is_llm_configured():
            raise ApiError("LLM 未配置（需要设置 TINYROUTER_BASE_URL 和 TINYROUTER_API_KEY）", HTTPStatus.SERVICE_UNAVAILABLE)
        title = payload.get("title", "").strip()
        if not title:
            raise ApiError("标题不能为空")
        platform = payload.get("platform", "公众号")
        angle = payload.get("angle", "")
        target_audience = payload.get("target_audience", "")
        model = payload.get("model", "deepseek-chat")
        try:
            result = generate_draft_outline(title, platform, angle, target_audience, model)
        except LLMClientError as error:
            raise ApiError(f"大纲生成失败：{error}", HTTPStatus.INTERNAL_SERVER_ERROR) from error
        if payload.get("auto_save") and result.get("outline"):
            draft = create_draft({
                "title": result.get("suggested_title", title),
                "platform": platform,
                "content_type": "文章",
                "outline": result["outline"],
                "status": "大纲",
                "ai_model": model,
                "topic_id": payload.get("topic_id"),
                "idea_id": payload.get("idea_id"),
                "source": "ai-outline",
            })
            result["draft"] = draft
        return result

    def _handle_generate_content(self, payload: dict) -> dict:
        if not is_llm_configured():
            raise ApiError("LLM 未配置", HTTPStatus.SERVICE_UNAVAILABLE)
        title = payload.get("title", "").strip()
        if not title:
            raise ApiError("标题不能为空")
        outline = payload.get("outline", [])
        if not outline:
            raise ApiError("大纲不能为空")
        platform = payload.get("platform", "公众号")
        target_audience = payload.get("target_audience", "")
        hook = payload.get("hook", "")
        model = payload.get("model", "deepseek-chat")
        try:
            result = generate_draft_content(title, outline, platform, target_audience, hook, model)
        except LLMClientError as error:
            raise ApiError(f"内容生成失败：{error}", HTTPStatus.INTERNAL_SERVER_ERROR) from error
        draft_id = payload.get("draft_id")
        if draft_id:
            patch_draft(draft_id, {
                "content": result["content"],
                "word_count": result["word_count"],
                "status": "草稿",
                "ai_model": model,
            })
            result["draft_id"] = draft_id
        return result

    def _handle_generate_cover(self, payload: dict) -> dict:
        if not is_llm_configured():
            raise ApiError("LLM 未配置", HTTPStatus.SERVICE_UNAVAILABLE)
        title = payload.get("title", "").strip()
        if not title:
            raise ApiError("标题不能为空")
        platform = payload.get("platform", "公众号")
        style = payload.get("style", "")
        model = payload.get("model", "deepseek-chat")
        try:
            result = generate_cover_prompt(title, platform, style, model)
        except LLMClientError as error:
            raise ApiError(f"封面提示词生成失败：{error}", HTTPStatus.INTERNAL_SERVER_ERROR) from error
        if payload.get("auto_save"):
            saved = save_generated_cover(
                title, result, platform,
                draft_id=payload.get("draft_id"),
                topic_id=payload.get("topic_id"),
                model=model,
            )
            result["saved"] = saved
        return result

    def _handle_generate_jimeng(self, payload: dict) -> dict:
        if not is_llm_configured():
            raise ApiError("LLM 未配置", HTTPStatus.SERVICE_UNAVAILABLE)
        title = payload.get("title", "").strip()
        if not title:
            raise ApiError("标题不能为空")
        content = payload.get("content", "")
        shot_count = int(payload.get("shot_count", 5))
        style = payload.get("style", "")
        model = payload.get("model", "deepseek-chat")
        try:
            result = generate_jimeng_shots(title, content, shot_count, style, model)
        except LLMClientError as error:
            raise ApiError(f"即梦分镜生成失败：{error}", HTTPStatus.INTERNAL_SERVER_ERROR) from error
        if payload.get("auto_save"):
            saved = save_generated_shots(
                title, result, payload.get("platform", "视频号"),
                draft_id=payload.get("draft_id"),
                topic_id=payload.get("topic_id"),
                model=model,
            )
            result["saved"] = saved
        return result

    def _handle_generate_inline_images(self, payload: dict) -> dict:
        if not is_llm_configured():
            raise ApiError("LLM 未配置", HTTPStatus.SERVICE_UNAVAILABLE)
        title = payload.get("title", "").strip()
        if not title:
            raise ApiError("标题不能为空")
        outline = payload.get("outline", [])
        platform = payload.get("platform", "公众号")
        image_count = int(payload.get("image_count", 3))
        model = payload.get("model", "deepseek-chat")
        try:
            result = generate_inline_image_prompts(title, outline, platform, image_count, model)
        except LLMClientError as error:
            raise ApiError(f"配图提示词生成失败：{error}", HTTPStatus.INTERNAL_SERVER_ERROR) from error
        if payload.get("auto_save"):
            saved = save_generated_inline_images(
                title, result, platform,
                draft_id=payload.get("draft_id"),
                topic_id=payload.get("topic_id"),
                model=model,
            )
            result["saved"] = saved
        return result

    def read_payload(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ApiError(f"JSON 解析失败：{error}") from error
        if not isinstance(payload, dict):
            raise ApiError("请求体必须是 JSON 对象")
        return payload

    def serve_static(self, path: str) -> None:
        clean_path = unquote(path).lstrip("/")
        file_path = STATIC_DIR / (clean_path or "index.html")
        if file_path.is_dir():
            file_path = file_path / "index.html"
        try:
            resolved = file_path.resolve()
            resolved.relative_to(STATIC_DIR.resolve())
        except ValueError as error:
            raise ApiError("非法路径", HTTPStatus.FORBIDDEN) from error
        if not resolved.exists():
            raise ApiError("文件不存在", HTTPStatus.NOT_FOUND)

        content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        data = resolved.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_error_json(self, error: Exception) -> None:
        status = error.status if isinstance(error, ApiError) else HTTPStatus.INTERNAL_SERVER_ERROR
        if isinstance(error, (ValueError, KeyError)):
            status = HTTPStatus.BAD_REQUEST
        message = str(error)
        try:
            append_log("api_error", message, status="failed", target="api")
        except Exception:
            pass
        self.send_json({"error": message}, status)


def main() -> None:
    port = int(os.environ.get("JARVIS_WORKBENCH_PORT", "8080"))
    ensure_initialized()
    update_system_status(workbench="online", backend_api="enabled", database="sqlite", public_access=False, telegram="not_configured")

    try:
        from adapters.telegram.telegram_adapter import start_telegram_bot
        if start_telegram_bot():
            print("Telegram bot started", flush=True)
    except Exception as error:
        print(f"Telegram bot not started: {error}", flush=True)

    server = ThreadingHTTPServer(("127.0.0.1", port), JarvisHandler)
    print(f"Jarvis workbench API listening on http://127.0.0.1:{port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        try:
            from adapters.telegram.telegram_adapter import stop_telegram_bot
            stop_telegram_bot()
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
