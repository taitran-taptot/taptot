ALTER TABLE cooking_posts ADD COLUMN dish_slug TEXT;
ALTER TABLE cooking_posts ADD COLUMN servings INTEGER NOT NULL DEFAULT 1;
ALTER TABLE cooking_posts ADD COLUMN yield_grams REAL;
ALTER TABLE cooking_posts ADD COLUMN ingredients TEXT NOT NULL DEFAULT '[]';

CREATE INDEX IF NOT EXISTS idx_cooking_posts_dish_slug ON cooking_posts(dish_slug);
