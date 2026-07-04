-- V4.0 内容生产 MVP 数据库迁移
-- 创建时间: 2026-07-04
-- 说明: 为 drafts 表添加缺失字段，创建 prompt_versions 和 content_reviews 表

BEGIN TRANSACTION;

-- ============================================
-- 1. 为 drafts 表添加缺失字段
-- ============================================

-- 检查并添加 source_message_id 字段
ALTER TABLE drafts ADD COLUMN source_message_id TEXT;

-- 添加 channel 字段（对应原来的 platform）
ALTER TABLE drafts ADD COLUMN channel TEXT;

-- 添加 body 字段（对应原来的 content，保持兼容）
ALTER TABLE drafts ADD COLUMN body TEXT;

-- 添加 summary 字段
ALTER TABLE drafts ADD COLUMN summary TEXT;

-- 添加 review_status 字段（审核状态）
ALTER TABLE drafts ADD COLUMN review_status TEXT NOT NULL DEFAULT 'pending';

-- 添加 prompt_version 字段
ALTER TABLE drafts ADD COLUMN prompt_version TEXT;

-- 添加 model_name 字段（对应原来的 ai_model，保持兼容）
ALTER TABLE drafts ADD COLUMN model_name TEXT;

-- 添加 generation_mode 字段（生成模式：template 或 llm）
ALTER TABLE drafts ADD COLUMN generation_mode TEXT NOT NULL DEFAULT 'template';

-- 添加 input_context_json 字段（输入上下文）
ALTER TABLE drafts ADD COLUMN input_context_json TEXT;

-- 添加 output_metadata_json 字段（输出元数据）
ALTER TABLE drafts ADD COLUMN output_metadata_json TEXT;

-- 添加 review_notes 字段（审核备注）
ALTER TABLE drafts ADD COLUMN review_notes TEXT;

-- 添加 rejection_reason 字段（驳回原因）
ALTER TABLE drafts ADD COLUMN rejection_reason TEXT;

-- 添加 approved_at 字段（批准时间）
ALTER TABLE drafts ADD COLUMN approved_at TEXT;

-- 添加 archived_at 字段（归档时间）
ALTER TABLE drafts ADD COLUMN archived_at TEXT;

-- ============================================
-- 2. 创建 prompt_versions 表
-- ============================================

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

-- ============================================
-- 3. 创建 content_reviews 表
-- ============================================

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

-- ============================================
-- 4. 数据迁移：从旧字段迁移到新字段
-- ============================================

-- 将 platform 字段的值复制到 channel 字段
UPDATE drafts SET channel = platform WHERE channel IS NULL;

-- 将 content 字段的值复制到 body 字段
UPDATE drafts SET body = content WHERE body IS NULL;

-- 将 ai_model 字段的值复制到 model_name 字段
UPDATE drafts SET model_name = ai_model WHERE model_name IS NULL;

-- 根据原有 status 设置 review_status
-- 如果 status 是 '定稿'，设置为 'approved'
UPDATE drafts SET review_status = 'approved' WHERE status = '定稿' AND review_status = 'pending';

-- 如果 status 是 '已发布'，设置为 'approved'
UPDATE drafts SET review_status = 'approved' WHERE status = '已发布' AND review_status = 'pending';

COMMIT;

-- ============================================
-- 5. 创建索引（为 drafts 表的新字段）
-- ============================================

CREATE INDEX IF NOT EXISTS idx_drafts_channel ON drafts(channel);
CREATE INDEX IF NOT EXISTS idx_drafts_review_status ON drafts(review_status);
CREATE INDEX IF NOT EXISTS idx_drafts_generation_mode ON drafts(generation_mode);
