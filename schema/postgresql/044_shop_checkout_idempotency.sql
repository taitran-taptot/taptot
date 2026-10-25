CREATE TABLE IF NOT EXISTS shop_checkout_requests (
    actor_scope VARCHAR(80) NOT NULL,
    key_hash CHAR(64) NOT NULL,
    request_fingerprint CHAR(64) NOT NULL,
    order_id BIGINT UNIQUE REFERENCES shop_orders(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (actor_scope, key_hash)
);

CREATE INDEX IF NOT EXISTS idx_shop_checkout_requests_created_at
    ON shop_checkout_requests (created_at);
