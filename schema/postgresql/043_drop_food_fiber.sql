-- Drop dietary fiber; carbs are total carbohydrate with no fiber math.

ALTER TABLE foods DROP COLUMN IF EXISTS fiber_g;
ALTER TABLE foods DROP COLUMN IF EXISTS fiber_100g;
