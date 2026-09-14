-- Workout schedule frames by experience level × sessions/week
-- Applied via ensure_workout_schedule_frames at startup if missing.

CREATE TABLE IF NOT EXISTS workout_schedule_frames (
    id                  SERIAL PRIMARY KEY,
    code                VARCHAR(64) NOT NULL UNIQUE,
    experience_level    SMALLINT NOT NULL CHECK (experience_level BETWEEN 1 AND 5),
    sessions_per_week   SMALLINT NOT NULL CHECK (sessions_per_week BETWEEN 1 AND 7),
    name_vi             VARCHAR(255) NOT NULL,
    experience_label_vi VARCHAR(120) NOT NULL,
    experience_range_vi VARCHAR(80) NOT NULL,
    goal_vi             TEXT NOT NULL,
    sort_order          INTEGER NOT NULL DEFAULT 0,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (experience_level, sessions_per_week)
);

CREATE INDEX IF NOT EXISTS idx_wsf_level_sessions
    ON workout_schedule_frames(experience_level, sessions_per_week);

CREATE TABLE IF NOT EXISTS workout_schedule_frame_days (
    id           SERIAL PRIMARY KEY,
    frame_id     INTEGER NOT NULL REFERENCES workout_schedule_frames(id) ON DELETE CASCADE,
    day_index    INTEGER NOT NULL,
    label_vi     VARCHAR(255) NOT NULL,
    split_role   VARCHAR(40) NOT NULL,
    focus_vi     TEXT,
    notes_vi     TEXT,
    intensity    VARCHAR(20) NOT NULL DEFAULT 'moderate',
    UNIQUE (frame_id, day_index)
);

CREATE INDEX IF NOT EXISTS idx_wsfd_frame
    ON workout_schedule_frame_days(frame_id);
