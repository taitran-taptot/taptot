-- Workout schedule frames by experience level × sessions/week
-- Applied via ensure_workout_schedule_frames at startup if missing.

CREATE TABLE IF NOT EXISTS workout_schedule_frames (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    code                TEXT NOT NULL UNIQUE,
    experience_level    INTEGER NOT NULL CHECK (experience_level BETWEEN 1 AND 5),
    sessions_per_week   INTEGER NOT NULL CHECK (sessions_per_week BETWEEN 1 AND 7),
    name_vi             TEXT NOT NULL,
    experience_label_vi TEXT NOT NULL,
    experience_range_vi TEXT NOT NULL,
    goal_vi             TEXT NOT NULL,
    sort_order          INTEGER NOT NULL DEFAULT 0,
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (experience_level, sessions_per_week)
);

CREATE INDEX IF NOT EXISTS idx_wsf_level_sessions
    ON workout_schedule_frames(experience_level, sessions_per_week);

CREATE TABLE IF NOT EXISTS workout_schedule_frame_days (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    frame_id     INTEGER NOT NULL REFERENCES workout_schedule_frames(id) ON DELETE CASCADE,
    day_index    INTEGER NOT NULL,
    label_vi     TEXT NOT NULL,
    split_role   TEXT NOT NULL,
    focus_vi     TEXT,
    notes_vi     TEXT,
    intensity    TEXT NOT NULL DEFAULT 'moderate',
    UNIQUE (frame_id, day_index)
);

CREATE INDEX IF NOT EXISTS idx_wsfd_frame
    ON workout_schedule_frame_days(frame_id);
