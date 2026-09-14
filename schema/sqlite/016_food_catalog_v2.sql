-- Food catalog v2: explicit kind, per-100g truth, portions, soft status

ALTER TABLE foods ADD COLUMN food_kind TEXT NOT NULL DEFAULT 'ingredient';
ALTER TABLE foods ADD COLUMN prep_state TEXT;
ALTER TABLE foods ADD COLUMN status TEXT NOT NULL DEFAULT 'active';
ALTER TABLE foods ADD COLUMN merged_into_id INTEGER REFERENCES foods(id);
ALTER TABLE foods ADD COLUMN kcal_100g REAL;
ALTER TABLE foods ADD COLUMN protein_100g REAL;
ALTER TABLE foods ADD COLUMN carbs_100g REAL;
ALTER TABLE foods ADD COLUMN fat_100g REAL;
ALTER TABLE foods ADD COLUMN fiber_100g REAL;
ALTER TABLE foods ADD COLUMN sugar_100g REAL;
ALTER TABLE foods ADD COLUMN sodium_100mg REAL;
ALTER TABLE foods ADD COLUMN alcohol_100g REAL;
ALTER TABLE foods ADD COLUMN source_ref TEXT;
ALTER TABLE foods ADD COLUMN confidence TEXT NOT NULL DEFAULT 'estimated';
ALTER TABLE foods ADD COLUMN yield_factor REAL;
ALTER TABLE foods ADD COLUMN density_g_per_ml REAL;

CREATE INDEX IF NOT EXISTS idx_foods_kind ON foods(food_kind);
CREATE INDEX IF NOT EXISTS idx_foods_status ON foods(status);
CREATE INDEX IF NOT EXISTS idx_foods_prep_state ON foods(prep_state);

CREATE TABLE IF NOT EXISTS food_portions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    food_id     INTEGER NOT NULL REFERENCES foods(id) ON DELETE CASCADE,
    label_vi    TEXT NOT NULL,
    grams       REAL NOT NULL,
    is_default  INTEGER NOT NULL DEFAULT 0,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    UNIQUE (food_id, label_vi)
);

CREATE INDEX IF NOT EXISTS idx_food_portions_food ON food_portions(food_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_food_default_portion
    ON food_portions(food_id) WHERE is_default = 1;

ALTER TABLE meal_plan_items ADD COLUMN grams REAL;
ALTER TABLE meal_plan_items ADD COLUMN portion_id INTEGER REFERENCES food_portions(id);
ALTER TABLE user_daily_plan_meals ADD COLUMN grams REAL;
ALTER TABLE user_daily_plan_meals ADD COLUMN portion_id INTEGER REFERENCES food_portions(id);
