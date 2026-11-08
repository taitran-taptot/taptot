-- Drop write-only columns. Safe to re-run.
-- Keep payment token/expires_at/plan_id, pushup created timestamps, user_id.

ALTER TABLE payment_transactions DROP COLUMN IF EXISTS currency;
ALTER TABLE payment_transactions DROP COLUMN IF EXISTS description;
ALTER TABLE payment_transactions DROP COLUMN IF EXISTS payment_provider;
ALTER TABLE payment_entitlements DROP COLUMN IF EXISTS purpose;
ALTER TABLE pushup_challenge_sessions DROP COLUMN IF EXISTS reps;
