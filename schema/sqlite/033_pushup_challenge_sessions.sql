CREATE TABLE IF NOT EXISTS pushup_challenge_sessions (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    reps INTEGER,
    ticket_jti TEXT,
    entry_used_at TEXT,
    ip TEXT
);

CREATE INDEX IF NOT EXISTS idx_pushup_challenge_sessions_jti
    ON pushup_challenge_sessions(ticket_jti);
