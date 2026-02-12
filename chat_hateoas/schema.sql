PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS conversations (
  id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY,
  conversation_id INTEGER NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  raw_text TEXT NOT NULL,
  rendered_html TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('streaming', 'complete', 'error')),
  created_at TEXT NOT NULL,
  FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS assistant_metadata (
  message_id INTEGER PRIMARY KEY,
  provider TEXT NOT NULL,
  model_id TEXT NOT NULL,
  stop_reason TEXT NOT NULL,
  input_tokens INTEGER NOT NULL,
  output_tokens INTEGER NOT NULL,
  latency_ms INTEGER NOT NULL,
  tool_events_json TEXT NOT NULL,
  raw_event_count INTEGER NOT NULL,
  FOREIGN KEY (message_id) REFERENCES messages (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS message_feedback (
  message_id INTEGER PRIMARY KEY,
  vote TEXT NOT NULL CHECK (vote IN ('up', 'down')),
  updated_at TEXT NOT NULL,
  FOREIGN KEY (message_id) REFERENCES messages (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
  ON messages (conversation_id, created_at);
