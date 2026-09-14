-- Add exercise section (warmup | main | cooldown) for daily plan UI grouping
-- SQLite does not support IF NOT EXISTS on ADD COLUMN in older versions; apply once.

ALTER TABLE user_daily_plan_exercises ADD COLUMN section TEXT NOT NULL DEFAULT 'main';

CREATE INDEX IF NOT EXISTS idx_user_daily_plan_exercises_section
    ON user_daily_plan_exercises(plan_day_id, section, sort_order);
