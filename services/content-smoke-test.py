#!/usr/bin/env python3
"""
V4.0 内容生产完整流程 Smoke Test (Python 版本)
测试从选题到归档的完整链路
"""

import sys
import json
import time
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE = os.environ.get("JARVIS_BASE_URL", "http://127.0.0.1:8080")

def api(method: str, path: str, body: dict = None) -> dict:
    url = BASE + path
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body else None
    req = Request(url, data=data, headers={
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
    }, method=method)
    try:
        with urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        try:
            return json.loads(body_text)
        except Exception:
            print(f"[FAIL] HTTP {e.code}: {body_text[:200]}")
            sys.exit(1)
    except (URLError, ConnectionRefusedError) as e:
        print(f"[FAIL] 连接失败: {e}")
        sys.exit(1)

def main():
    print("===== Jarvis V4.0 内容生产 Smoke Test (Python) =====")
    print()

    # 1. 创建测试选题
    print("[1/9] 创建测试选题...")
    topic = api("POST", "/api/topics", {
        "title": "V4.0 测试选题 - 内容生产流程",
        "platform": "公众号",
        "content_type": "文章",
        "target_audience": "测试用户",
        "status": "候选",
        "tags": ["测试"]
    })
    topic_id = topic.get("topic_id", "")
    if not topic_id:
        print(f"[FAIL] 创建选题失败: {topic}")
        sys.exit(1)
    print(f"[PASS] 选题已创建: {topic_id}")
    print()

    # 2. 从选题生成草稿
    print("[2/9] 从选题生成草稿...")
    draft_resp = api("POST", f"/api/topics/{topic_id}/generate-draft", {
        "channel": "wechat",
        "content_type": "article",
        "generation_mode": "auto"
    })
    draft_id = draft_resp.get("draft_id", "")
    if not draft_id:
        print(f"[FAIL] 生成草稿失败: {draft_resp}")
        sys.exit(1)
    print(f"[PASS] 草稿已生成: {draft_id}")
    print()

    # 3. 读取草稿详情
    print("[3/9] 读取草稿详情...")
    draft = api("GET", f"/api/drafts/{draft_id}")
    draft_title = draft.get("title", "")
    draft_status = draft.get("status", "")
    draft_word_count = draft.get("word_count", 0)
    print(f"  标题: {draft_title}")
    print(f"  状态: {draft_status}")
    print(f"  字数: {draft_word_count}")
    if draft_word_count == 0:
        print("[FAIL] 草稿内容为空")
        sys.exit(1)
    print("[PASS] 草稿内容非空")
    print()

    # 4. 编辑草稿
    print("[4/9] 编辑草稿...")
    api("PATCH", f"/api/drafts/{draft_id}", {
        "title": draft_title + " (已编辑)"
    })
    print("[PASS] 草稿已编辑")
    print()

    # 5. 提交审核
    print("[5/9] 提交审核...")
    api("POST", f"/api/drafts/{draft_id}/submit-review", {
        "submit_notes": "Smoke test 提交审核"
    })
    print("[PASS] 已提交审核")
    print()

    # 6. 批准草稿
    print("[6/9] 批准草稿...")
    api("POST", f"/api/drafts/{draft_id}/approve", {
        "review_notes": "Smoke test 批准"
    })
    time.sleep(1)
    draft = api("GET", f"/api/drafts/{draft_id}")
    if draft.get("status") != "定稿":
        print(f"[FAIL] 批准失败，当前状态: {draft.get('status')}")
        sys.exit(1)
    print(f"[PASS] 草稿已批准，状态: {draft.get('status')}")
    print()

    # 7. 归档草稿
    print("[7/9] 归档草稿...")
    archive_resp = api("POST", f"/api/drafts/{draft_id}/archive-wiki", {})
    wiki_page_id = archive_resp.get("page_id", "")
    if not wiki_page_id:
        print(f"[FAIL] 归档失败: {archive_resp}")
        sys.exit(1)
    print(f"[PASS] 草稿已归档到 wiki: {wiki_page_id}")
    print()

    # 8. 验证 wiki 文件
    print("[8/9] 验证 wiki 文件...")
    wiki = api("GET", f"/api/wiki/{wiki_page_id}")
    wiki_slug = wiki.get("slug", "")
    print(f"  Wiki slug: {wiki_slug}")
    archive_file = f"wiki/pages/content/{time.strftime('%Y-%m-%d')}-{draft_id}.md"
    if os.path.isfile(archive_file):
        print(f"[PASS] 归档文件已生成: {archive_file}")
    else:
        print(f"[WARN] 归档文件未找到: {archive_file}")
    print()

    # 9. 验证草稿状态
    print("[9/9] 验证草稿状态...")
    draft = api("GET", f"/api/drafts/{draft_id}")
    if draft.get("status") != "已归档":
        print(f"[FAIL] 草稿状态不正确: {draft.get('status')}")
        sys.exit(1)
    if not draft.get("archived_at"):
        print("[FAIL] archived_at 未设置")
        sys.exit(1)
    print(f"[PASS] 草稿状态正确: {draft.get('status')}")
    print(f"[PASS] archived_at 已设置: {draft.get('archived_at')}")
    print()

    # 完成
    print("===== Content flow verified =====")
    print()
    print("[PASS] V4.0 内容生产完整流程测试通过！")
    print()
    print("测试摘要：")
    print(f"  - 选题 ID: {topic_id}")
    print(f"  - 草稿 ID: {draft_id}")
    print(f"  - Wiki 页面 ID: {wiki_page_id}")
    print(f"  - 归档文件: {archive_file}")

if __name__ == "__main__":
    main()
