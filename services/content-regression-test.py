#!/usr/bin/env python3
"""
V4.0 内容生产回归测试 (Python 版本)
验证所有 API 接口可用，不出现公网发布接口，不出现真实 secret
"""

import sys
import json
import os
import re
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE = os.environ.get("JARVIS_BASE_URL", "http://127.0.0.1:8080")
ISSUES = []

def api(method: str, path: str, body: dict = None, expect_status: int = None) -> dict:
    url = BASE + path
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body else None
    req = Request(url, data=data, headers={
        "Content-Type": "application/json; charset=utf-8",
    }, method=method)
    try:
        with urlopen(req, timeout=10) as resp:
            return {"status": resp.status, "data": json.loads(resp.read().decode("utf-8"))}
    except HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        try:
            return {"status": e.code, "data": json.loads(body_text)}
        except Exception:
            return {"status": e.code, "data": {"error": body_text[:200]}}
    except (URLError, ConnectionRefusedError) as e:
        return {"status": 0, "data": {"error": str(e)}}

def check(label: str, ok: bool, detail: str = ""):
    status = "[PASS]" if ok else "[FAIL]"
    print(f"  {status} {label}" + (f" ({detail})" if detail else ""))
    if not ok:
        ISSUES.append(label)

def main():
    print("===== Jarvis V4.0 回归测试 =====")
    print()

    # 1. 旧 API 可用
    print("[1/8] 旧 API 可用性检查...")
    old_apis = ["/api/tasks", "/api/ideas", "/api/topics", "/api/messages"]
    for api_path in old_apis:
        result = api("GET", api_path)
        check(f"GET {api_path}", result["status"] in [200, 401, 403])
    print()

    # 2. drafts API 可用
    print("[2/8] drafts API 可用性检查...")
    result = api("GET", "/api/drafts")
    check("GET /api/drafts", result["status"] in [200, 401, 403])
    print()

    # 3. generation endpoints 可用
    print("[3/8] 内容生成 endpoints 检查...")
    result = api("POST", "/api/drafts/generate-outline", {"topic_id": "test"}, 404)
    check("POST /api/drafts/generate-outline 不返回 500", result["status"] != 500)
    result = api("POST", "/api/drafts/generate-content", {"topic_id": "test"}, 404)
    check("POST /api/drafts/generate-content 不返回 500", result["status"] != 500)
    print()

    # 4. review API 可用
    print("[4/8] 审核 API 可用性检查...")
    result = api("POST", "/api/drafts/test/submit-review", {}, 404)
    check("POST /api/drafts/{id}/submit-review 不返回 500", result["status"] != 500)
    result = api("POST", "/api/drafts/test/approve", {}, 404)
    check("POST /api/drafts/{id}/approve 不返回 500", result["status"] != 500)
    result = api("POST", "/api/drafts/test/reject", {}, 404)
    check("POST /api/drafts/{id}/reject 不返回 500", result["status"] != 500)
    print()

    # 5. archive API 可用
    print("[5/8] 归档 API 可用性检查...")
    result = api("POST", "/api/drafts/test/archive-wiki", {}, 404)
    check("POST /api/drafts/{id}/archive-wiki 不返回 500", result["status"] != 500)
    print()

    # 6. 不出现公网发布接口
    print("[6/8] 公网发布接口检查...")
    forbidden = ["/api/publish", "/api/wechat/send", "/api/xiaohongshu/post"]
    for api_path in forbidden:
        result = api("POST", api_path, {})
        check(f"不应存在 {api_path}", result["status"] in [404, 405])
    print()

    # 7. 不出现真实 secret
    print("[7/8] 代码中的 secret 检查...")
    # 检查当前目录的 Python 文件
    secret_patterns = [
        r"sk-[a-zA-Z0-9]{20,}",  # OpenAI-like API keys
        r"Bearer\s+[a-zA-Z0-9_\-]{20,}",
        r"password\s*=\s*[\"'][^\"']{8,}['\"]",
    ]
    issues_found = []
    for root, dirs, files in os.walk("."):
        # 跳过备份和虚拟环境
        dirs[:] = [d for d in dirs if d not in [".git", "__pycache__", "venv", "env", "backups"]]
        for fname in files:
            if fname.endswith(".py") or fname.endswith(".js"):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                        for pattern in secret_patterns:
                            if re.search(pattern, content):
                                issues_found.append(f"{fpath}: 可能包含 secret")
                except Exception:
                    pass
    if issues_found:
        for issue in issues_found[:5]:  # 只显示前 5 个
            print(f"  [WARN] {issue}")
        check("代码中无真实 secret", False, f"{len(issues_found)} 个文件可能有问题")
    else:
        check("代码中无真实 secret", True)
    print()

    # 8. LLM 配置状态
    print("[8/8] LLM 配置状态检查...")
    result = api("GET", "/api/llm/status")
    if result["status"] == 200:
        data = result["data"]
        print(f"  LLM 配置: {data.get('configured', False)}")
        print(f"  图片配置: {data.get('image_configured', False)}")
        check("LLM 状态接口可用", True)
    else:
        check("LLM 状态接口可用", False, f"HTTP {result['status']}")
    print()

    # 总结
    print("===== 回归测试完成 =====")
    print()
    if ISSUES:
        print(f"[FAIL] {len(ISSUES)} 个问题需要修复：")
        for issue in ISSUES:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("[PASS] 所有回归测试通过！")
        sys.exit(0)

if __name__ == "__main__":
    main()
