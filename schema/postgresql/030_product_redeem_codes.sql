CREATE TABLE IF NOT EXISTS product_redeem_batches (
    id SERIAL PRIMARY KEY,
    product_id INT REFERENCES shop_products(id) ON DELETE SET NULL,
    qty INT NOT NULL CHECK (qty > 0),
    note TEXT,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_product_redeem_batches_product
    ON product_redeem_batches(product_id, id DESC);

CREATE TABLE IF NOT EXISTS product_redeem_codes (
    id SERIAL PRIMARY KEY,
    batch_id INT NOT NULL REFERENCES product_redeem_batches(id) ON DELETE CASCADE,
    code VARCHAR(16) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'unused'
        CHECK (status IN ('unused', 'redeemed', 'void')),
    reservation_token VARCHAR(64),
    reserved_at TIMESTAMPTZ,
    redeemed_at TIMESTAMPTZ,
    plan_id INT REFERENCES user_daily_plans(id) ON DELETE SET NULL,
    redeemed_user_id UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_product_redeem_codes_batch
    ON product_redeem_codes(batch_id, id);
CREATE INDEX IF NOT EXISTS idx_product_redeem_codes_status
    ON product_redeem_codes(status, id);
