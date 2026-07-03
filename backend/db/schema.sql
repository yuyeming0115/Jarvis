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

CREATE TABLE IF NOT EXISTS system_status (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  payload_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_at ON tasks(due_at);
CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs(created_at);
