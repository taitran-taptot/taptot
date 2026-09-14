CREATE TABLE IF NOT EXISTS feedback_suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_feedback_suggestions_user
    ON feedback_suggestions(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS trainer_contact_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    age INTEGER NOT NULL,
    phone_zalo TEXT NOT NULL,
    email TEXT NOT NULL,
    message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_trainer_contact_requests_created
    ON trainer_contact_requests(created_at DESC);
