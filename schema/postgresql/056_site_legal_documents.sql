CREATE TABLE IF NOT EXISTS site_legal_documents (
    slug TEXT PRIMARY KEY,
    body TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
