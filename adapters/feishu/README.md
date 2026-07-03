# Feishu Adapter

V2.0 提供本地飞书事件回调适配器。

## 本地回调地址

```text
POST http://127.0.0.1:8080/api/feishu/event
```

真实飞书开放平台不能直接访问 `127.0.0.1`，因此正式联通前需要准备一个安全的公网 HTTPS 回调方案。

## 当前支持

- URL 验证 challenge
- 明文 `im.message.receive_v1` 文本事件
- Verification Token 校验
- 规则分类：任务、灵感、选题
- 写入 `messages` 表
- 路由到任务、灵感或选题数据表

## 当前不支持

- 加密事件解密
- 飞书消息主动回复
- 飞书多维表格同步

## 本地模拟

```bash
bash "$HOME/Jarvis/services/simulate-feishu-event.sh" challenge
bash "$HOME/Jarvis/services/simulate-feishu-event.sh" task
bash "$HOME/Jarvis/services/simulate-feishu-event.sh" idea
bash "$HOME/Jarvis/services/simulate-feishu-event.sh" topic
```
