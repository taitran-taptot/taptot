-- SQLite: columns added via ensure_shop_checkout (ALTER ADD COLUMN).
-- Kept for documentation / fresh applies where possible.

CREATE INDEX IF NOT EXISTS idx_shop_orders_phone_code
    ON shop_orders (phone, public_code);

CREATE UNIQUE INDEX IF NOT EXISTS uq_shop_orders_sepay_transaction_id
    ON shop_orders (sepay_transaction_id)
    WHERE sepay_transaction_id IS NOT NULL;
