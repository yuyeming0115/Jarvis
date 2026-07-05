#!/usr/bin/env bash
set -euo pipefail

# V4.0 导出草稿脚本
# 导出路径：backups/export-drafts-YYYYMMDD-HHMMSS/

BASE="${JARVIS_BASE_URL:-http://127.0.0.1:8080}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
EXPORT_DIR="backups/export-drafts-${TIMESTAMP}"

echo "===== 导出草稿 ====="
echo "导出目录: $EXPORT_DIR"
echo ""

# 创建导出目录
mkdir -p "$EXPORT_DIR"
mkdir -p "$EXPORT_DIR/approved-drafts"
mkdir -p "$EXPORT_DIR/archived-drafts"

# 1. 导出所有草稿到 JSON
echo "步骤 1: 导出草稿 JSON..."
curl -s "$BASE/api/drafts" > "$EXPORT_DIR/drafts.json"

if [ ! -s "$EXPORT_DIR/drafts.json" ]; then
  echo "✗ 导出草稿 JSON 失败"
  exit 1
fi

echo "✓ 草稿 JSON 已导出: $EXPORT_DIR/drafts.json"

# 2. 导出 CSV（简化版本，使用 Python 转换）
echo ""
echo "步骤 2: 导出草稿 CSV..."
python3 - <<'EOF'
import json, csv, sys

with open('$EXPORT_DIR/drafts.json', 'r', encoding='utf-8') as f:
    drafts = json.load(f)

if not drafts:
    print("未找到草稿")
    sys.exit(0)

with open('$EXPORT_DIR/drafts.csv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['draft_id', 'title', 'channel', 'content_type', 'status', 'review_status', 'word_count', 'created_at'])
    for draft in drafts:
        writer.writerow([
            draft.get('draft_id', ''),
            draft.get('title', ''),
            draft.get('channel', draft.get('platform', '')),
            draft.get('content_type', ''),
            draft.get('status', ''),
            draft.get('review_status', ''),
            draft.get('word_count', 0),
            draft.get('created_at', '')
        ])

print("✓ 草稿 CSV 已导出: $EXPORT_DIR/drafts.csv")
EOF'

# 3. 导出批准的草稿内容
echo ""
echo "步骤 3: 导出批准的草稿内容..."
approved_drafts=$(curl -s "$BASE/api/drafts?status=定稿" || echo "[]")

echo "$approved_drafts" | python3 - <<'EOF'
import json, sys, os

drafts = json.load(sys.stdin)
export_dir = '$EXPORT_DIR/approved-drafts'

for draft in drafts:
    draft_id = draft.get('draft_id', 'unknown')
    title = draft.get('title', 'untitled')
    content = draft.get('content', draft.get('body', ''))
    
    # 保存为 Markdown 文件
    filename = f"{export_dir}/{draft_id}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# {title}\n\n")
        f.write(f"**ID**: {draft_id}\n\n")
        f.write(f"**状态**: {draft.get('status', '')}\n\n")
        f.write(f"**创建时间**: {draft.get('created_at', '')}\n\n")
        f.write("---\n\n")
        f.write(content)
    
    print(f"  ✓ {draft_id}.md")
EOF'

echo "✓ 批准的草稿已导出: $EXPORT_DIR/approved-drafts/"

# 4. 导出已归档的草稿内容
echo ""
echo "步骤 4: 导出已归档的草稿内容..."
archived_drafts=$(curl -s "$BASE/api/drafts?status=已归档" || echo "[]")

echo "$archived_drafts" | python3 - <<'EOF'
import json, sys, os

drafts = json.load(sys.stdin)
export_dir = '$EXPORT_DIR/archived-drafts'

for draft in drafts:
    draft_id = draft.get('draft_id', 'unknown')
    title = draft.get('title', 'untitled')
    content = draft.get('content', draft.get('body', ''))
    
    # 保存为 Markdown 文件
    filename = f"{export_dir}/{draft_id}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# {title}\n\n")
        f.write(f"**ID**: {draft_id}\n\n")
        f.write(f"**状态**: {draft.get('status', '')}\n\n")
        f.write(f"**归档时间**: {draft.get('archived_at', '')}\n\n")
        f.write("---\n\n")
        f.write(content)
    
    print(f"  ✓ {draft_id}.md")
EOF'

echo "✓ 已归档的草稿已导出: $EXPORT_DIR/archived-drafts/"

# 5. 生成导出报告
echo ""
echo "步骤 5: 生成导出报告..."
total_count=$(curl -s "$BASE/api/drafts" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
approved_count=$(curl -s "$BASE/api/drafts?status=定稿" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
archived_count=$(curl -s "$BASE/api/drafts?status=已归档" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")

cat > "$EXPORT_DIR/export-report.md" <<'REPORT'
# 草稿导出报告

**导出时间**: $(date +'%Y-%m-%d %H:%M:%S')

## 统计

- **总草稿数**: ${total_count}
- **批准草稿数**: ${approved_count}
- **已归档草稿数**: ${archived_count}

## 文件列表

- `drafts.json` - 所有草稿的 JSON 数据
- `drafts.csv` - 所有草稿的 CSV 表格
- `approved-drafts/` - 批准的草稿 Markdown 文件
- `archived-drafts/` - 已归档的草稿 Markdown 文件

REPORT'

echo "✓ 导出报告已生成: $EXPORT_DIR/export-report.md"

echo ""
echo "===== 导出完成 ====="
echo ""
echo "✅ 草稿导出完成！"
echo ""
echo "导出摘要:"
echo "  - 总草稿数: ${total_count}"
echo "  - 批准草稿数: ${approved_count}"
echo "  - 已归档草稿数: ${archived_count}"
echo "  - 导出目录: $EXPORT_DIR"
