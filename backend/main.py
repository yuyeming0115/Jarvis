from __future__ import annotations

import json
import mimetypes
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path.home() / "Jarvis"
STATIC_DIR = ROOT / "apps" / "workbench"
BACKEND_DIR = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.ideas import create_idea, list_ideas
from backend.core.store import append_log, ensure_initialized, read_json, update_system_status
from backend.core.tasks import complete_task, create_task, list_tasks, patch_task
from backend.core.topics import create_topic, list_topics
from backend.gateway.inbox import handle_inbox


class ApiError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.status = status


class JarvisHandler(BaseHTTPRequestHandler):
    server_version = "JarvisWorkbench/1.2"

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
        routes = {
            "/api/tasks": list_tasks,
            "/api/ideas": list_ideas,
            "/api/topics": list_topics,
            "/api/system-status": lambda: read_json("system-status"),
            "/api/logs": lambda: read_json("logs"),
        }
        handler = routes.get(path)
        if not handler:
            raise ApiError("接口不存在", HTTPStatus.NOT_FOUND)
        self.send_json(handler())

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
        elif method == "POST" and path.startswith("/api/tasks/") and path.endswith("/complete"):
            task_id = path.split("/")[3]
            result = complete_task(task_id)
        elif method == "PATCH" and path.startswith("/api/tasks/"):
            task_id = path.split("/")[3]
            result = patch_task(task_id, payload)
        else:
            raise ApiError("接口不存在", HTTPStatus.NOT_FOUND)

        self.send_json(result, HTTPStatus.CREATED if method == "POST" else HTTPStatus.OK)

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
    update_system_status(workbench="online", backend_api="enabled", database="sqlite", public_access=False)
    server = ThreadingHTTPServer(("127.0.0.1", port), JarvisHandler)
    print(f"Jarvis workbench API listening on http://127.0.0.1:{port}/", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
