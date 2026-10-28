-- One promo code per collaborator. Order snapshot columns are added
-- idempotently by ensure_collaborator_promo:
--   shop_orders.promo_code, promo_owner_user_id, promo_percent, promo_discount_vnd

CREATE TABLE IF NOT EXISTS collaborator_promos (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    code VARCHAR(32),
    discount_percent INT NOT NULL DEFAULT 10,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    code_created_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_collaborator_promos_code
    ON collaborator_promos (code);
