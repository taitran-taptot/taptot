ALTER TABLE cooking_posts ADD COLUMN IF NOT EXISTS dish_slug VARCHAR(150);
ALTER TABLE cooking_posts ADD COLUMN IF NOT EXISTS servings INT NOT NULL DEFAULT 1;
ALTER TABLE cooking_posts ADD COLUMN IF NOT EXISTS yield_grams DECIMAL(8, 2);
ALTER TABLE cooking_posts ADD COLUMN IF NOT EXISTS ingredients JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS idx_cooking_posts_dish_slug ON cooking_posts(dish_slug);
