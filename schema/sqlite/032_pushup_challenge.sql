CREATE TABLE IF NOT EXISTS pushup_challenge_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL,
    birth_year INTEGER NOT NULL,
    age_band TEXT NOT NULL,
    reps INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_pushup_challenge_reps
    ON pushup_challenge_entries(reps DESC, created_at);

CREATE INDEX IF NOT EXISTS idx_pushup_challenge_age_reps
    ON pushup_challenge_entries(age_band, reps DESC, created_at);
