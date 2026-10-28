-- Drop ORM-unmapped leftover columns. Safe to re-run.
-- Does not touch venue, specs_vi, owner_user_id, or shop columns.

DROP INDEX IF EXISTS idx_exercises_body_part;
DROP INDEX IF EXISTS idx_exercises_equipment;
DROP INDEX IF EXISTS idx_exercises_beginner;

ALTER TABLE meal_plans DROP COLUMN IF EXISTS target_date;
ALTER TABLE exports DROP COLUMN IF EXISTS template_id;

ALTER TABLE exercises DROP COLUMN IF EXISTS body_part;
ALTER TABLE exercises DROP COLUMN IF EXISTS equipment;
ALTER TABLE exercises DROP COLUMN IF EXISTS is_beginner_friendly;
ALTER TABLE exercises DROP COLUMN IF EXISTS media_id;
ALTER TABLE exercises DROP COLUMN IF EXISTS attribution;
ALTER TABLE exercises DROP COLUMN IF EXISTS instruction_en;
ALTER TABLE exercises DROP COLUMN IF EXISTS instruction_steps_en;
