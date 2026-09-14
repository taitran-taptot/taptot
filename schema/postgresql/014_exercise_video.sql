-- Exercise instructional video URL (YouTube or direct MP4)
ALTER TABLE exercises ADD COLUMN IF NOT EXISTS video_url TEXT;
