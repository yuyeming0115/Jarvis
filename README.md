# Jarvis

本目录是个人 Jarvis 系统的本地工作区。当前版本为 V1.2：SQLite 数据库版。

## 当前能力

- 本地工作台页面
- SQLite 主数据源
- JSON 导出和备份
- 新增任务、灵感、选题
- 修改任务状态和优先级
- 完成任务
- 写入前自动备份 SQLite 和 JSON 快照
- 启动、停止、健康检查脚本
- launchd 开机自启和崩溃自动重启
- 每日维护备份
- JSON 手动备份脚本
- 日志轮转

## 快速启动

```bash
bash "$HOME/Jarvis/services/start-workbench.sh"
```

打开：

```text
http://127.0.0.1:8080/
```

## 健康检查

```bash
bash "$HOME/Jarvis/services/health-check.sh"
```

## 停止

```bash
bash "$HOME/Jarvis/services/stop-workbench.sh"
```

如果已经安装 launchd 服务，停止/移除常驻服务使用：

```bash
bash "$HOME/Jarvis/services/uninstall-launchd.sh"
```

## 备份和 Git

当前有三种保护：

- 手动 JSON 导出：运行 `services/export-json.sh`
- 手动数据库备份：运行 `services/backup-db.sh`
- 每日自动维护：launchd 会在每天 03:15 运行 `services/run-maintenance.sh`
- 自动备份：每次通过工作台写入前，会在 `backups/` 生成 SQLite 和 JSON 快照
- 开发版本：本地 Git 记录代码和文档历史，真实运行数据不进入 Git

## 安全说明

V1.2 不接飞书、微信、Telegram、AI 模型或真实 API Key。真实密钥只应写入本地 `.env`，不要粘贴到聊天窗口、日志或代码里。
