CREATE TABLE IF NOT EXISTS shop_finance_settings (
    id INTEGER PRIMARY KEY,
    marketing_vnd INTEGER NOT NULL DEFAULT 0
);

INSERT INTO shop_finance_settings (id, marketing_vnd)
SELECT 1, 0
WHERE NOT EXISTS (SELECT 1 FROM shop_finance_settings WHERE id = 1);
