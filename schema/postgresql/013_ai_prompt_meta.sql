-- AI prompt metadata on ai_generations (PostgreSQL)

ALTER TABLE ai_generations ADD COLUMN IF NOT EXISTS prompt_version TEXT;
ALTER TABLE ai_generations ADD COLUMN IF NOT EXISTS system_prompt_hash TEXT;
