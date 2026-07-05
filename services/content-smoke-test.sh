#!/usr/bin/env bash
set -euo pipefail

# V4.0 内容生产完整流程 Smoke Test
# 测试从选题到归档的完整链路

BASE="${JARVIS_BASE_URL:-http://127.0.0.1:8080}"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || command -v python || true)}"
if [ -z "$PYTHON_BIN" ]; then
  echo "✗ 未找到 Python，请先安装 python3"
  exit 1
fi

echo "===== Jarvis V4.0 内容生产 Smoke Test ====="
echo ""

# 1. 创建测试选题
echo "步骤 1: 创建测试选题..."
topic_resp=$(curl -s -X POST "$BASE/api/topics" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "V4.0 测试选题 - 内容生产流程",
    "platform": "公众号",
    "content_type": "文章",
    "target_audience": "测试用户",
    "status": "候选",
    "tags": ["测试"]
  }')

topic_id=$(echo "$topic_resp" | "$PYTHON_BIN" -c "import sys, json; print(json.load(sys.stdin).get('topic_id', ''))")

if [ -z "$topic_id" ]; then
  echo "✗ 创建选题失败"
  exit 1
fi

echo "✓ 选题已创建: $topic_id"
echo ""

# 2. 从选题生成草稿
echo "步骤 2: 从选题生成草稿..."
draft_resp=$(curl -s -X POST "$BASE/api/topics/$topic_id/generate-draft" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "wechat",
    "content_type": "article",
    "generation_mode": "auto"
  }')

draft_id=$(echo "$draft_resp" | "$PYTHON_BIN" -c "import sys, json; print(json.load(sys.stdin).get('draft_id', ''))")

if [ -z "$draft_id" ]; then
  echo "✗ 生成草稿失败"
  echo "$draft_resp"
  exit 1
fi

echo "✓ 草稿已生成: $draft_id"
echo ""

# 3. 读取草稿详情
echo "步骤 3: 读取草稿详情..."
draft_detail=$(curl -s "$BASE/api/drafts/$draft_id")
draft_title=$(echo "$draft_detail" | "$PYTHON_BIN" -c "import sys, json; print(json.load(sys.stdin).get('title', ''))")
draft_status=$(echo "$draft_detail" | "$PYTHON_BIN" -c "import sys, json; print(json.load(sys.stdin).get('status', ''))")
draft_word_count=$(echo "$draft_detail" | "$PYTHON_BIN" -c "import sys, json; print(json.load(sys.stdin).get('word_count', 0))")

echo "  标题: $draft_title"
echo "  状态: $draft_status"
echo "  字数: $draft_word_count"

if [ "$draft_word_count" -eq 0 ]; then
  echo "✗ 草稿内容为空"
  exit 1
fi

echo "✓ 草稿内容非空"
echo ""

# 4. 编辑草稿
echo "步骤 4: 编辑草稿..."
edit_resp=$(curl -s -X PATCH "$BASE/api/drafts/$draft_id" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "'"$draft_title"' (已编辑)"
  }')

echo "✓ 草稿已编辑"
echo ""

# 5. 提交审核
echo "步骤 5: 提交审核..."
submit_resp=$(curl -s -X POST "$BASE/api/drafts/$draft_id/submit-review" \
  -H "Content-Type: application/json" \
  -d '{
    "submit_notes": "Smoke test 提交审核"
  }')

echo "✓ 已提交审核"
echo ""

# 6. 批准草稿
echo "步骤 6: 批准草稿..."
approve_resp=$(curl -s -X POST "$BASE/api/drafts/$draft_id/approve" \
  -H "Content-Type: application/json" \
  -d '{
    "review_notes": "Smoke test 批准"
  }')

draft_status=$(curl -s "$BASE/api/drafts/$draft_id" | "$PYTHON_BIN" -c "import sys, json; print(json.load(sys.stdin).get('status', ''))")

if [ "$draft_status" != "定稿" ]; then
  echo "✗ 批准失败，当前状态: $draft_status"
  exit 1
fi

echo "✓ 草稿已批准，状态: $draft_status"
echo ""

# 7. 归档草稿
echo "步骤 7: 归档草稿..."
archive_resp=$(curl -s -X POST "$BASE/api/drafts/$draft_id/archive-wiki" \
  -H "Content-Type: application/json" \
  -d '{}')

wiki_page_id=$(echo "$archive_resp" | "$PYTHON_BIN" -c "import sys, json; print(json.load(sys.stdin).get('page_id', ''))")

if [ -z "$wiki_page_id" ]; then
  echo "✗ 归档失败"
  echo "$archive_resp"
  exit 1
fi

echo "✓ 草稿已归档到 wiki: $wiki_page_id"
echo ""

# 8. 验证 wiki 文件
echo "步骤 8: 验证 wiki 文件..."
wiki_detail=$(curl -s "$BASE/api/wiki/$wiki_page_id")
wiki_slug=$(echo "$wiki_detail" | "$PYTHON_BIN" -c "import sys, json; print(json.load(sys.stdin).get('slug', ''))")

echo "  Wiki slug: $wiki_slug"

# 检查归档文件是否存在
archive_file="wiki/pages/content/$(date +%Y-%m-%d)-${draft_id}.md"
if [ -f "$archive_file" ]; then
  echo "✓ 归档文件已生成: $archive_file"
else
  echo "⚠ 归档文件未找到: $archive_file"
fi

echo ""

# 9. 验证草稿状态
echo "步骤 9: 验证草稿状态..."
draft_status=$(curl -s "$BASE/api/drafts/$draft_id" | "$PYTHON_BIN" -c "import sys, json; print(json.load(sys.stdin).get('status', ''))")
draft_archived_at=$(curl -s "$BASE/api/drafts/$draft_id" | "$PYTHON_BIN" -c "import sys, json; print(json.load(sys.stdin).get('archived_at', ''))")

if [ "$draft_status" != "已归档" ]; then
  echo "✗ 草稿状态不正确: $draft_status"
  exit 1
fi

if [ -z "$draft_archived_at" ]; then
  echo "✗ archived_at 未设置"
  exit 1
fi

echo "✓ 草稿状态正确: $draft_status"
echo "✓ archived_at 已设置: $draft_archived_at"
echo ""

# 完成
echo "===== Content flow verified ====="
echo ""
echo "✅ V4.0 内容生产完整流程测试通过！"
echo ""
echo "测试摘要："
echo "  - 选题 ID: $topic_id"
echo "  - 草稿 ID: $draft_id"
echo "  - Wiki 页面 ID: $wiki_page_id"
echo "  - 归档文件: $archive_file"

if [ "${JARVIS_KEEP_TEST_DATA:-0}" != "1" ]; then
  curl -s -X DELETE "$BASE/api/wiki/$wiki_page_id" > /dev/null || true
  curl -s -X DELETE "$BASE/api/drafts/$draft_id" > /dev/null || true
  curl -s -X DELETE "$BASE/api/topics/$topic_id" > /dev/null || true
  rm -f "$archive_file"
  echo ""
  echo "测试数据已清理。如需保留测试数据，请设置 JARVIS_KEEP_TEST_DATA=1。"
fi
