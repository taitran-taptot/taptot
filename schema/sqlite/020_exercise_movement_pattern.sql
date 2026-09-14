-- Exercise movement_pattern: h_push | h_pull | v_push | v_pull | squat | hinge | core | other
-- Applied via ensure_exercise_movement_pattern at startup if missing.

ALTER TABLE exercises ADD COLUMN movement_pattern TEXT;
CREATE INDEX IF NOT EXISTS idx_exercises_movement_pattern ON exercises(movement_pattern);
