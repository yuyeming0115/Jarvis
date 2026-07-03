# 备份与 Git 策略

## 当前备份方式

V1.2 已支持三种备份：

- 手动 JSON 导出：运行 `bash "$HOME/Jarvis/services/export-json.sh"`
- 手动 SQLite 备份：运行 `bash "$HOME/Jarvis/services/backup-db.sh"`
- 自动备份：每次通过本地 API 写入前，复制 SQLite，并导出 JSON 快照到 `backups/auto-data-*`

这意味着误操作后，可以优先恢复 SQLite；必要时也可以从 JSON 快照恢复单条数据。

## 是否需要 GitHub

建议需要，但不要第一时间公开或推送。

推荐顺序：

1. 先建立本地 Git 仓库，记录代码和文档变更。
2. `.env`、本地 JSON 数据、日志、PID、备份目录、数据库文件不进入 Git。
3. V1.1 稳定后，再创建 GitHub 私有仓库。
4. 远程仓库只同步代码、文档、示例配置，不同步真实密钥、本地 JSON 数据和个人数据备份。

## 后续增强

- V1.3 增加定时备份和日志轮转。
- 如接入 NAS，可以把 `backups/` 同步到 NAS 或 Time Machine。
