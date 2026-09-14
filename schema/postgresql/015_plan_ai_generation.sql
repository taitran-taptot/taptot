-- Link daily plans back to the AI generation that created them
ALTER TABLE user_daily_plans ADD COLUMN IF NOT EXISTS ai_generation_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_user_daily_plans_ai_generation
  ON user_daily_plans(ai_generation_id);
