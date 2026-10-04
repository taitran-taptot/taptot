-- SQLite: add nullable FKs. created_by nullability is applied via ORM on new DBs.
ALTER TABLE product_redeem_codes ADD COLUMN order_id INTEGER REFERENCES shop_orders(id) ON DELETE SET NULL;
ALTER TABLE product_redeem_codes ADD COLUMN order_item_id INTEGER REFERENCES shop_order_items(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_product_redeem_codes_order
    ON product_redeem_codes(order_id, id);
