---
title: Jarvis 内容生产 MVP 迭代计划
version: V4.0
date: 2026-07-04
status: ready-for-codex
target_repo_path: "$HOME/Jarvis"
recommended_doc_path: "docs/Jarvis内容生产MVP_V4.0_Codex迭代计划.md"
---

# Jarvis 内容生产 MVP 迭代计划 V4.0

> 本文档是给 Codex 使用的开发规格书。  
> 目标不是重写 Jarvis，而是在现有本地工作台、SQLite、launchd、Feishu/Telegram 入口、AI 分类能力之上，补齐一条稳定的内容生产闭环。

---

## 0. Codex 执行规则

Codex 必须按以下规则执行本计划：

1. **一次只实现一个里程碑。**
2. **每个里程碑完成后必须运行对应 smoke test。**
3. **不得删除旧功能、旧接口、旧数据。**
4. **不得重构前端框架。**
5. **不得引入 React/Vue/Postgres/Redis/Celery/OpenClaw/Hermes。**
6. **不得自动发布任何内容到外部平台。**
7. **不得写入真实 API Key、Token、Secret。**
8. **所有新增写入操作必须进入 SQLite，并保持 JSON 导出/备份兼容。**
9. **所有失败必须有日志，不能静默失败。**
10. **所有新功能必须有回滚路径。**

---

## 1. 当前系统基线

### 1.1 已有能力

从当前文档和代码状态推断，Jarvis 已经具备以下能力：

- 本地 Workbench 页面。
- SQLite 作为主数据源。
- JSON 作为导出、备份、调试格式。
- launchd 管理工作台、维护任务、提醒服务、Feishu 公网链路监控。
- Feishu 消息入口。
- Telegram 备用入口。
- 统一 Inbox Gateway。
- AI 分类能力。
- 规则 fallback。
- 低置信度人工确认。
- 任务、灵感、选题、消息、系统状态、日志等基本数据结构。
- 前端已有 `tasks / ideas / topics / drafts / wiki / media` 等入口占位。
- 安全模式、本机访问、AI 配置状态等 UI 标识。

### 1.2 当前缺口

当前缺的不是入口，也不是更大的 Agent 框架，而是：

```text
idea/topic/message
    -> topic pool
    -> draft generation
    -> review queue
    -> manual approval
    -> wiki/archive
    -> future style corpus
```

也就是一条可回滚、可测试、可人工审核的内容生产流水线。

---

## 2. V4.0 总目标

V4.0 的目标是把 Jarvis 从“任务/灵感/选题管理器”升级为：

> 本地优先的个人内容生产工作台。

第一阶段只做 MVP：

- 能从已有选题生成内容草稿。
- 能保存草稿。
- 能查看、编辑、重写草稿。
- 能人工审核草稿。
- 能批准、驳回、归档草稿。
- 能把已批准草稿归档到本地 wiki。
- 能通过 smoke test 验证完整链路。

---

## 3. 明确非目标

V4.0 不做以下事情：

- 不接微信公众号发布 API。
- 不接小红书发布 API。
- 不接视频号发布 API。
- 不做自动发布。
- 不做自动群发。
- 不做微信个人号机器人。
- 不读取微信聊天记录。
- 不读取公司系统。
- 不做联系人抓取。
- 不引入 OpenClaw。
- 不引入 Hermes。
- 不迁移 Postgres。
- 不引入 Redis。
- 不引入 Celery。
- 不重写前端为 React/Vue。
- 不开放公网访问 Jarvis 核心服务。
- 不在代码、日志、文档中写真实密钥。
- 不改变现有任务、灵感、选题、消息的主流程。

---

## 4. 推荐版本切分

```text
V4.0.0  冻结当前基线与备份
V4.0.1  新增内容草稿数据模型
V4.0.2  新增 drafts 后端 CRUD
V4.0.3  新增 prompt loader 与内容生成器
V4.0.4  前端接入内容草稿页面
V4.0.5  新增人工审核状态机
V4.0.6  新增 wiki 归档
V4.0.7  新增 smoke/regression/export 脚本与文档
```

---

## 5. V4.0.0：冻结当前基线

### 5.1 目标

在开发 V4.0 前，确认当前系统可启动、可备份、可回归。

### 5.2 Codex 执行步骤

```bash
cd "$HOME/Jarvis"

bash services/status-launchd.sh || true
bash services/health-check.sh || true
bash services/api-smoke-test.sh || true
bash services/backup-db.sh
bash services/export-json.sh
git status
```

### 5.3 产出

新增或更新：

```text
docs/变更记录.md
docs/Jarvis内容生产MVP_V4.0_Codex迭代计划.md
```

### 5.4 验收标准

- 当前工作台可以启动。
- 当前 API smoke test 不比开发前更差。
- SQLite 备份成功。
- JSON 导出成功。
- Git 工作区状态清晰。

### 5.5 回滚方式

如果后续任何一步失败，先回滚代码，再恢复开发前 SQLite 备份。

---

## 6. V4.0.1：新增内容草稿数据模型

### 6.1 目标

新增 `drafts`、`prompt_versions`、`content_reviews` 三张表，不破坏旧表。

### 6.2 新增文件

```text
backend/db/migrations/004_content_mvp.sql
```

### 6.3 SQL 迁移草案

```sql
BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS drafts (
  draft_id TEXT PRIMARY KEY,
  topic_id TEXT,
  idea_id TEXT,
  source_message_id TEXT,

  title TEXT NOT NULL,
  channel TEXT NOT NULL,
  content_type TEXT NOT NULL,

  outline TEXT,
  body TEXT NOT NULL,
  summary TEXT,

  status TEXT NOT NULL DEFAULT 'draft',
  review_status TEXT NOT NULL DEFAULT 'pending',

  prompt_version TEXT,
  model_name TEXT,
  generation_mode TEXT NOT NULL DEFAULT 'template',

  input_context_json TEXT,
  output_metadata_json TEXT,

  review_notes TEXT,
  rejection_reason TEXT,

  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  approved_at TEXT,
  archived_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_drafts_topic_id
ON drafts(topic_id);

CREATE INDEX IF NOT EXISTS idx_drafts_idea_id
ON drafts(idea_id);

CREATE INDEX IF NOT EXISTS idx_drafts_status
ON drafts(status);

CREATE INDEX IF NOT EXISTS idx_drafts_review_status
ON drafts(review_status);

CREATE INDEX IF NOT EXISTS idx_drafts_created_at
ON drafts(created_at);

CREATE TABLE IF NOT EXISTS prompt_versions (
  prompt_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  version TEXT NOT NULL,
  channel TEXT,
  content_type TEXT,
  file_path TEXT NOT NULL,
  description TEXT,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_prompt_versions_active
ON prompt_versions(is_active);

CREATE TABLE IF NOT EXISTS content_reviews (
  review_id TEXT PRIMARY KEY,
  draft_id TEXT NOT NULL,
  action TEXT NOT NULL,
  review_notes TEXT,
  created_at TEXT NOT NULL,

  FOREIGN KEY (draft_id) REFERENCES drafts(draft_id)
);

CREATE INDEX IF NOT EXISTS idx_content_reviews_draft_id
ON content_reviews(draft_id);

COMMIT;
```

### 6.4 状态枚举

`drafts.status` 只允许以下值：

```text
draft
reviewing
approved
rejected
archived
```

`drafts.review_status` 只允许以下值：

```text
pending
approved
rejected
needs_rewrite
```

### 6.5 验收标准

```bash
cd "$HOME/Jarvis"
python3 -m backend.db.migrate
sqlite3 backend/db/jarvis.sqlite3 ".schema drafts"
sqlite3 backend/db/jarvis.sqlite3 ".schema prompt_versions"
sqlite3 backend/db/jarvis.sqlite3 ".schema content_reviews"
bash services/api-smoke-test.sh
```

### 6.6 回滚方式

因为是新增表，回滚时不得删除旧表。若必须回滚，只撤销新代码引用，不主动 drop 表。

---

## 7. V4.0.2：新增 drafts 后端 CRUD

### 7.1 目标

实现内容草稿的创建、读取、更新、列表查询。

### 7.2 新增文件

```text
backend/core/drafts.py
```

### 7.3 修改文件

根据当前后端结构，修改实际 API 入口文件，例如：

```text
backend/app.py
backend/server.py
backend/main.py
```

如果当前项目不是这些文件名，Codex 需要先搜索现有 `/api/tasks`、`/api/topics` 的定义位置，再按同样风格接入。

### 7.4 API 合约

#### GET /api/drafts

查询草稿列表。

Query 参数：

```text
status
review_status
channel
content_type
limit
offset
```

返回示例：

```json
{
  "items": [
    {
      "draft_id": "draft_20260704_001",
      "title": "AI Agent 如何帮普通人减少心智负担",
      "channel": "wechat",
      "content_type": "article",
      "status": "draft",
      "review_status": "pending",
      "created_at": "2026-07-04T10:00:00+08:00",
      "updated_at": "2026-07-04T10:00:00+08:00"
    }
  ],
  "total": 1
}
```

#### GET /api/drafts/{draft_id}

返回单条草稿详情。

#### POST /api/drafts

手动创建草稿。

请求示例：

```json
{
  "title": "AI Agent 如何帮普通人减少心智负担",
  "channel": "wechat",
  "content_type": "article",
  "outline": "1. 问题\n2. 场景\n3. 方法\n4. 总结",
  "body": "正文内容……",
  "topic_id": "topic_xxx",
  "idea_id": null,
  "source_message_id": null
}
```

#### PATCH /api/drafts/{draft_id}

更新草稿标题、正文、状态、审核备注等字段。

### 7.5 验收标准

新增脚本：

```text
services/drafts-api-smoke-test.sh
```

脚本要求：

```bash
#!/usr/bin/env bash
set -euo pipefail

BASE="${JARVIS_BASE_URL:-http://127.0.0.1:8080}"

curl -fsS "$BASE/api/drafts" >/tmp/jarvis-drafts-list.json

curl -fsS -X POST "$BASE/api/drafts" \
  -H "Content-Type: application/json" \
  -d '{
    "title":"V4.0 草稿 API 测试",
    "channel":"wechat",
    "content_type":"article",
    "body":"这是一条 V4.0 草稿 API 测试内容。"
  }' >/tmp/jarvis-draft-create.json

echo "Drafts API verified"
```

通过条件：

```bash
bash services/drafts-api-smoke-test.sh
bash services/api-smoke-test.sh
```

### 7.6 回滚方式

- 保留数据库表。
- 移除或注释新增 `/api/drafts` 路由。
- 旧 `/api/tasks`、`/api/ideas`、`/api/topics` 必须不受影响。

---

## 8. V4.0.3：新增 prompt loader 与内容生成器

### 8.1 目标

从 topic/idea/message 生成草稿，并保存到 `drafts` 表。

### 8.2 新增文件

```text
backend/core/prompts.py
backend/core/content_generator.py

prompts/draft-wechat-article.md
prompts/draft-xiaohongshu-post.md
prompts/draft-video-script.md
prompts/rewrite-draft.md
prompts/review-rubric.md
```

### 8.3 生成模式

必须支持两种生成模式：

```text
template
llm
```

要求：

- 如果 LLM 未配置，必须使用 `template` fallback。
- 如果 LLM 调用失败，必须记录错误并 fallback 到 `template`。
- 生成结果必须保存 `generation_mode`。
- 生成结果必须保存 `prompt_version`。
- 生成结果必须保存 `model_name`，未使用模型则填 `template`.

### 8.4 新增 API

#### POST /api/topics/{topic_id}/generate-draft

请求示例：

```json
{
  "channel": "wechat",
  "content_type": "article",
  "generation_mode": "auto"
}
```

返回示例：

```json
{
  "draft_id": "draft_20260704_001",
  "topic_id": "topic_abc",
  "title": "AI Agent 如何帮普通人减少心智负担",
  "channel": "wechat",
  "content_type": "article",
  "generation_mode": "llm",
  "status": "draft",
  "review_status": "pending"
}
```

### 8.5 支持的首批内容类型

只做三类：

```text
wechat + article
xiaohongshu + short_post
video + script
```

不要扩展更多渠道。

### 8.6 prompt 文件要求

每个 prompt 文件必须包含：

```text
# 角色
# 输入
# 输出要求
# 风格约束
# 安全边界
# 输出格式
```

### 8.7 template fallback 示例逻辑

当 LLM 不可用时，生成以下结构：

```markdown
# {topic_title}

## 核心观点

{topic_summary 或 topic_title 的扩展说明}

## 正文草稿

这是基于当前选题生成的模板草稿。请在人工审核阶段补充案例、细节和表达风格。

## 待补充

- 具体案例
- 个人观点
- 发布渠道适配
```

### 8.8 验收标准

新增脚本：

```text
services/content-generation-smoke-test.sh
```

脚本必须验证：

- 找到或创建一个测试 topic。
- 调用 `/api/topics/{topic_id}/generate-draft`。
- 返回 `draft_id`。
- `/api/drafts/{draft_id}` 能读取。
- `body` 非空。
- `status = draft`。
- `review_status = pending`。

输出：

```text
Content generation verified
```

### 8.9 回滚方式

- 保留已生成草稿。
- 停用生成 API。
- 前端隐藏生成按钮。
- 不删除 drafts 表。

---

## 9. V4.0.4：前端接入内容草稿页面

### 9.1 目标

在现有 Workbench 中激活 `内容草稿` tab，不重写 UI。

### 9.2 修改文件

```text
apps/workbench/app.js
apps/workbench/styles.css
apps/workbench/index.html
```

如果项目实际路径不同，以现有 `index.html`、`app.js`、`styles.css` 为准。

### 9.3 UI 功能

`drafts` tab 需要支持：

- 草稿列表。
- 按状态筛选。
- 按渠道筛选。
- 按内容类型筛选。
- 点击查看详情。
- 编辑标题。
- 编辑正文。
- 保存。
- 复制正文。
- 进入审核。
- 批准。
- 驳回。
- 重写。
- 归档。

### 9.4 选题详情页新增按钮

在 topic 详情页增加：

```text
生成公众号文章
生成小红书短文
生成视频口播稿
```

按钮调用：

```text
POST /api/topics/{topic_id}/generate-draft
```

### 9.5 前端安全要求

- 不显示任何 API Key。
- 不显示任何 Token。
- 不暴露公网地址。
- 不出现“发布”按钮。
- 只能出现“复制”“归档”“导出”按钮。
- 如果以后出现“发布”能力，也必须是独立版本，不属于 V4.0。

### 9.6 验收标准

手工验收：

1. 打开 Workbench。
2. 点击 `内容草稿`。
3. 能看到草稿列表。
4. 点击草稿能看到详情。
5. 修改正文并保存成功。
6. 从选题生成一篇草稿。
7. 新草稿出现在列表中。
8. 旧任务、灵感、选题页面仍可用。

脚本验收：

```bash
bash services/api-smoke-test.sh
bash services/drafts-api-smoke-test.sh
bash services/content-generation-smoke-test.sh
```

### 9.7 回滚方式

- 隐藏前端 `drafts` tab 的新增交互。
- 保留后端 API。
- 不影响旧 tabs。

---

## 10. V4.0.5：新增人工审核状态机

### 10.1 目标

草稿必须经过人工审核，才能进入归档。

### 10.2 新增/修改文件

```text
backend/core/content_reviews.py
backend/core/drafts.py
apps/workbench/app.js
```

### 10.3 API 合约

#### POST /api/drafts/{draft_id}/submit-review

状态变化：

```text
draft -> reviewing
review_status: pending
```

#### POST /api/drafts/{draft_id}/approve

状态变化：

```text
reviewing/draft -> approved
review_status: approved
approved_at: now
```

请求示例：

```json
{
  "review_notes": "可以作为公众号初稿，发布前再补一个案例。"
}
```

#### POST /api/drafts/{draft_id}/reject

状态变化：

```text
reviewing/draft -> rejected
review_status: rejected
```

请求示例：

```json
{
  "rejection_reason": "观点太泛，缺少具体场景。"
}
```

#### POST /api/drafts/{draft_id}/rewrite

行为：

- 不覆盖原草稿。
- 生成新草稿或创建修订版本。
- 新草稿必须保留 `source_draft_id` 或在 `input_context_json` 中记录来源。

### 10.4 审核动作记录

每次审核动作都写入 `content_reviews`：

```text
approve
reject
submit_review
rewrite
archive
```

### 10.5 验收标准

新增脚本：

```text
services/content-review-smoke-test.sh
```

脚本必须验证：

- 创建草稿。
- submit review。
- approve。
- 检查 `content_reviews` 有记录。
- 检查草稿状态为 `approved`。

输出：

```text
Content review verified
```

### 10.6 回滚方式

- 保留审核记录。
- 禁用审核按钮。
- 草稿仍可通过 CRUD 查看和编辑。

---

## 11. V4.0.6：新增 wiki 归档

### 11.1 目标

只有 `approved` 草稿可以归档到本地 wiki。

### 11.2 新增文件

```text
backend/core/wiki_archive.py
```

### 11.3 归档路径

```text
wiki/pages/content/YYYY-MM-DD-{draft_id}.md
```

示例：

```text
wiki/pages/content/2026-07-04-draft_20260704_001.md
```

### 11.4 归档 Markdown 格式

```markdown
---
draft_id: draft_20260704_001
title: AI Agent 如何帮普通人减少心智负担
channel: wechat
content_type: article
status: approved
archived_at: 2026-07-04T10:30:00+08:00
prompt_version: draft-wechat-article@v1
model_name: gpt-compatible
---

# AI Agent 如何帮普通人减少心智负担

正文……
```

### 11.5 API 合约

#### POST /api/drafts/{draft_id}/archive

规则：

- 只有 `status = approved` 才能归档。
- 未批准草稿调用该接口必须返回 400。
- 归档后状态变为 `archived`。
- `archived_at` 写入当前时间。
- 归档路径写入 `output_metadata_json`。

### 11.6 验收标准

新增脚本：

```text
services/wiki-archive-smoke-test.sh
```

脚本必须验证：

- 未批准草稿不能归档。
- 批准草稿可以归档。
- wiki 文件存在。
- wiki 文件包含 frontmatter。
- 草稿状态变为 `archived`。

输出：

```text
Wiki archive verified
```

### 11.7 回滚方式

- 如果归档失败，不改变草稿状态。
- 如果写文件成功但 DB 更新失败，日志必须提示人工修复。
- 不自动删除已归档 Markdown。

---

## 12. V4.0.7：新增完整内容流水线测试

### 12.1 目标

一条命令验证内容生产 MVP 是否可用。

### 12.2 新增文件

```text
services/content-smoke-test.sh
services/content-regression-test.sh
services/export-drafts.sh
docs/内容生产运行手册.md
```

### 12.3 content-smoke-test.sh 必须验证

完整链路：

```text
create topic
-> generate draft
-> read draft
-> edit draft
-> submit review
-> approve
-> archive
-> verify wiki file
```

成功输出：

```text
Content flow verified
```

### 12.4 content-regression-test.sh 必须验证

最低限度：

- 旧 API 可用。
- drafts API 可用。
- generation fallback 可用。
- review API 可用。
- archive API 可用。
- 不出现公网发布接口。
- 不出现真实 secret。

### 12.5 export-drafts.sh

导出路径：

```text
backups/export-drafts-YYYYMMDD-HHMMSS/
```

导出格式：

```text
drafts.json
drafts.csv
approved-drafts/
archived-drafts/
```

### 12.6 验收标准

```bash
bash services/content-smoke-test.sh
bash services/content-regression-test.sh
bash services/api-smoke-test.sh
```

全部通过后，V4.0 可标记为完成。

---

## 13. 最终验收清单

V4.0 完成必须满足：

- [ ] Workbench 可正常打开。
- [ ] 旧任务功能可用。
- [ ] 旧灵感功能可用。
- [ ] 旧选题功能可用。
- [ ] 旧消息功能可用。
- [ ] `/api/drafts` 可用。
- [ ] 可以从 topic 生成公众号文章草稿。
- [ ] 可以从 topic 生成小红书短文草稿。
- [ ] 可以从 topic 生成视频口播稿。
- [ ] LLM 未配置时 template fallback 可用。
- [ ] 草稿可以保存到 SQLite。
- [ ] 草稿可以在前端查看。
- [ ] 草稿可以在前端编辑。
- [ ] 草稿可以提交审核。
- [ ] 草稿可以批准。
- [ ] 草稿可以驳回。
- [ ] 只有批准草稿可以归档。
- [ ] 归档生成 Markdown 文件。
- [ ] `content-smoke-test.sh` 输出 `Content flow verified`。
- [ ] 没有自动发布能力。
- [ ] 没有真实 secret 写入代码。
- [ ] 没有公网暴露核心服务。
- [ ] 没有引入 OpenClaw/Hermes/Postgres/React。

---

## 14. 建议目录结构

V4.0 完成后，推荐形成以下结构：

```text
$HOME/Jarvis/
  apps/
    workbench/
      index.html
      app.js
      styles.css

  backend/
    core/
      drafts.py
      content_generator.py
      content_reviews.py
      prompts.py
      wiki_archive.py
      llm.py
      reminders.py
    db/
      jarvis.sqlite3
      migrations/
        004_content_mvp.sql

  prompts/
    draft-wechat-article.md
    draft-xiaohongshu-post.md
    draft-video-script.md
    rewrite-draft.md
    review-rubric.md

  services/
    api-smoke-test.sh
    drafts-api-smoke-test.sh
    content-generation-smoke-test.sh
    content-review-smoke-test.sh
    wiki-archive-smoke-test.sh
    content-smoke-test.sh
    content-regression-test.sh
    export-drafts.sh

  wiki/
    pages/
      content/

  docs/
    Jarvis内容生产MVP_V4.0_Codex迭代计划.md
    内容生产运行手册.md
    变更记录.md
```

---

## 15. Codex 推荐执行顺序

Codex 应按以下顺序提交变更：

### Step 1：基线检查

```text
不改代码，只运行当前 smoke test、backup、export。
```

### Step 2：数据库迁移

```text
新增 004_content_mvp.sql。
运行迁移。
确认旧表不受影响。
```

### Step 3：drafts.py

```text
实现草稿 CRUD。
接入 /api/drafts。
补 drafts-api-smoke-test.sh。
```

### Step 4：prompts.py

```text
实现 prompt 文件加载。
支持 prompt version。
支持缺失 prompt 的明确错误。
```

### Step 5：content_generator.py

```text
实现 topic -> draft。
先 template fallback。
再接入现有 core/llm.py。
```

### Step 6：前端 drafts tab

```text
激活内容草稿页面。
接入列表、详情、编辑、保存。
```

### Step 7：review queue

```text
加入 submit-review / approve / reject / rewrite。
所有动作写 content_reviews。
```

### Step 8：wiki archive

```text
只允许 approved 草稿归档。
写 Markdown 文件。
更新草稿 archived 状态。
```

### Step 9：完整 smoke test

```text
实现 content-smoke-test.sh。
跑完整链路。
```

### Step 10：文档更新

```text
更新 内容生产运行手册.md。
更新 变更记录.md。
```

---

## 16. V4.1 暂缓项

V4.0 稳定前不要做：

- 风格样本库自动学习。
- 批量标题生成。
- 热点素材抓取。
- 多平台发布排期。
- Feishu 卡片审核。
- 公众号草稿箱 API。
- 小红书发布 API。
- 视频号发布 API。
- 向量数据库。
- 长期记忆 Hermes。
- OpenClaw Agent 框架。
- 多用户权限系统。
- 云端固定 relay。

这些可以进入 V4.1/V4.2，但不能挤进 V4.0。

---

## 17. 关键设计判断

### 17.1 为什么先做内容草稿，而不是先做知识库？

因为高质量知识库的前提是有“已审核终稿”。  
如果先把未审核草稿、灵感碎片、半成品内容全部放进知识库，后续生成会放大噪声。

正确顺序是：

```text
草稿
-> 人工审核
-> 批准终稿
-> 归档
-> 样本库/知识库
```

### 17.2 为什么不先引入 OpenClaw/Hermes？

因为当前系统最缺的是稳定流水线，不是更强 Agent。  
在没有稳定审核、归档、回归测试之前，引入更强 Agent 只会增加不可控性。

### 17.3 为什么不迁移 Postgres？

因为当前是个人本地系统，SQLite 足够支撑 V4.0。  
迁移数据库会显著增加复杂度，且不能直接提升内容生产闭环。

### 17.4 为什么必须有 template fallback？

因为内容生产功能不能完全依赖 LLM 配置。  
即使 AI 未配置，系统也应该能生成结构化草稿，保证前后端链路可测试。

---

## 18. V4.0 完成定义

当以下命令全部通过时，V4.0 才算完成：

```bash
cd "$HOME/Jarvis"

bash services/api-smoke-test.sh
bash services/drafts-api-smoke-test.sh
bash services/content-generation-smoke-test.sh
bash services/content-review-smoke-test.sh
bash services/wiki-archive-smoke-test.sh
bash services/content-smoke-test.sh
bash services/content-regression-test.sh
```

最终输出必须包含：

```text
Content flow verified
```

### 18.1 2026-07-04 验证记录

本次在 Windows 本地环境完成等价 smoke 验证，结果全部通过：

- 前端资源验证：`/`、`/app.js`、`/styles.css` 均可访问。
- API 写入验证：创建并完成测试任务通过。
- 草稿 CRUD 验证通过。
- 内容生成验证通过，未配置 LLM 时走 template fallback。
- 内容审核验证通过，`submit-review` 与 `approve` 能正确写入 `review_status`。
- Wiki 归档验证通过，未批准草稿被拒绝，批准草稿可归档并写入 `archived_at`。
- 完整内容流验证通过：选题 -> 草稿 -> 编辑 -> 审核 -> 批准 -> 归档。
- 回归验证通过，确认未暴露公网发布接口。

本次同步修复了 `do_DELETE`、`get_topic()` 和 V4.0 草稿字段持久化缺口；运行时需确保 `8080` 端口只有一个 Jarvis 后端实例，避免旧进程干扰 smoke 结果。

---

## 19. 最后提醒

V4.0 的核心不是“让 Jarvis 更聪明”，而是让 Jarvis 具备稳定产出内容草稿的能力。

本阶段唯一主线是：

```text
选题 -> 草稿 -> 审核 -> 归档
```

所有不能服务这条主线的功能，都应推迟。
