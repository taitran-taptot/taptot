-- Exercise detail content fields (instruction / tips / media)
ALTER TABLE exercises ADD COLUMN IF NOT EXISTS instruction_vi TEXT;
ALTER TABLE exercises ADD COLUMN IF NOT EXISTS instruction_steps_vi JSONB;
ALTER TABLE exercises ADD COLUMN IF NOT EXISTS common_mistakes_vi TEXT;
ALTER TABLE exercises ADD COLUMN IF NOT EXISTS tips_vi TEXT;
ALTER TABLE exercises ADD COLUMN IF NOT EXISTS gif_url TEXT;
ALTER TABLE exercises ADD COLUMN IF NOT EXISTS image_url TEXT;
