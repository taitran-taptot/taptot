-- Guest checkout + shipping snapshot + payment + public order code

ALTER TABLE shop_orders ALTER COLUMN user_id DROP NOT NULL;

ALTER TABLE shop_orders ADD COLUMN IF NOT EXISTS public_code VARCHAR(32);
ALTER TABLE shop_orders ADD COLUMN IF NOT EXISTS recipient_name VARCHAR(120);
ALTER TABLE shop_orders ADD COLUMN IF NOT EXISTS phone VARCHAR(20);
ALTER TABLE shop_orders ADD COLUMN IF NOT EXISTS province_code VARCHAR(20);
ALTER TABLE shop_orders ADD COLUMN IF NOT EXISTS province_name VARCHAR(120);
ALTER TABLE shop_orders ADD COLUMN IF NOT EXISTS district_code VARCHAR(20);
ALTER TABLE shop_orders ADD COLUMN IF NOT EXISTS district_name VARCHAR(120);
ALTER TABLE shop_orders ADD COLUMN IF NOT EXISTS ward_code VARCHAR(20);
ALTER TABLE shop_orders ADD COLUMN IF NOT EXISTS ward_name VARCHAR(120);
ALTER TABLE shop_orders ADD COLUMN IF NOT EXISTS address_line TEXT;
ALTER TABLE shop_orders ADD COLUMN IF NOT EXISTS payment_method VARCHAR(30);
ALTER TABLE shop_orders ADD COLUMN IF NOT EXISTS payment_status VARCHAR(30);
ALTER TABLE shop_orders ADD COLUMN IF NOT EXISTS shipping_fee_vnd INT NOT NULL DEFAULT 0;

UPDATE shop_orders
SET order_status = 'awaiting_confirm'
WHERE order_status = 'placed';

UPDATE shop_orders
SET payment_method = COALESCE(payment_method, 'cod'),
    payment_status = COALESCE(payment_status, 'cod')
WHERE payment_method IS NULL OR payment_status IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_shop_orders_public_code
    ON shop_orders (public_code)
    WHERE public_code IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_shop_orders_phone_code
    ON shop_orders (phone, public_code);
