-- Per-day nutrition targets on plan days (training days in weekly template)
ALTER TABLE user_daily_plan_days ADD COLUMN target_calories INTEGER;
ALTER TABLE user_daily_plan_days ADD COLUMN target_protein_g REAL;
ALTER TABLE user_daily_plan_days ADD COLUMN target_carbs_g REAL;
ALTER TABLE user_daily_plan_days ADD COLUMN target_fat_g REAL;
