-- One cart row per product. Column drops run in ensure_shop_cart_option_key
-- so duplicate lines can be summed before the unique key is tightened.
ALTER TABLE shop_products DROP COLUMN IF EXISTS options_json;
