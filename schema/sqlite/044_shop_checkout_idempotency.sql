CREATE TABLE IF NOT EXISTS shop_checkout_requests (
    actor_scope TEXT NOT NULL,
    key_hash TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    order_id INTEGER UNIQUE REFERENCES shop_orders(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    PRIMARY KEY (actor_scope, key_hash)
);

CREATE INDEX IF NOT EXISTS idx_shop_checkout_requests_created_at
    ON shop_checkout_requests (created_at);
