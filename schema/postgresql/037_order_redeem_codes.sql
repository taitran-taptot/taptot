ALTER TABLE product_redeem_batches
    ALTER COLUMN created_by DROP NOT NULL;

ALTER TABLE product_redeem_codes
    ADD COLUMN IF NOT EXISTS order_id INT REFERENCES shop_orders(id) ON DELETE SET NULL;

ALTER TABLE product_redeem_codes
    ADD COLUMN IF NOT EXISTS order_item_id INT REFERENCES shop_order_items(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_product_redeem_codes_order
    ON product_redeem_codes(order_id, id);
