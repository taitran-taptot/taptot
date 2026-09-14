-- Exercise movement_role: compound | isolation | mobility | cardio
-- Applied via ensure_exercise_movement_role at startup if missing.

ALTER TABLE exercises ADD COLUMN movement_role TEXT;
CREATE INDEX IF NOT EXISTS idx_exercises_movement_role ON exercises(movement_role);
