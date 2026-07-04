-- V4.0 设置表迁移
-- 创建时间: 2026-07-04
-- 说明: 创建 settings 表用于存储运行时配置

BEGIN TRANSACTION;

-- ============================================
-- 创建 settings 表
-- ============================================

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT,
  is_secret INTEGER NOT NULL DEFAULT 0,
  description TEXT,
  group_name TEXT NOT NULL DEFAULT 'general',
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_settings_group
ON settings(group_name);

-- ============================================
-- 插入默认设置（从 .env 读取的初始值）
-- ============================================

-- LLM 配置
INSERT OR IGNORE INTO settings (key, value, is_secret, description, group_name, updated_at)
VALUES ('tinytrouter_base_url', 'http://127.0.0.1:20129/v1', 0, 'LLM API 端点地址', 'llm', datetime('now', 'localtime'));

INSERT OR IGNORE INTO settings (key, value, is_secret, description, group_name, updated_at)
VALUES ('tinytrouter_api_key', '', 1, 'LLM API 密钥（留空则不需要）', 'llm', datetime('now', 'localtime'));

INSERT OR IGNORE INTO settings (key, value, is_secret, description, group_name, updated_at)
VALUES ('tinytrouter_model_map', 'deepseek-chat=SS/deepseek-v4-flash,deepseek-reasoner=SS/deepseek-v4-flash', 0, '模型别名映射（格式：别名=实际模型,...）', 'llm', datetime('now', 'localtime'));

INSERT OR IGNORE INTO settings (key, value, is_secret, description, group_name, updated_at)
VALUES ('default_llm_model', 'deepseek-chat', 0, '默认 LLM 模型', 'llm', datetime('now', 'localtime'));

INSERT OR IGNORE INTO settings (key, value, is_secret, description, group_name, updated_at)
VALUES ('default_llm_temperature', '0.7', 0, '默认生成温度（0.0-2.0）', 'llm', datetime('now', 'localtime'));

INSERT OR IGNORE INTO settings (key, value, is_secret, description, group_name, updated_at)
VALUES ('default_llm_max_tokens', '4000', 0, '默认最大 token 数', 'llm', datetime('now', 'localtime'));

-- 图片生成配置
INSERT OR IGNORE INTO settings (key, value, is_secret, description, group_name, updated_at)
VALUES ('image_gen_base_url', '', 0, '图片生成 API 端点地址', 'image', datetime('now', 'localtime'));

INSERT OR IGNORE INTO settings (key, value, is_secret, description, group_name, updated_at)
VALUES ('image_gen_api_key', '', 1, '图片生成 API 密钥', 'image', datetime('now', 'localtime'));

INSERT OR IGNORE INTO settings (key, value, is_secret, description, group_name, updated_at)
VALUES ('image_gen_model', '', 0, '图片生成模型', 'image', datetime('now', 'localtime'));

-- 系统配置
INSERT OR IGNORE INTO settings (key, value, is_secret, description, group_name, updated_at)
VALUES ('jarvis_port', '8080', 0, 'Workbench 服务端口', 'system', datetime('now', 'localtime'));

INSERT OR IGNORE INTO settings (key, value, is_secret, description, group_name, updated_at)
VALUES ('jarvis_safe_mode', 'true', 0, '安全模式（只允许本机访问）', 'system', datetime('now', 'localtime'));

INSERT OR IGNORE INTO settings (key, value, is_secret, description, group_name, updated_at)
VALUES ('jarvis_public_access', 'false', 0, '允许局域网访问', 'system', datetime('now', 'localtime'));

-- 内容生成默认值
INSERT OR IGNORE INTO settings (key, value, is_secret, description, group_name, updated_at)
VALUES ('default_platform', '公众号', 0, '默认内容平台（公众号/小红书/视频号）', 'content', datetime('now', 'localtime'));

INSERT OR IGNORE INTO settings (key, value, is_secret, description, group_name, updated_at)
VALUES ('default_content_type', '文章', 0, '默认内容类型（文章/短文/脚本）', 'content', datetime('now', 'localtime'));

INSERT OR IGNORE INTO settings (key, value, is_secret, description, group_name, updated_at)
VALUES ('default_target_audience', '普通读者', 0, '默认目标读者', 'content', datetime('now', 'localtime'));

COMMIT;
