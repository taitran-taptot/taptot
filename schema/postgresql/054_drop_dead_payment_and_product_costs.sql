-- Challenge checkout and product-level cost columns are unused.
-- Month costs stay on shop_month_costs / shop_month_product_costs.

DROP TABLE IF EXISTS payment_entitlements;
DROP TABLE IF EXISTS payment_transactions;
DROP TABLE IF EXISTS shop_finance_settings;

ALTER TABLE shop_products DROP COLUMN IF EXISTS cost_vnd;
ALTER TABLE shop_products DROP COLUMN IF EXISTS marketing_vnd;
