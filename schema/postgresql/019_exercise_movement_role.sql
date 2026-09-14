-- Exercise movement_role: compound | isolation | mobility | cardio
-- Applied via ensure_exercise_movement_role at startup if missing.

ALTER TABLE exercises ADD COLUMN IF NOT EXISTS movement_role VARCHAR(20);
CREATE INDEX IF NOT EXISTS idx_exercises_movement_role ON exercises(movement_role);
