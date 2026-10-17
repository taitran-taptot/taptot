-- Equipment catalog images (relative path under /media)
ALTER TABLE equipment ADD COLUMN IF NOT EXISTS image_url TEXT;
