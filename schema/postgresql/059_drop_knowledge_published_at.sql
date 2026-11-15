-- Knowledge visibility is is_published. published_at was stored and never shown.

ALTER TABLE knowledge_articles DROP COLUMN IF EXISTS published_at;
