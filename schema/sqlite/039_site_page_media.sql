CREATE TABLE IF NOT EXISTS site_page_media (
    id INTEGER PRIMARY KEY,
    home_challenge_youtube_id TEXT NOT NULL DEFAULT 'EngW7tLk6R8',
    shop_guide_youtube_id TEXT NOT NULL DEFAULT 'EngW7tLk6R8',
    service_lo_trinh_image_url TEXT,
    service_dung_cu_image_url TEXT,
    service_hlv_image_url TEXT,
    about_hero_image_url TEXT,
    about_founder_image_url TEXT,
    about_trainer_image_url TEXT,
    contact_trainer_image_url TEXT,
    success_1_image_url TEXT,
    success_1_name TEXT,
    success_1_result TEXT,
    success_1_quote TEXT,
    success_2_image_url TEXT,
    success_2_name TEXT,
    success_2_result TEXT,
    success_2_quote TEXT,
    success_stories TEXT,
    success_stories_visible TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO site_page_media (id) VALUES (1);
