-- Drop unused legacy tables (local cleanup). Safe to re-run.
-- Dependent columns first so remaining tables stay valid.

ALTER TABLE knowledge_articles DROP COLUMN IF EXISTS series_id;
ALTER TABLE workout_sessions DROP COLUMN IF EXISTS program_day_id;
ALTER TABLE workout_sessions DROP COLUMN IF EXISTS enrollment_id;
ALTER TABLE trainer_assigned_plans DROP COLUMN IF EXISTS workout_plan_id;
ALTER TABLE trainer_assigned_plans DROP COLUMN IF EXISTS program_id;

DROP TABLE IF EXISTS workout_session_sets CASCADE;
DROP TABLE IF EXISTS client_notes CASCADE;
DROP TABLE IF EXISTS exercise_equipment_suggestions CASCADE;
DROP TABLE IF EXISTS equipment_products CASCADE;
DROP TABLE IF EXISTS export_templates CASCADE;
DROP TABLE IF EXISTS exercise_localizations CASCADE;
DROP TABLE IF EXISTS body_part_labels CASCADE;
DROP TABLE IF EXISTS equipment_labels CASCADE;
DROP TABLE IF EXISTS muscle_labels CASCADE;
DROP TABLE IF EXISTS workout_schedule_frame_days CASCADE;
DROP TABLE IF EXISTS workout_schedule_frames CASCADE;
DROP TABLE IF EXISTS program_day_exercises CASCADE;
DROP TABLE IF EXISTS program_day_meals CASCADE;
DROP TABLE IF EXISTS user_program_enrollments CASCADE;
DROP TABLE IF EXISTS program_days CASCADE;
DROP TABLE IF EXISTS programs CASCADE;
DROP TABLE IF EXISTS user_workout_plan_exercises CASCADE;
DROP TABLE IF EXISTS user_workout_plans CASCADE;
DROP TABLE IF EXISTS knowledge_series CASCADE;
