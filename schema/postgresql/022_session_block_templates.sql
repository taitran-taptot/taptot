-- Session structure blocks by experience_level (L1–L3)
-- Applied via ensure_session_block_templates at startup.

CREATE TABLE IF NOT EXISTS session_block_templates (
    id                      SERIAL PRIMARY KEY,
    experience_level        SMALLINT NOT NULL CHECK (experience_level BETWEEN 1 AND 5),
    sort_order              INTEGER NOT NULL,
    block_key               VARCHAR(40) NOT NULL,
    label_vi                VARCHAR(255) NOT NULL,
    plan_section            VARCHAR(20) NOT NULL,
    movement_role           VARCHAR(20),
    count_min               SMALLINT NOT NULL DEFAULT 0,
    count_max               SMALLINT NOT NULL DEFAULT 0,
    duration_min_minutes    SMALLINT,
    duration_max_minutes    SMALLINT,
    is_optional             BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (experience_level, block_key)
);

CREATE INDEX IF NOT EXISTS idx_sbt_level_sort
    ON session_block_templates(experience_level, sort_order);
