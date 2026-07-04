# Telegram Adapter

V2.3 版本已实现 Telegram Bot 备用入口。

## 配置方法

1. 在 Telegram 中找 @BotFather 创建一个 Bot，获取 Token
2. 在 `.env` 中添加：
   ```
   TELEGRAM_BOT_TOKEN=你的BotToken
   TELEGRAM_ALLOWED_USER_IDS=你的Telegram用户ID（可选，多个用逗号分隔）
   ```
3. 重启 Jarvis 工作台，Bot 会自动启动

## 获取你的 Telegram User ID

- 给 @userinfobot 发任意消息即可获取你的 ID
- 如果不配置 `TELEGRAM_ALLOWED_USER_IDS`，所有人都能用（不推荐）

## 支持的命令

- `/start` / `/help` - 显示帮助
- `/add <内容>` - 新增任务（支持自然语言时间，例：`/add 明天 10点交方案`）
- `/idea <内容>` - 记录灵感
- `/topic <内容>` - 记录选题
- `/today` - 查看今日待办
- `/status` - 查看系统状态

## 技术特点

- 使用长轮询（getUpdates），不需要公网 IP、不需要回调地址、不需要域名
- 后台线程运行，不阻塞主 HTTP 服务
- 配置了 Token 自动启动，没配置自动跳过
- 所有数据和飞书/工作台互通，统一入库
