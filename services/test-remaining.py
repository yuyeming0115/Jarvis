#!/usr/bin/env python3
"""
测试剩余两个场景 - 简化版
结果写入文件，避免 Windows 控制台编码问题
"""

import sys
import json
import time
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE = os.environ.get("JARVIS_BASE_URL", "http://127.0.0.1:8080")
RESULT_FILE = "test-result.txt"

def api(method, path, body=None, timeout=120):
    url = BASE + path
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body else None
    req = Request(url, data=data, headers={
        "Content-Type": "application/json; charset=utf-8",
    }, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            return {"ok": True, "status": resp.status, "data": json.loads(resp.read().decode("utf-8"))}
    except HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        try:
            return {"ok": False, "status": e.code, "data": json.loads(body_text)}
        except Exception:
            return {"ok": False, "status": e.code, "data": {"error": body_text[:300]}}
    except Exception as e:
        return {"ok": False, "status": 0, "data": {"error": str(e)}}

def log(msg):
    """写入文件 + 控制台（ASCII only）"""
    # 写入文件（UTF-8）
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    # 控制台输出（ASCII only）
    ascii_msg = msg.encode("ascii", errors="replace").decode("ascii")
    if ascii_msg != msg:
        ascii_msg = "[包含中文/Unicode] " + msg[:50].encode("ascii", errors="replace").decode("ascii")
    print(ascii_msg)

def test_xiaohongshu():
    log("=" * 60)
    log("[测试 1/2] 从 topic 生成小红书短文")
    log("=" * 60)
    
    # 创建选题
    log("\n[步骤 1] 创建小红书测试选题...")
    r = api("POST", "/api/topics", {
        "title": "AI 助手如何提升日常工作效率",
        "platform": "小红书",
        "content_type": "短文",
        "target_audience": "职场新人",
        "status": "候选",
        "tags": ["AI", "效率", "测试"]
    })
    if not r["ok"]:
        log(f"[FAIL] 创建选题失败: {r['data']}")
        return False
    topic_id = r["data"]["topic_id"]
    log(f"[PASS] 选题已创建: {topic_id}")
    
    # 生成草稿
    log("\n[步骤 2] 生成小红书短文...")
    r = api("POST", f"/api/topics/{topic_id}/generate-draft", {
        "channel": "xiaohongshu",
        "content_type": "post",
        "generation_mode": "auto"
    }, timeout=120)
    if not r["ok"]:
        log(f"[FAIL] 生成草稿失败: {r['data']}")
        return False
    draft_id = r["data"]["draft_id"]
    log(f"[PASS] 草稿已生成: {draft_id}")
    
    # 读取草稿
    log("\n[步骤 3] 读取草稿详情...")
    r = api("GET", f"/api/drafts/{draft_id}")
    if not r["ok"]:
        log(f"[FAIL] 读取草稿失败: {r['data']}")
        return False
    
    draft = r["data"]
    log(f"  标题: {draft.get('title', '')}")
    log(f"  状态: {draft.get('status', '')}")
    log(f"  字数: {draft.get('word_count', 0)}")
    log(f"  渠道: {draft.get('channel', '')}")
    log(f"  类型: {draft.get('content_type', '')}")
    
    if draft.get("word_count", 0) == 0:
        log("[FAIL] 草稿内容为空")
        return False
    
    log("\n[PASS] 小红书短文生成测试通过！")
    return True

def test_video_script():
    log("\n" + "=" * 60)
    log("[测试 2/2] 从 topic 生成视频口播稿")
    log("=" * 60)
    
    # 创建选题
    log("\n[步骤 1] 创建视频测试选题...")
    r = api("POST", "/api/topics", {
        "title": "如何用 AI 快速生成视频脚本",
        "platform": "视频号",
        "content_type": "口播稿",
        "target_audience": "内容创作者",
        "status": "候选",
        "tags": ["AI", "视频", "脚本", "测试"]
    })
    if not r["ok"]:
        log(f"[FAIL] 创建选题失败: {r['data']}")
        return False
    topic_id = r["data"]["topic_id"]
    log(f"[PASS] 选题已创建: {topic_id}")
    
    # 生成草稿
    log("\n[步骤 2] 生成视频口播稿...")
    r = api("POST", f"/api/topics/{topic_id}/generate-draft", {
        "channel": "video",
        "content_type": "script",
        "generation_mode": "auto"
    }, timeout=120)
    if not r["ok"]:
        log(f"[FAIL] 生成草稿失败: {r['data']}")
        return False
    draft_id = r["data"]["draft_id"]
    log(f"[PASS] 草稿已生成: {draft_id}")
    
    # 读取草稿
    log("\n[步骤 3] 读取草稿详情...")
    r = api("GET", f"/api/drafts/{draft_id}")
    if not r["ok"]:
        log(f"[FAIL] 读取草稿失败: {r['data']}")
        return False
    
    draft = r["data"]
    log(f"  标题: {draft.get('title', '')}")
    log(f"  状态: {draft.get('status', '')}")
    log(f"  字数: {draft.get('word_count', 0)}")
    log(f"  渠道: {draft.get('channel', '')}")
    log(f"  类型: {draft.get('content_type', '')}")
    
    if draft.get("word_count", 0) == 0:
        log("[FAIL] 草稿内容为空")
        return False
    
    log("\n[PASS] 视频口播稿生成测试通过！")
    return True

if __name__ == "__main__":
    # 清空结果文件
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        f.write("")
    
    log("Jarvis V4.0 剩余场景测试")
    log("=" * 60)
    
    results = []
    results.append(("[测试 1/2] 小红书短文", test_xiaohongshu()))
    results.append(("[测试 2/2] 视频口播稿", test_video_script()))
    
    log("\n" + "=" * 60)
    log("测试总结")
    log("=" * 60)
    for name, ok in results:
        status = "[PASS]" if ok else "[FAIL]"
        log(f"{status} {name}")
    
    if all(ok for _, ok in results):
        log("\n[PASS] All tests passed! V4.0 complete.")
        sys.exit(0)
    else:
        log("\n[FAIL] Some tests failed.")
        sys.exit(1)
