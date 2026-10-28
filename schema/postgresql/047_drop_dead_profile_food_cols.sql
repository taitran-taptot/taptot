-- Drop ORM-unmapped leftover profile/food/meal/001 columns. Safe to re-run.
-- Does not touch venue, specs_vi, owner_user_id, shop, experience_level, or foods.confidence.

DROP INDEX IF EXISTS idx_foods_province_id;

ALTER TABLE user_profiles DROP COLUMN IF EXISTS tdee;
ALTER TABLE user_profiles DROP COLUMN IF EXISTS target_calories;
ALTER TABLE user_profiles DROP COLUMN IF EXISTS target_protein_g;
ALTER TABLE user_profiles DROP COLUMN IF EXISTS target_carbs_g;
ALTER TABLE user_profiles DROP COLUMN IF EXISTS target_fat_g;
ALTER TABLE user_profiles DROP COLUMN IF EXISTS gender;
ALTER TABLE user_profiles DROP COLUMN IF EXISTS height_cm;
ALTER TABLE user_profiles DROP COLUMN IF EXISTS weight_kg;
ALTER TABLE user_profiles DROP COLUMN IF EXISTS goal;

ALTER TABLE foods DROP COLUMN IF EXISTS merged_into_id;
ALTER TABLE foods DROP COLUMN IF EXISTS province_id;

ALTER TABLE meal_plan_items DROP COLUMN IF EXISTS grams;
ALTER TABLE meal_plan_items DROP COLUMN IF EXISTS portion_id;
ALTER TABLE user_daily_plan_meals DROP COLUMN IF EXISTS grams;
ALTER TABLE user_daily_plan_meals DROP COLUMN IF EXISTS portion_id;

ALTER TABLE exercises DROP COLUMN IF EXISTS target_muscle;
ALTER TABLE exercises DROP COLUMN IF EXISTS muscle_group;
