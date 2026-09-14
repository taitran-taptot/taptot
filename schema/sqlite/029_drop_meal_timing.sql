-- Drop meal timing (user arranges workout time outside the app).
ALTER TABLE user_daily_plan_meals DROP COLUMN IF EXISTS timing;
ALTER TABLE meal_plan_items DROP COLUMN IF EXISTS timing;
