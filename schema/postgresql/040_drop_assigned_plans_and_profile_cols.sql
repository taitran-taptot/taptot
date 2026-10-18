-- Drop unused trainer_assigned_plans and deprecated user_profiles columns.
-- Safe to re-run. Existing DBs only. Fresh 001/002 no longer create these.

DROP TABLE IF EXISTS trainer_assigned_plans CASCADE;

ALTER TABLE user_profiles DROP COLUMN IF EXISTS birth_year;
ALTER TABLE user_profiles DROP COLUMN IF EXISTS activity_level;
ALTER TABLE user_profiles DROP COLUMN IF EXISTS target_weight_kg;
ALTER TABLE user_profiles DROP COLUMN IF EXISTS training_location;
ALTER TABLE user_profiles DROP COLUMN IF EXISTS available_equipment;
