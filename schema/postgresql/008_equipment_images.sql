-- Equipment catalog images (relative path under /media)
ALTER TABLE equipment ADD COLUMN IF NOT EXISTS image_url TEXT;
ALTER TABLE equipment ADD COLUMN IF NOT EXISTS image_source TEXT;
ALTER TABLE equipment ADD COLUMN IF NOT EXISTS image_attribution TEXT;
