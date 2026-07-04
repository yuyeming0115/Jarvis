# Mac Mini Jarvis 系统优化搭建计划 V1.1

> 版本：V1.1 架构优化版  
> 生成日期：2026-07-03  
> 使用场景：带回家后，在 Mac Mini 上交给 Codex 按步骤搭建个人 Jarvis 系统。  
> 核心目标：先让系统每天可用，再逐步进化为多入口、AI 分类、内容生产和知识库助手。  
> 总原则：本地核心优先，外部入口后置；飞书先做，Telegram 预留，微信最后评估。

---

## 一、最终结论

这不是一个炫技项目，而是一个长期运行在 Mac Mini 上的个人效率系统。

最推荐路线：

```text
第一阶段：本地核心可用
第二阶段：本地可编辑 + SQLite
第三阶段：飞书入口和提醒闭环
第四阶段：AI 分类和内容草稿
第五阶段：Telegram 备用入口
第六阶段：微信 / 公众号 / 企业微信评估
```

不要一开始就做：

```text
微信机器人
Telegram 机器人
AI 自动分类
公网访问
自动发布内容
自动读取公司系统
自动读取聊天记录
```

第一晚只做一件事：

```text
让 Mac Mini 上能打开一个本地 Jarvis 工作台，并能稳定启动、停止、检查健康状态。
```

---

## 二、核心架构

系统采用分层结构：

```text
输入入口层 Input Adapters
  ├── Web 工作台
  ├── 飞书 Bot
  ├── Telegram Bot
  ├── 微信 / 公众号 / 企业微信
  └── 本地快捷指令

统一入口层 Inbox Gateway
  ├── 消息标准化
  ├── 来源识别
  ├── 去重
  ├── 鉴权
  ├── 限流
  └── 日志记录

Jarvis Core 本地核心
  ├── 任务管理
  ├── 灵感管理
  ├── 选题管理
  ├── 提醒管理
  ├── AI 分类
  ├── 内容草稿
  └── 知识库

数据层 Data Layer
  ├── SQLite
  ├── JSON 导出
  ├── Markdown Wiki
  └── 本地备份

输出通道 Output Adapters
  ├── Web 工作台
  ├── 飞书提醒
  ├── Telegram 回复
  ├── 微信提醒
  └── macOS 本地通知
```

关键原则：

```text
任何外部平台都不能直接耦合 Jarvis Core。
飞书、Telegram、微信都只能作为 Adapter。
所有消息必须先进入 Inbox Gateway，转成统一消息格式。
Jarvis Core 只处理统一数据结构。
```

---

## 三、平台接入策略

### 1. 飞书：第一入口

飞书适合作为第一入口，因为它适合：

```text
任务录入
提醒通知
多维表格同步
机器人回复
每日摘要
```

飞书第一阶段只做个人空间，不做公司系统抓取。

### 2. Telegram：备用远程入口

Telegram 适合后续作为：

```text
备用命令入口
远程状态查询
故障通知
紧急提醒
开发者控制台
```

先预留目录和接口，不第一晚接入。

### 3. 微信：最后评估

微信触达很强，但不建议一开始做。

微信可选路线：

```text
个人微信机器人：不推荐作为正式方案
微信公众号：适合未来内容分发和读者互动
企业微信：适合未来工作流和稳定提醒
```

当前结论：

```text
飞书 = 第一入口
Web 工作台 = 主控制台
SQLite = 主数据源
Telegram = 备用远程入口
微信 = 未来可选触达入口
AI = 后置增强能力
```

---

## 四、推荐安装目录

Mac Mini 上统一使用：

```bash
~/Jarvis
```

推荐目录结构：

```text
~/Jarvis/
├── README.md
├── .env.example
├── .env                         # 手动创建，不提交，不展示
├── apps/
│   └── workbench/
│       ├── index.html
│       ├── styles.css
│       ├── app.js
│       └── data/
│           ├── tasks.json
│           ├── ideas.json
│           ├── topics.json
│           ├── system-status.json
│           └── logs.json
├── backend/
│   ├── README.md
│   ├── main.py                   # V1.1 后启用
│   ├── requirements.txt          # V1.1 后启用
│   ├── core/
│   │   ├── __init__.py
│   │   ├── tasks.py
│   │   ├── ideas.py
│   │   ├── topics.py
│   │   ├── reminders.py
│   │   └── logs.py
│   ├── gateway/
│   │   ├── __init__.py
│   │   └── inbox.py
│   └── db/
│       ├── schema.sql
│       └── jarvis.sqlite3        # V1.2 后生成，不提交
├── adapters/
│   ├── feishu/
│   │   ├── README.md
│   │   ├── feishu_adapter.py     # V2.0 后启用
│   │   └── feishu.env.example
│   ├── telegram/
│   │   ├── README.md
│   │   ├── telegram_adapter.py   # 未来启用
│   │   └── telegram.env.example
│   └── wechat/
│       ├── README.md
│       └── wechat_evaluation.md
├── services/
│   ├── start-workbench.sh
│   ├── stop-workbench.sh
│   ├── health-check.sh
│   ├── backup-json.sh
│   ├── export-json.sh
│   └── sync-feishu-placeholder.sh
├── config/
│   ├── tinyrouter.config.example.yaml
│   ├── feishu.env.example
│   ├── telegram.env.example
│   └── launchd/
│       └── com.local.jarvis.workbench.plist.example
├── docs/
│   ├── 运行手册.md
│   ├── 数据结构.md
│   ├── 飞书接入清单.md
│   ├── 多入口接入策略.md
│   ├── 安全边界.md
│   └── 变更记录.md
├── wiki/
│   ├── raw/
│   ├── pages/
│   ├── index.md
│   └── log.md
├── prompts/
│   ├── classify-message.md
│   ├── draft-article.md
│   └── jimeng-shot-prompt.md
├── backups/
│   └── .gitkeep
└── logs/
    └── .gitkeep
```

---

## 五、版本路线总览

| 版本 | 名称 | 目标 | 是否第一晚做 |
|---|---|---|---|
| V1.0 | 本地展示版 | 工作台 + JSON + 启动脚本 | 是 |
| V1.1 | 本地可编辑版 | 页面内新增、修改、完成任务 | 否 |
| V1.2 | SQLite 数据库版 | 从 JSON 迁移到 SQLite | 否 |
| V1.3 | 本地服务化版 | launchd、备份、健康检查 | 否 |
| V2.0 | 飞书入口版 | 飞书消息入库 | 否 |
| V2.1 | 提醒闭环版 | 今日摘要、到期提醒、逾期提醒 | 否 |
| V2.2 | 飞书按钮版 | 完成、稍后提醒、查看详情 | 否 |
| V2.3 | Telegram 预留版 | 备用远程入口 | 否 |
| V2.4 | 微信评估版 | 评估公众号 / 企业微信 | 否 |
| V3.0 | AI 分类版 | 消息自动分类 | 否 |
| V3.1 | 内容草稿版 | 公众号、小红书、视频号草稿 | 否 |
| V3.2 | 知识库版 | Wiki 和长期记忆 | 否 |
| V3.3 | 多媒体提示词版 | 封面图、正文图、即梦分镜 prompt | 否 |

---

## 六、第一晚给 Codex 的总指令

回家后，在 Mac Mini 上打开 Codex，把下面这段话发给它：

```text
你现在要在我的 Mac Mini 上搭建个人 Jarvis 系统。

请严格执行这个计划文件：
《Mac Mini Jarvis 系统优化搭建计划 V1.1.md》

第一阶段只执行版本 V1.0：本地展示版。

不要接飞书。
不要接微信。
不要接 Telegram。
不要接 AI。
不要接真实 API Key。
不要安装大型依赖。
不要暴露公网。
不要自动启用 launchd。
不要删除我已有文件。
不要读取公司系统。
不要读取微信聊天记录。
不要读取个人隐私数据。

目标：
1. 创建 ~/Jarvis 目录结构。
2. 创建本地 JSON 数据。
3. 创建本地工作台页面。
4. 创建启动、停止、健康检查脚本。
5. 创建 .env.example。
6. 创建 launchd 示例文件，但不要正式加载。
7. 浏览器打开 http://127.0.0.1:8080/。
8. 跑通验收脚本。

所有涉及 API Key、Token、Secret 的地方，只生成 .env.example。
不要让我把真实密钥写进代码、日志或聊天窗口。

所有脚本必须：
- 使用 $HOME，不要硬编码用户名。
- 支持重复执行。
- 对端口占用做提示。
- 不要直接 kill 未知进程。
- 执行后更新 docs/变更记录.md。

完成后请告诉我：
- 工作台访问地址
- 创建了哪些文件
- 如何启动
- 如何停止
- 如何检查健康状态
- 下一步进入 V1.1 需要做什么
```

---

## 七、版本 V1.0：本地展示版

### 目标

让 Mac Mini 本地跑起一个可打开、可演示、可验收的 Jarvis 工作台。

这一版不依赖：

```text
飞书 API
微信 API
Telegram Bot
TinyRouter
OpenClaw
Hermes
真实 AI 模型
NAS
云服务器
公网域名
```

### V1.0 需要完成的任务

#### 1. 创建目录

```bash
mkdir -p "$HOME/Jarvis/apps/workbench/data"
mkdir -p "$HOME/Jarvis/backend/core"
mkdir -p "$HOME/Jarvis/backend/gateway"
mkdir -p "$HOME/Jarvis/backend/db"
mkdir -p "$HOME/Jarvis/adapters/feishu"
mkdir -p "$HOME/Jarvis/adapters/telegram"
mkdir -p "$HOME/Jarvis/adapters/wechat"
mkdir -p "$HOME/Jarvis/services"
mkdir -p "$HOME/Jarvis/config/launchd"
mkdir -p "$HOME/Jarvis/docs"
mkdir -p "$HOME/Jarvis/wiki/raw"
mkdir -p "$HOME/Jarvis/wiki/pages"
mkdir -p "$HOME/Jarvis/prompts"
mkdir -p "$HOME/Jarvis/backups"
mkdir -p "$HOME/Jarvis/logs"
```

#### 2. 创建本地数据文件

`apps/workbench/data/tasks.json`

```json
[
  {
    "task_id": "task_001",
    "title": "测试：完成 Jarvis 工作台本地部署",
    "description": "第一晚目标：Mac Mini 本地能打开 Jarvis 工作台，并能看到任务、灵感、选题、系统状态和日志。",
    "project": "Jarvis",
    "source": "local-json",
    "due_at": "2026-07-03 23:00",
    "priority": "P1",
    "status": "进行中",
    "reminder_level": "today",
    "tags": ["Jarvis", "本地部署"],
    "external_id": null,
    "sync_status": "local_only",
    "completed_at": null,
    "deleted_at": null,
    "created_at": "2026-07-03 20:00",
    "updated_at": "2026-07-03 20:00"
  }
]
```

`apps/workbench/data/ideas.json`

```json
[
  {
    "idea_id": "idea_001",
    "raw_text": "把飞书作为 Jarvis 第一入口，先做任务和提醒闭环；Telegram 预留，微信后评估。",
    "type": "系统规划",
    "tags": ["Jarvis", "飞书", "Telegram", "微信", "任务管理"],
    "status": "已记录",
    "ai_summary": "优先搭建本地核心和飞书入口，不急于接入微信和 Telegram。",
    "source": "local-json",
    "external_id": null,
    "sync_status": "local_only",
    "created_at": "2026-07-03 20:00",
    "updated_at": "2026-07-03 20:00"
  }
]
```

`apps/workbench/data/topics.json`

```json
[
  {
    "topic_id": "topic_001",
    "title": "普通人如何用 AI Agent 管理一天",
    "angle": "从任务提醒、灵感记录和内容生产三个场景切入",
    "platform": "公众号",
    "content_type": "文章",
    "target_audience": "想提升效率但没有技术背景的普通用户",
    "score": 82,
    "status": "候选",
    "draft_status": "未生成",
    "source": "local-json",
    "external_id": null,
    "sync_status": "local_only",
    "created_at": "2026-07-03 20:00",
    "updated_at": "2026-07-03 20:00"
  }
]
```

`apps/workbench/data/system-status.json`

```json
{
  "workbench": "online",
  "backend_api": "not_enabled",
  "database": "json_only",
  "feishu": "not_configured",
  "telegram": "reserved_not_configured",
  "wechat": "evaluation_only",
  "openclaw": "not_installed",
  "tinyrouter": "not_installed",
  "hermes": "not_installed",
  "last_sync_at": null,
  "safe_mode": true,
  "public_access": false
}
```

`apps/workbench/data/logs.json`

```json
[
  {
    "log_id": "log_001",
    "trace_id": "trace_init_001",
    "level": "info",
    "event_type": "system_init",
    "source": "local",
    "target": "workbench",
    "status": "success",
    "message": "本地 Jarvis 工作台初始化完成。",
    "cost": 0,
    "created_at": "2026-07-03 20:00"
  }
]
```

#### 3. 创建工作台页面

创建：

```text
~/Jarvis/apps/workbench/index.html
~/Jarvis/apps/workbench/styles.css
~/Jarvis/apps/workbench/app.js
```

V1.0 工作台必须支持：

```text
读取 data/tasks.json
读取 data/ideas.json
读取 data/topics.json
读取 data/system-status.json
读取 data/logs.json
显示今日任务
显示紧急任务
显示灵感池
显示选题池
显示 AI 建议占位区
显示系统状态
显示运行日志
无数据时显示空状态
读取失败时显示错误提示
```

页面标题建议：

```text
Jarvis Workbench
```

页面模块建议：

```text
顶部：系统状态总览
左侧：今日任务
中间：灵感和选题池
右侧：AI 建议和服务状态
底部：运行日志
```

#### 4. 创建启动脚本

`services/start-workbench.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

PORT="${JARVIS_WORKBENCH_PORT:-8080}"
APP_DIR="$HOME/Jarvis/apps/workbench"

if [ ! -d "$APP_DIR" ]; then
  echo "Workbench directory not found: $APP_DIR"
  exit 1
fi

EXISTING_PID=$(lsof -ti tcp:"$PORT" || true)
if [ -n "$EXISTING_PID" ]; then
  echo "Port $PORT is already in use by PID: $EXISTING_PID"
  echo "If this is Jarvis, run: bash $HOME/Jarvis/services/stop-workbench.sh"
  exit 1
fi

cd "$APP_DIR"
echo "Starting Jarvis workbench at http://127.0.0.1:$PORT/"
python3 -m http.server "$PORT" --bind 127.0.0.1
```

#### 5. 创建停止脚本

`services/stop-workbench.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

PORT="${JARVIS_WORKBENCH_PORT:-8080}"
PID=$(lsof -ti tcp:"$PORT" || true)

if [ -z "$PID" ]; then
  echo "No process is listening on port $PORT."
  exit 0
fi

echo "Process listening on port $PORT: $PID"
echo "Stopping it now."
kill $PID
```

说明：

```text
这个脚本比 lsof -ti tcp:8080 | xargs -r kill 更适合 macOS。
macOS 的 xargs 不一定支持 GNU xargs 的 -r 参数。
```

#### 6. 创建健康检查脚本

`services/health-check.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

PORT="${JARVIS_WORKBENCH_PORT:-8080}"
URL="http://127.0.0.1:$PORT/"

curl -fsS "$URL" >/dev/null
echo "Jarvis workbench is online: $URL"
```

#### 7. 创建备份脚本占位

`services/backup-json.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

SRC="$HOME/Jarvis/apps/workbench/data"
DEST="$HOME/Jarvis/backups/json-$(date +%Y%m%d-%H%M%S)"

mkdir -p "$DEST"
cp "$SRC"/*.json "$DEST"/
echo "JSON backup created: $DEST"
```

#### 8. 添加执行权限

```bash
chmod +x "$HOME/Jarvis/services/start-workbench.sh"
chmod +x "$HOME/Jarvis/services/stop-workbench.sh"
chmod +x "$HOME/Jarvis/services/health-check.sh"
chmod +x "$HOME/Jarvis/services/backup-json.sh"
```

#### 9. 创建 .env.example

`.env.example`

```bash
# Workbench
JARVIS_WORKBENCH_PORT=8080
JARVIS_SAFE_MODE=true
JARVIS_PUBLIC_ACCESS=false

# Feishu
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_VERIFICATION_TOKEN=
FEISHU_ENCRYPT_KEY=

# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USER_IDS=

# WeChat / Official Account / WeCom
WECHAT_APP_ID=
WECHAT_APP_SECRET=
WECHAT_TOKEN=
WECHAT_ENCODING_AES_KEY=

# TinyRouter
TINYROUTER_BASE_URL=http://127.0.0.1:20128/v1

# Database
JARVIS_DB_PATH=$HOME/Jarvis/backend/db/jarvis.sqlite3
```

注意：

```text
.env.example 只放字段名，不放真实密钥。
真实 .env 由用户手动创建。
不要把 .env 内容粘贴到聊天窗口。
不要把 .env 提交到 Git。
```

#### 10. 创建 launchd 示例文件

`config/launchd/com.local.jarvis.workbench.plist.example`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>com.local.jarvis.workbench</string>

    <key>ProgramArguments</key>
    <array>
      <string>/bin/bash</string>
      <string>/Users/YOUR_USER/Jarvis/services/start-workbench.sh</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/Users/YOUR_USER/Jarvis/logs/workbench.out.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USER/Jarvis/logs/workbench.err.log</string>
  </dict>
</plist>
```

注意：

```text
V1.0 只生成这个 example 文件。
不要自动 launchctl load。
不要第一晚启用开机自启。
等手动启动稳定后，再进入 V1.3。
```

---

## 八、V1.0 验收步骤

### 1. 启动工作台

```bash
cd "$HOME/Jarvis"
bash services/start-workbench.sh
```

### 2. 新开终端检查健康状态

```bash
bash "$HOME/Jarvis/services/health-check.sh"
```

### 3. 浏览器打开

```text
http://127.0.0.1:8080/
```

### 4. 验收标准

必须满足：

```text
页面能打开
能看到 tasks.json 里的测试任务
能看到 ideas.json 里的灵感
能看到 topics.json 里的选题
能看到系统状态
能看到日志记录
服务可以停止
服务可以重新启动
健康检查通过
```

### 5. 停止工作台

```bash
bash "$HOME/Jarvis/services/stop-workbench.sh"
```

---

## 九、版本 V1.1：本地可编辑版

### 目标

从“能看”变成“能用”。

新增本地 API 服务，让工作台可以：

```text
新增任务
编辑任务
完成任务
新增灵感
新增选题
写入操作日志
自动备份 JSON
```

推荐技术：

```text
后端：Python FastAPI
前端：原生 HTML/CSS/JS
数据：JSON + 自动备份
```

### V1.1 目录

```text
backend/
├── main.py
├── requirements.txt
├── core/
│   ├── tasks.py
│   ├── ideas.py
│   ├── topics.py
│   └── logs.py
└── gateway/
    └── inbox.py
```

### V1.1 API 草案

```text
GET    /api/tasks
POST   /api/tasks
PATCH  /api/tasks/{task_id}
POST   /api/tasks/{task_id}/complete

GET    /api/ideas
POST   /api/ideas

GET    /api/topics
POST   /api/topics

GET    /api/system-status
GET    /api/logs
POST   /api/inbox
```

### V1.1 验收标准

```text
可以在工作台新增一条任务
刷新页面后任务仍然存在
可以把任务标记为完成
新增灵感后能显示在页面
新增选题后能显示在页面
操作写入 logs.json
每次写入前自动备份 JSON
```

---

## 十、版本 V1.2：SQLite 数据库版

### 目标

从 JSON 临时数据源升级到 SQLite 主数据源。

SQLite 作为 Jarvis Core 的主数据源，JSON 只作为：

```text
导出
备份
调试
兼容旧版本
```

### 建议数据库表

```text
tasks
ideas
topics
messages
reminders
logs
sync_state
platform_accounts
```

### tasks 表建议字段

```text
task_id
 title
description
project
source
source_platform
source_message_id
due_at
reminder_at
priority
status
reminder_level
tags
external_id
sync_status
completed_at
deleted_at
created_at
updated_at
```

### messages 表建议字段

```text
message_id
platform
platform_user_id
chat_id
raw_text
message_type
normalized_intent
normalized_payload_json
status
error_message
received_at
processed_at
created_at
```

### V1.2 验收标准

```text
工作台通过本地 API 读取 SQLite
可以新增、修改、完成任务
每天可以导出 JSON 备份
旧的 JSON 示例数据可以迁移进 SQLite
```

---

## 十一、版本 V1.3：本地服务化版

### 目标

让 Mac Mini 长期稳定运行 Jarvis。

新增：

```text
launchd 正式服务配置
开机自启
健康检查
日志轮转
每日备份
崩溃自动重启
端口占用检测
安全模式
```

V1.3 才允许正式启用 launchd。

### V1.3 验收标准

```text
Mac Mini 重启后 Jarvis 自动启动
工作台可以打开
健康检查通过
日志文件正常生成
备份文件正常生成
```

---

## 十二、版本 V2.0：飞书入口版

### 目标

让飞书成为第一个真实移动端入口。

核心流程：

```text
飞书消息
  -> Feishu Adapter
  -> Inbox Gateway
  -> Jarvis Core
  -> SQLite
  -> 工作台展示
  -> 飞书回复
```

### 你需要手动准备

```text
注册或确认个人飞书账号
在飞书开放平台创建机器人应用
获取 APP_ID
获取 APP_SECRET
获取 Verification Token
获取 Encrypt Key
创建飞书多维表格
授权机器人访问多维表格
```

### 飞书多维表格建议

创建 6 张表：

```text
任务表
灵感表
选题池
消息表
运行日志
系统配置
```

### 飞书消息第一版分类规则

V2.0 可以先不用 AI，用规则分类：

```text
包含“提醒我”“明天”“周五”“截止”“到期” -> 任务
包含“选题”“写一篇”“拍一个”“视频”“公众号”“小红书” -> 选题
包含“想法”“灵感”“记一下” -> 灵感
包含“今天有什么”“状态”“进度” -> 查询
其他 -> 灵感
```

### V2.0 验收标准

```text
飞书发送：“周五交 Q3 方案，提前一天提醒我”
机器人回复：“已记录任务”
SQLite 新增任务
工作台刷新后出现任务
logs 记录 success
```

---

## 十三、版本 V2.1：提醒闭环版

### 目标

让 Jarvis 真正减少心智负担。

新增：

```text
每天 08:30 今日摘要
每天 21:30 明日预告
到期前提醒
逾期提醒
完成按钮
稍后提醒按钮
```

提醒优先级：

```text
第一优先：飞书
第二优先：Web 工作台
第三优先：Telegram，未来可选
第四优先：微信，未来可选
```

### V2.1 验收标准

```text
每天早上收到今日任务摘要
任务到期前收到提醒
逾期任务会提醒
可以标记完成
可以稍后提醒
```

---

## 十四、版本 V2.2：飞书按钮版

### 目标

让飞书消息不只是通知，还能交互。

支持按钮：

```text
完成
稍后提醒
查看详情
转为选题
转为灵感
取消任务
```

### V2.2 验收标准

```text
收到任务提醒后，点击“完成”
SQLite 中任务状态变为已完成
工作台同步显示已完成
logs 记录操作来源为 feishu_button
```

---

## 十五、版本 V2.3：Telegram 预留版

### 目标

预留 Telegram 备用入口，不一定马上启用。

目录：

```text
adapters/telegram/
├── README.md
├── telegram_adapter.py
└── telegram.env.example
```

Telegram 未来支持命令：

```text
/add 明天上午 10 点提醒我交方案
/idea 做一个 AI Agent 日常管理视频
/topic 写一篇关于普通人如何使用 Agent 的文章
/status
/today
/help
```

Telegram 适合：

```text
远程快速记录
状态查询
故障通知
备用提醒
```

不适合：

```text
作为第一入口
复杂任务看板
内容生产主界面
```

---

## 十六、版本 V2.4：微信入口评估版

### 目标

只评估，不急着开发。

微信入口分三类：

```text
个人微信机器人
微信公众号
企业微信
```

建议：

```text
个人微信机器人：不推荐作为正式方案
微信公众号：适合未来内容分发和读者互动
企业微信：适合未来稳定提醒和工作流
```

微信适合：

```text
最终提醒入口
内容触达入口
读者互动入口
```

微信不适合一开始做：

```text
Jarvis 主控入口
高频自动化控制入口
复杂任务管理入口
```

微信评估结论未明确前，不写真实代码，只写文档。

---

## 十七、版本 V3.0：AI 分类版

### 目标

让 Jarvis 能理解自然语言。

新增：

```text
TinyRouter
分类 Prompt
模型 fallback
消息分类结果入库
低风险自动入库
高风险人工确认
```

分类类型：

```text
任务
灵感
选题
动画需求
查询
系统指令
未知
```

### 分类原则

```text
能规则判断的，不调用 AI
低成本分类优先便宜模型
写作和复杂理解再用高质量模型
模型失败时 fallback
模型不确定时让用户确认
```

### V3.0 验收标准

```text
“明天写 AI Agent 普通人怎么用”
识别为选题，不误识别为任务。

“周五交 Q3 方案，提前一天提醒我”
识别为任务，并生成 due_at 和 reminder_at。
```

---

## 十八、版本 V3.1：内容草稿版

### 目标

从选题生成内容草稿。

支持：

```text
公众号草稿
小红书草稿
视频号脚本
即梦分镜提示词
封面图 Prompt
正文配图 Prompt
```

原则：

```text
只生成草稿
不自动发布
不自动发朋友圈
不自动发公众号
不自动发小红书
不自动打开生图网页
```

### V3.1 验收标准

```text
选中一个选题后，可以生成：
1. 公众号草稿
2. 小红书草稿
3. 视频号脚本
4. 封面图 Prompt
5. 正文配图 Prompt
```

---

## 十九、版本 V3.2：知识库版

### 目标

让 Jarvis 形成长期记忆。

目录：

```text
wiki/
├── raw/
├── pages/
├── index.md
└── log.md
```

支持：

```text
历史灵感查询
历史选题查询
草稿归档
写作偏好总结
常用表达沉淀
内容复盘
```

### V3.2 验收标准

```text
可以查询历史灵感
可以根据历史内容生成相似风格草稿
可以把终稿归档到 wiki
可以总结用户写作偏好
```

---

## 二十、统一消息格式

未来所有入口都必须转成统一格式。

```json
{
  "message_id": "msg_xxx",
  "platform": "feishu",
  "platform_user_id": "user_xxx",
  "chat_id": "chat_xxx",
  "raw_text": "周五交 Q3 方案，提前一天提醒我",
  "message_type": "text",
  "received_at": "2026-07-03 20:00:00",
  "normalized": {
    "intent": "task",
    "title": "交 Q3 方案",
    "due_at": "2026-07-10 18:00:00",
    "reminder_at": "2026-07-09 09:00:00",
    "priority": "P1"
  },
  "status": "processed"
}
```

Jarvis Core 只能处理这个统一格式，不直接处理飞书、Telegram、微信的原始消息。

---

## 二十一、安全边界

必须坚持：

```text
公司任务只允许手动录入，不主动抓取公司系统
飞书个人机器人只服务个人空间
不读取个人微信聊天记录
不抓取通讯录
不暴露公网
不把 OpenClaw、TinyRouter、Hermes 暴露到公网
所有真实密钥只放 .env
.env 不上传、不展示、不粘贴到聊天窗口
日志不记录密钥
日志不记录完整敏感内容
发布内容只进入草稿箱
缺席模式只自动生成，不自动发布
任何影响外部世界的动作必须人工确认
```

---

## 二十二、Codex 执行规则

让 Mac Mini 上的 Codex 遵守：

```text
先做 V1.0，不要跳到 V2 或 V3
不要把真实 API Key 写进代码
不要自动提交或发布任何外部内容
不要暴露本地服务到公网
启动服务优先监听 127.0.0.1
需要手机访问时，通过 Tailscale
每完成一个版本，必须跑验收脚本
每次修改后更新 docs/变更记录.md
如果某一步需要用户手动登录、授权、复制密钥，必须停下来问用户
不要删除用户已有文件
每一步执行前说明将创建或修改哪些文件
所有脚本必须支持重复执行
所有 shell 脚本必须 chmod +x
所有路径优先使用 $HOME
如果端口被占用，先提示，不要直接 kill 未知进程
```

---

## 二十三、第一晚最短执行路线

如果时间有限，只做这 10 步：

```text
1. 创建 ~/Jarvis 目录
2. 创建 apps/workbench 页面
3. 创建 data/*.json
4. 创建启动脚本
5. 创建停止脚本
6. 创建健康检查脚本
7. 创建 .env.example
8. 启动 http://127.0.0.1:8080/
9. 确认页面能读到 JSON 数据
10. 停止并重新启动一次，确认稳定
```

第一晚成功标准：

```text
Mac Mini 上能打开 Jarvis 工作台
工作台能显示任务、灵感、选题、系统状态和日志
不用任何 API Key
不用真实飞书
不用微信
不用 Telegram
不用 AI
可以停止
可以重启
健康检查通过
```

---

## 二十四、推荐执行排期

```text
第 1 晚：V1.0 本地展示版
第 2 晚：V1.1 本地可编辑版
第 3 晚：V1.2 SQLite 数据库版
第 4 晚：V1.3 开机自启和备份版
第 5-6 晚：V2.0 飞书入口版
第 7 晚：V2.1 提醒闭环版
后续：V2.3 Telegram 备用入口
最后：V2.4 微信 / 公众号 / 企业微信评估
再后：V3 AI 分类、内容草稿、知识库
```

---

## 二十五、最终交付物清单

### V1.0 完成后至少有

```text
~/Jarvis/
├── README.md
├── .env.example
├── apps/workbench/index.html
├── apps/workbench/styles.css
├── apps/workbench/app.js
├── apps/workbench/data/tasks.json
├── apps/workbench/data/ideas.json
├── apps/workbench/data/topics.json
├── apps/workbench/data/system-status.json
├── apps/workbench/data/logs.json
├── services/start-workbench.sh
├── services/stop-workbench.sh
├── services/health-check.sh
├── services/backup-json.sh
├── config/launchd/com.local.jarvis.workbench.plist.example
├── docs/运行手册.md
├── docs/数据结构.md
├── docs/多入口接入策略.md
├── docs/安全边界.md
└── docs/变更记录.md
```

### V1.1 完成后追加

```text
~/Jarvis/
├── backend/main.py
├── backend/requirements.txt
├── backend/core/tasks.py
├── backend/core/ideas.py
├── backend/core/topics.py
├── backend/core/logs.py
└── backend/gateway/inbox.py
```

### V1.2 完成后追加

```text
~/Jarvis/
├── backend/db/schema.sql
├── backend/db/jarvis.sqlite3
├── services/export-json.sh
└── services/backup-db.sh
```

### V2.0 完成后追加

```text
~/Jarvis/
├── adapters/feishu/README.md
├── adapters/feishu/feishu_adapter.py
├── adapters/feishu/feishu.env.example
├── services/sync-feishu.sh
├── services/send-daily-summary.sh
└── docs/飞书接入清单.md
```

### V3 完成后追加

```text
~/Jarvis/
├── config/tinyrouter.config.example.yaml
├── docs/WRITER.md
├── wiki/raw/
├── wiki/pages/
├── wiki/index.md
├── wiki/log.md
└── prompts/
    ├── classify-message.md
    ├── draft-article.md
    └── jimeng-shot-prompt.md
```

---

## 二十六、给未来 Codex 的最后提醒

你不是在搭一个炫技系统，而是在搭一个每天能帮用户减少心智负担的私人工作台。

优先级永远是：

```text
稳定记录 > 准时提醒 > 清晰展示 > 多端入口 > AI 建议 > 内容生产 > 自动化发布
```

任何自动化能力，只要会影响外部世界，都必须人工确认。

第一晚不要追求完整。
第一晚只追求一个结果：

```text
Mac Mini 上能稳定打开 Jarvis 工作台。
```

---

## 二十七、变更记录

### 2026-07-03

- 基于原 Mac Mini Jarvis 计划升级为 V1.1 架构优化版。
- 增加 Input Adapters、Inbox Gateway、Jarvis Core、Data Layer、Output Adapters 分层架构。
- 明确飞书为第一入口，Telegram 为备用入口，微信为未来评估入口。
- 增加 V1.1 本地可编辑版。
- 增加 V1.2 SQLite 数据库版。
- 增加 V1.3 本地服务化版。
- 优化 macOS 停止脚本，避免使用 xargs -r。
- 增加统一消息格式。
- 增加多平台入口策略。
- 强化安全边界：不读公司系统、不读微信聊天、不暴露公网、不自动发布。
- 明确第一晚只做 V1.0 本地展示版。
