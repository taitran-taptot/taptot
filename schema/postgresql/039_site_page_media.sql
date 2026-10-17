CREATE TABLE IF NOT EXISTS site_page_media (
    id INT PRIMARY KEY,
    home_challenge_youtube_id TEXT NOT NULL DEFAULT 'EngW7tLk6R8',
    shop_guide_youtube_id TEXT NOT NULL DEFAULT 'EngW7tLk6R8',
    service_lo_trinh_image_url TEXT,
    service_dung_cu_image_url TEXT,
    service_hlv_image_url TEXT,
    about_hero_image_url TEXT,
    about_founder_image_url TEXT,
    about_trainer_image_url TEXT,
    contact_trainer_image_url TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO site_page_media (id)
VALUES (1)
ON CONFLICT (id) DO NOTHING;
