CREATE TABLE IF NOT EXISTS cooking_posts (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(150) UNIQUE NOT NULL,
    title_vi VARCHAR(255) NOT NULL,
    excerpt TEXT,
    content_md TEXT NOT NULL,
    cover_image_url TEXT,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    published_at TIMESTAMPTZ,
    author_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    sort_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cooking_posts_published
    ON cooking_posts(is_published, published_at DESC, id DESC);
