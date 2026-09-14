-- Add exercise section (warmup | main | cooldown) for daily plan UI grouping
ALTER TABLE user_daily_plan_exercises
    ADD COLUMN IF NOT EXISTS section VARCHAR(20) NOT NULL DEFAULT 'main';

CREATE INDEX IF NOT EXISTS idx_user_daily_plan_exercises_section
    ON user_daily_plan_exercises(plan_day_id, section, sort_order);
