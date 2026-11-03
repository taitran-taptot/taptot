-- Drop unused two-slot success story columns. Safe to re-run.
-- Live copy lives in success_stories JSON.

ALTER TABLE site_page_media DROP COLUMN IF EXISTS success_1_image_url;
ALTER TABLE site_page_media DROP COLUMN IF EXISTS success_1_name;
ALTER TABLE site_page_media DROP COLUMN IF EXISTS success_1_result;
ALTER TABLE site_page_media DROP COLUMN IF EXISTS success_1_quote;
ALTER TABLE site_page_media DROP COLUMN IF EXISTS success_2_image_url;
ALTER TABLE site_page_media DROP COLUMN IF EXISTS success_2_name;
ALTER TABLE site_page_media DROP COLUMN IF EXISTS success_2_result;
ALTER TABLE site_page_media DROP COLUMN IF EXISTS success_2_quote;
