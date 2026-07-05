PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tasks (
  task_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  project TEXT,
  source TEXT,
  due_at TEXT,
  priority TEXT,
  status TEXT,
  reminder_level TEXT,
  tags_json TEXT NOT NULL DEFAULT '[]',
  external_id TEXT,
  sync_status TEXT,
  completed_at TEXT,
  deleted_at TEXT,
  created_at TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS ideas (
  idea_id TEXT PRIMARY KEY,
  raw_text TEXT NOT NULL,
  type TEXT,
  tags_json TEXT NOT NULL DEFAULT '[]',
  status TEXT,
  ai_summary TEXT,
  source TEXT,
  external_id TEXT,
  sync_status TEXT,
  created_at TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS topics (
  topic_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  angle TEXT,
  platform TEXT,
  content_type TEXT,
  target_audience TEXT,
  score INTEGER,
  status TEXT,
  draft_status TEXT,
  source TEXT,
  external_id TEXT,
  sync_status TEXT,
  created_at TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS logs (
  log_id TEXT PRIMARY KEY,
  trace_id TEXT,
  level TEXT,
  event_type TEXT,
  source TEXT,
  target TEXT,
  status TEXT,
  message TEXT,
  cost REAL DEFAULT 0,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS messages (
  message_id TEXT PRIMARY KEY,
  platform TEXT,
  platform_user_id TEXT,
  chat_id TEXT,
  raw_text TEXT NOT NULL,
  message_type TEXT,
  normalized_intent TEXT,
  normalized_payload_json TEXT NOT NULL DEFAULT '{}',
  source_event_json TEXT NOT NULL DEFAULT '{}',
  status TEXT,
  error_message TEXT,
  received_at TEXT,
  processed_at TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS system_status (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reminder_notifications (
  task_id TEXT PRIMARY KEY,
  due_at TEXT,
  notified_at TEXT,
  channel TEXT,
  status TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_at ON tasks(due_at);
CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs(created_at);

CREATE INDEX IF NOT EXISTS idx_messages_platform ON messages(platform);
CREATE INDEX IF NOT EXISTS idx_messages_received_at ON messages(received_at);
CREATE INDEX IF NOT EXISTS idx_reminder_notifications_status ON reminder_notifications(status);

CREATE TABLE IF NOT EXISTS drafts (
  draft_id TEXT PRIMARY KEY,
  topic_id TEXT,
  idea_id TEXT,
  title TEXT NOT NULL,
  platform TEXT,
  content_type TEXT,
  outline_json TEXT NOT NULL DEFAULT '[]',
  content TEXT,
  word_count INTEGER DEFAULT 0,
  status TEXT,
  ai_model TEXT,
  generation_params_json TEXT NOT NULL DEFAULT '{}',
  source TEXT,
  source_message_id TEXT,
  channel TEXT,
  body TEXT,
  summary TEXT,
  review_status TEXT NOT NULL DEFAULT 'pending',
  prompt_version TEXT,
  model_name TEXT,
  generation_mode TEXT NOT NULL DEFAULT 'template',
  input_context_json TEXT,
  output_metadata_json TEXT,
  review_notes TEXT,
  rejection_reason TEXT,
  approved_at TEXT,
  archived_at TEXT,
  deleted_at TEXT,
  created_at TEXT,
  updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_drafts_status ON drafts(status);
CREATE INDEX IF NOT EXISTS idx_drafts_topic_id ON drafts(topic_id);
CREATE INDEX IF NOT EXISTS idx_drafts_channel ON drafts(channel);
CREATE INDEX IF NOT EXISTS idx_drafts_review_status ON drafts(review_status);
CREATE INDEX IF NOT EXISTS idx_drafts_generation_mode ON drafts(generation_mode);

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

CREATE TABLE IF NOT EXISTS wiki_pages (
  page_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  content_md TEXT NOT NULL DEFAULT '',
  summary TEXT,
  tags_json TEXT NOT NULL DEFAULT '[]',
  source_type TEXT,
  source_id TEXT,
  word_count INTEGER DEFAULT 0,
  status TEXT,
  deleted_at TEXT,
  created_at TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS media_prompts (
  prompt_id TEXT PRIMARY KEY,
  draft_id TEXT,
  topic_id TEXT,
  title TEXT NOT NULL,
  prompt_type TEXT NOT NULL,
  platform TEXT,
  prompts_json TEXT NOT NULL DEFAULT '[]',
  style_reference TEXT,
  music_suggestion TEXT,
  ai_model TEXT,
  status TEXT,
  deleted_at TEXT,
  created_at TEXT,
  updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_wiki_slug ON wiki_pages(slug);
CREATE INDEX IF NOT EXISTS idx_wiki_status ON wiki_pages(status);
CREATE INDEX IF NOT EXISTS idx_wiki_tags ON wiki_pages(tags_json);
CREATE INDEX IF NOT EXISTS idx_media_prompts_draft_id ON media_prompts(draft_id);
CREATE INDEX IF NOT EXISTS idx_media_prompts_type ON media_prompts(prompt_type);

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
