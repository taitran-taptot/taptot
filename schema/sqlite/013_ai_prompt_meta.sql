-- AI prompt metadata on ai_generations (SQLite)

ALTER TABLE ai_generations ADD COLUMN prompt_version TEXT;
ALTER TABLE ai_generations ADD COLUMN system_prompt_hash TEXT;
