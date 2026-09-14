-- Restore exercises.secondary_muscles (JSON list of secondary muscle labels)
-- Applied via ensure_exercise_secondary_muscles at startup if missing.

ALTER TABLE exercises ADD COLUMN secondary_muscles TEXT NOT NULL DEFAULT '[]';
