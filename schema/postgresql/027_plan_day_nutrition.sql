-- Per-day nutrition targets on plan days (training days in weekly template)
ALTER TABLE user_daily_plan_days ADD COLUMN IF NOT EXISTS target_calories INTEGER;
ALTER TABLE user_daily_plan_days ADD COLUMN IF NOT EXISTS target_protein_g DOUBLE PRECISION;
ALTER TABLE user_daily_plan_days ADD COLUMN IF NOT EXISTS target_carbs_g DOUBLE PRECISION;
ALTER TABLE user_daily_plan_days ADD COLUMN IF NOT EXISTS target_fat_g DOUBLE PRECISION;
