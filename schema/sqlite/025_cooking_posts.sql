CREATE TABLE IF NOT EXISTS cooking_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    title_vi TEXT NOT NULL,
    excerpt TEXT,
    content_md TEXT NOT NULL,
    cover_image_url TEXT,
    is_published INTEGER NOT NULL DEFAULT 0,
    published_at TEXT,
    author_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cooking_posts_published
    ON cooking_posts(is_published, published_at DESC, id DESC);
