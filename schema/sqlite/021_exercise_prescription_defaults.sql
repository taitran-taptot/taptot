-- Default sets/reps by experience_level × movement_role (compound | isolation)
-- Applied via ensure_exercise_prescription_defaults at startup.

CREATE TABLE IF NOT EXISTS exercise_prescription_defaults (
    id                  INTEGER PRIMARY KEY,
    experience_level    INTEGER NOT NULL,
    movement_role       TEXT NOT NULL,
    default_sets        INTEGER NOT NULL,
    default_reps        INTEGER NOT NULL,
    UNIQUE (experience_level, movement_role)
);

CREATE INDEX IF NOT EXISTS idx_epd_level_role
    ON exercise_prescription_defaults(experience_level, movement_role);
