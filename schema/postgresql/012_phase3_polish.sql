-- Phase 3 polish: custom foods, meal timing (PostgreSQL)

ALTER TABLE foods ADD COLUMN IF NOT EXISTS owner_user_id UUID REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE user_daily_plan_meals ADD COLUMN IF NOT EXISTS timing VARCHAR(20) NOT NULL DEFAULT 'any';

ALTER TABLE meal_plan_items ADD COLUMN IF NOT EXISTS timing VARCHAR(20) NOT NULL DEFAULT 'any';

CREATE INDEX IF NOT EXISTS idx_foods_owner_user ON foods(owner_user_id);
