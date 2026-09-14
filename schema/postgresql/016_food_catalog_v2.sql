-- Food catalog v2: explicit kind, per-100g truth, portions, soft status

ALTER TABLE foods ADD COLUMN IF NOT EXISTS food_kind VARCHAR(20) NOT NULL DEFAULT 'ingredient';
ALTER TABLE foods ADD COLUMN IF NOT EXISTS prep_state VARCHAR(10);
ALTER TABLE foods ADD COLUMN IF NOT EXISTS status VARCHAR(12) NOT NULL DEFAULT 'active';
ALTER TABLE foods ADD COLUMN IF NOT EXISTS merged_into_id INT REFERENCES foods(id);
ALTER TABLE foods ADD COLUMN IF NOT EXISTS kcal_100g DECIMAL(7, 2);
ALTER TABLE foods ADD COLUMN IF NOT EXISTS protein_100g DECIMAL(6, 2);
ALTER TABLE foods ADD COLUMN IF NOT EXISTS carbs_100g DECIMAL(6, 2);
ALTER TABLE foods ADD COLUMN IF NOT EXISTS fat_100g DECIMAL(6, 2);
ALTER TABLE foods ADD COLUMN IF NOT EXISTS fiber_100g DECIMAL(6, 2);
ALTER TABLE foods ADD COLUMN IF NOT EXISTS sugar_100g DECIMAL(6, 2);
ALTER TABLE foods ADD COLUMN IF NOT EXISTS sodium_100mg DECIMAL(8, 2);
ALTER TABLE foods ADD COLUMN IF NOT EXISTS alcohol_100g DECIMAL(5, 2);
ALTER TABLE foods ADD COLUMN IF NOT EXISTS source_ref VARCHAR(120);
ALTER TABLE foods ADD COLUMN IF NOT EXISTS confidence VARCHAR(10) NOT NULL DEFAULT 'estimated';
ALTER TABLE foods ADD COLUMN IF NOT EXISTS yield_factor DECIMAL(4, 2);
ALTER TABLE foods ADD COLUMN IF NOT EXISTS density_g_per_ml DECIMAL(5, 3);

CREATE INDEX IF NOT EXISTS idx_foods_kind ON foods(food_kind);
CREATE INDEX IF NOT EXISTS idx_foods_status ON foods(status);
CREATE INDEX IF NOT EXISTS idx_foods_prep_state ON foods(prep_state);

CREATE TABLE IF NOT EXISTS food_portions (
    id          SERIAL PRIMARY KEY,
    food_id     INT NOT NULL REFERENCES foods(id) ON DELETE CASCADE,
    label_vi    VARCHAR(60) NOT NULL,
    grams       DECIMAL(7, 2) NOT NULL,
    is_default  BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order  INT NOT NULL DEFAULT 0,
    UNIQUE (food_id, label_vi)
);

CREATE INDEX IF NOT EXISTS idx_food_portions_food ON food_portions(food_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_food_default_portion
    ON food_portions(food_id) WHERE is_default = TRUE;

ALTER TABLE meal_plan_items ADD COLUMN IF NOT EXISTS grams DECIMAL(7, 2);
ALTER TABLE meal_plan_items ADD COLUMN IF NOT EXISTS portion_id INT REFERENCES food_portions(id);
ALTER TABLE user_daily_plan_meals ADD COLUMN IF NOT EXISTS grams DECIMAL(7, 2);
ALTER TABLE user_daily_plan_meals ADD COLUMN IF NOT EXISTS portion_id INT REFERENCES food_portions(id);
