-- One promo code per collaborator. Order snapshot columns are added
-- idempotently by ensure_collaborator_promo:
--   shop_orders.promo_code, promo_owner_user_id, promo_percent, promo_discount_vnd

CREATE TABLE IF NOT EXISTS collaborator_promos (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    code TEXT,
    discount_percent INTEGER NOT NULL DEFAULT 10,
    created_at TEXT NOT NULL,
    code_created_at TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_collaborator_promos_code
    ON collaborator_promos (code);
