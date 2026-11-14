-- Meal templates always stored source = 'manual' and nothing reads the column.

ALTER TABLE meal_plans DROP COLUMN IF EXISTS source;
