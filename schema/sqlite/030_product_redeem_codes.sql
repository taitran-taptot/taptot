CREATE TABLE IF NOT EXISTS product_redeem_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER REFERENCES shop_products(id) ON DELETE SET NULL,
    qty INTEGER NOT NULL CHECK (qty > 0),
    note TEXT,
    created_by TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_product_redeem_batches_product
    ON product_redeem_batches(product_id, id DESC);

CREATE TABLE IF NOT EXISTS product_redeem_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL REFERENCES product_redeem_batches(id) ON DELETE CASCADE,
    code TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'unused'
        CHECK (status IN ('unused', 'redeemed', 'void')),
    reservation_token TEXT,
    reserved_at TEXT,
    redeemed_at TEXT,
    plan_id INTEGER REFERENCES user_daily_plans(id) ON DELETE SET NULL,
    redeemed_user_id TEXT REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_product_redeem_codes_batch
    ON product_redeem_codes(batch_id, id);
CREATE INDEX IF NOT EXISTS idx_product_redeem_codes_status
    ON product_redeem_codes(status, id);
