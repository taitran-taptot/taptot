-- Plan macro targets + meal template notes (SQLite)

ALTER TABLE user_daily_plans ADD COLUMN target_protein_g REAL;
ALTER TABLE user_daily_plans ADD COLUMN target_carbs_g REAL;
ALTER TABLE user_daily_plans ADD COLUMN target_fat_g REAL;

-- Slot notes for meal templates (breakfast/lunch/dinner/snack_N)
ALTER TABLE meal_plans ADD COLUMN meal_notes_json TEXT NOT NULL DEFAULT '{}';

ALTER TABLE meal_plan_items ADD COLUMN notes_vi TEXT;
