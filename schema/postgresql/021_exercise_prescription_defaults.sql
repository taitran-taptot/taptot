-- Default sets/reps by experience_level × movement_role (compound | isolation)
-- Applied via ensure_exercise_prescription_defaults at startup.

CREATE TABLE IF NOT EXISTS exercise_prescription_defaults (
    id                  SERIAL PRIMARY KEY,
    experience_level    SMALLINT NOT NULL CHECK (experience_level BETWEEN 1 AND 5),
    movement_role       VARCHAR(20) NOT NULL,
    default_sets        SMALLINT NOT NULL CHECK (default_sets > 0),
    default_reps        SMALLINT NOT NULL CHECK (default_reps > 0),
    UNIQUE (experience_level, movement_role)
);

CREATE INDEX IF NOT EXISTS idx_epd_level_role
    ON exercise_prescription_defaults(experience_level, movement_role);
