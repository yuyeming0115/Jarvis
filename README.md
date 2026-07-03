# Jarvis

本目录是个人 Jarvis 系统的本地工作区。当前版本为 V2.1：飞书入口与提醒闭环版。

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
- 飞书真实回调、临时公网回调和模拟测试
- 飞书提醒文本解析为任务到期时间
- macOS 本地提醒服务
- 飞书公网回调健康监控

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

真实密钥只应写入本地 `.env`，不要粘贴到聊天窗口、日志或代码里。当前版本只处理你发给 Jarvis 机器人的消息，不抓取公司飞书或公司系统数据。

## 飞书本地模拟

```bash
bash "$HOME/Jarvis/services/simulate-feishu-event.sh" challenge
bash "$HOME/Jarvis/services/simulate-feishu-event.sh" task
```

飞书链路回归：

```bash
bash "$HOME/Jarvis/services/verify-feishu-flow.sh"
```

真实飞书接入需要安全 HTTPS 回调地址，不能直接把本机 `127.0.0.1:8080` 暴露公网。

临时回调测试：

```bash
bash "$HOME/Jarvis/services/start-feishu-tunnel.sh"
bash "$HOME/Jarvis/services/show-feishu-callback-url.sh"
```

飞书 Verification Token 写入 `$HOME/Jarvis/.env` 后，launchd 启动的 Jarvis 会自动读取。

## 提醒服务

查看所有常驻服务：

```bash
bash "$HOME/Jarvis/services/status-launchd.sh"
```

干跑提醒扫描，不弹通知：

```bash
cd "$HOME/Jarvis"
python3 -m backend.core.reminders --once --dry-run
```
