CREATE TABLE IF NOT EXISTS payment_entitlements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    token           TEXT NOT NULL UNIQUE,
    transaction_id  INTEGER NOT NULL REFERENCES payment_transactions(id) ON DELETE CASCADE,
    purpose         TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    expires_at      TEXT NOT NULL,
    consumed_at     TEXT,
    plan_id         INTEGER REFERENCES user_daily_plans(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_payment_entitlements_transaction
    ON payment_entitlements(transaction_id);
