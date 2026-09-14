-- Exercise instructional video URL (YouTube or direct MP4)
-- SQLite: run via ensure_exercise_content_columns at startup if column missing.
ALTER TABLE exercises ADD COLUMN video_url TEXT;
