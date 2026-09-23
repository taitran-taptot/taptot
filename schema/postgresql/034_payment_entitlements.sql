CREATE TABLE IF NOT EXISTS payment_entitlements (
    id              SERIAL PRIMARY KEY,
    token           TEXT NOT NULL UNIQUE,
    transaction_id  INT NOT NULL REFERENCES payment_transactions(id) ON DELETE CASCADE,
    purpose         TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL,
    consumed_at     TIMESTAMPTZ,
    plan_id         INT REFERENCES user_daily_plans(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_payment_entitlements_transaction
    ON payment_entitlements(transaction_id);
