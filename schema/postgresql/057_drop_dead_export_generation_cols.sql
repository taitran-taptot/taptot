-- Unread export history fields and generation columns that were always empty
-- or a single constant. PDF export does not store a row. Restore reads output_data.

ALTER TABLE exports DROP COLUMN IF EXISTS source_id;
ALTER TABLE exports DROP COLUMN IF EXISTS format;
ALTER TABLE exports DROP COLUMN IF EXISTS file_url;

ALTER TABLE ai_generations DROP COLUMN IF EXISTS generation_type;
ALTER TABLE ai_generations DROP COLUMN IF EXISTS input_params;
