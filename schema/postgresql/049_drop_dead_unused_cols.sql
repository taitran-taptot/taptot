-- Drop unused leftover columns/tables. Safe to re-run.
-- Keep foods.confidence, shop_orders.district_name, shipping_fee_vnd.

ALTER TABLE foods DROP COLUMN IF EXISTS is_verified;
ALTER TABLE shop_orders DROP COLUMN IF EXISTS district_code;
ALTER TABLE pushup_challenge_sessions DROP COLUMN IF EXISTS ip;

DROP TABLE IF EXISTS user_checkins;
DROP TABLE IF EXISTS user_streaks;
