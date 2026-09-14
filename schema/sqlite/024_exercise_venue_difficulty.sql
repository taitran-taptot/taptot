-- exercises.venue: gym | home | both
-- Applied via ensure_exercise_venue_and_difficulty_v2 at startup if missing.

ALTER TABLE exercises ADD COLUMN venue TEXT;
CREATE INDEX IF NOT EXISTS idx_exercises_venue ON exercises(venue);
