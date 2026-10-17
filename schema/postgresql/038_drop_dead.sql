-- Drop unused tables/columns. Safe to re-run.

ALTER TABLE payment_transactions DROP COLUMN IF EXISTS subscription_id;

DROP TABLE IF EXISTS subscriptions CASCADE;
DROP TABLE IF EXISTS subscription_plans CASCADE;
DROP TABLE IF EXISTS workout_sessions CASCADE;
DROP TABLE IF EXISTS calculator_logs CASCADE;
DROP TABLE IF EXISTS ai_qa_messages CASCADE;
DROP TABLE IF EXISTS user_ai_usage CASCADE;
DROP TABLE IF EXISTS pushup_challenge_entries CASCADE;

ALTER TABLE ai_generations DROP COLUMN IF EXISTS tokens_used;
ALTER TABLE ai_generations DROP COLUMN IF EXISTS cost_usd;
ALTER TABLE ai_generations DROP COLUMN IF EXISTS is_paid;
ALTER TABLE ai_generations DROP COLUMN IF EXISTS prompt_version;
ALTER TABLE ai_generations DROP COLUMN IF EXISTS system_prompt_hash;

ALTER TABLE foods DROP COLUMN IF EXISTS vitamins_json;
ALTER TABLE foods DROP COLUMN IF EXISTS alcohol_100g;
ALTER TABLE foods DROP COLUMN IF EXISTS yield_factor;

ALTER TABLE equipment DROP COLUMN IF EXISTS image_source;
ALTER TABLE equipment DROP COLUMN IF EXISTS image_attribution;
