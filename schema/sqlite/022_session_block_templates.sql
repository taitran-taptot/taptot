-- Session structure blocks by experience_level (L1–L3)
-- Applied via ensure_session_block_templates at startup.

CREATE TABLE IF NOT EXISTS session_block_templates (
    id                      INTEGER PRIMARY KEY,
    experience_level        INTEGER NOT NULL,
    sort_order              INTEGER NOT NULL,
    block_key               TEXT NOT NULL,
    label_vi                TEXT NOT NULL,
    plan_section            TEXT NOT NULL,
    movement_role           TEXT,
    count_min               INTEGER NOT NULL DEFAULT 0,
    count_max               INTEGER NOT NULL DEFAULT 0,
    duration_min_minutes    INTEGER,
    duration_max_minutes    INTEGER,
    is_optional             INTEGER NOT NULL DEFAULT 0,
    UNIQUE (experience_level, block_key)
);

CREATE INDEX IF NOT EXISTS idx_sbt_level_sort
    ON session_block_templates(experience_level, sort_order);
