-- Link daily plans back to the AI generation that created them
-- SQLite: also applied via ensure_plan_ai_generation_column at startup if missing.
ALTER TABLE user_daily_plans ADD COLUMN ai_generation_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_user_daily_plans_ai_generation
  ON user_daily_plans(ai_generation_id);
