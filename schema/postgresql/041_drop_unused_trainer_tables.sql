-- Irreversible: drop unused HLV tables (data included). Safe to re-run.

DROP TABLE IF EXISTS trainer_credentials CASCADE;
DROP TABLE IF EXISTS trainer_clients CASCADE;
DROP TABLE IF EXISTS trainer_profiles CASCADE;
DROP TABLE IF EXISTS trainer_assigned_plans CASCADE;
