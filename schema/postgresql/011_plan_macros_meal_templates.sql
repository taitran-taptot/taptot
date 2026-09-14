-- Plan macro targets + meal template notes (PostgreSQL)

ALTER TABLE user_daily_plans ADD COLUMN IF NOT EXISTS target_protein_g REAL;
ALTER TABLE user_daily_plans ADD COLUMN IF NOT EXISTS target_carbs_g REAL;
ALTER TABLE user_daily_plans ADD COLUMN IF NOT EXISTS target_fat_g REAL;

ALTER TABLE meal_plans ADD COLUMN IF NOT EXISTS meal_notes_json JSONB NOT NULL DEFAULT '{}';

ALTER TABLE meal_plan_items ADD COLUMN IF NOT EXISTS notes_vi TEXT;
