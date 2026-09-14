-- Phase 3 polish: custom foods, meal timing (SQLite)

ALTER TABLE foods ADD COLUMN owner_user_id TEXT REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE user_daily_plan_meals ADD COLUMN timing TEXT NOT NULL DEFAULT 'any';

ALTER TABLE meal_plan_items ADD COLUMN timing TEXT NOT NULL DEFAULT 'any';

CREATE INDEX IF NOT EXISTS idx_foods_owner_user ON foods(owner_user_id);
