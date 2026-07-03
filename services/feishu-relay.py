from __future__ import annotations

import http.client
import json
import os
import secrets
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path.home() / "Jarvis"
LOCAL_CONFIG_DIR = ROOT / "config" / "local"
TOKEN_FILE = LOCAL_CONFIG_DIR / "feishu-callback-token"
JARVIS_PORT = int(os.environ.get("JARVIS_WORKBENCH_PORT", "8080"))
RELAY_PORT = int(os.environ.get("JARVIS_FEISHU_RELAY_PORT", "18790"))


def get_callback_token() -> str:
    LOCAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text(encoding="utf-8").strip()
    token = secrets.token_urlsafe(24)
    TOKEN_FILE.write_text(token + "\n", encoding="utf-8")
    TOKEN_FILE.chmod(0o600)
    return token


CALLBACK_TOKEN = get_callback_token()
CALLBACK_PATH = f"/feishu/{CALLBACK_TOKEN}/event"


class FeishuRelayHandler(BaseHTTPRequestHandler):
    server_version = "JarvisFeishuRelay/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        if urlparse(self.path).path == "/health":
            self.send_json({"status": "ok", "callback_path": CALLBACK_PATH})
            return
        self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if urlparse(self.path).path != CALLBACK_PATH:
            self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        status, payload = self.forward_to_jarvis(body)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def forward_to_jarvis(self, body: bytes) -> tuple[int, bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", JARVIS_PORT, timeout=15)
        try:
            conn.request(
                "POST",
                "/api/feishu/event",
                body=body,
                headers={"Content-Type": "application/json"},
            )
            response = conn.getresponse()
            payload = response.read()
            return response.status, payload
        finally:
            conn.close()

    def send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", RELAY_PORT), FeishuRelayHandler)
    print(f"Feishu relay listening on http://127.0.0.1:{RELAY_PORT}{CALLBACK_PATH}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
