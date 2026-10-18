-- Drop dietary fiber; carbs are total carbohydrate with no fiber math.

ALTER TABLE foods DROP COLUMN fiber_g;
ALTER TABLE foods DROP COLUMN fiber_100g;
