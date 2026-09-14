-- exercises.venue: gym | home | both
-- difficulty skill scale 1–4 (clamp any legacy 5 → 4 via ensure_*)
-- Applied via ensure_exercise_venue_and_difficulty_v2 at startup if missing.

ALTER TABLE exercises ADD COLUMN IF NOT EXISTS venue VARCHAR(10);
CREATE INDEX IF NOT EXISTS idx_exercises_venue ON exercises(venue);
