-- Drop unused legacy tables (SQLite). Safe to re-run.
PRAGMA foreign_keys = OFF;

DROP TABLE IF EXISTS workout_session_sets;
DROP TABLE IF EXISTS client_notes;
DROP TABLE IF EXISTS exercise_equipment_suggestions;
DROP TABLE IF EXISTS equipment_products;
DROP TABLE IF EXISTS export_templates;
DROP TABLE IF EXISTS exercise_localizations;
DROP TABLE IF EXISTS body_part_labels;
DROP TABLE IF EXISTS equipment_labels;
DROP TABLE IF EXISTS muscle_labels;
DROP TABLE IF EXISTS workout_schedule_frame_days;
DROP TABLE IF EXISTS workout_schedule_frames;
DROP TABLE IF EXISTS program_day_exercises;
DROP TABLE IF EXISTS program_day_meals;
DROP TABLE IF EXISTS user_program_enrollments;
DROP TABLE IF EXISTS program_days;
DROP TABLE IF EXISTS programs;
DROP TABLE IF EXISTS user_workout_plan_exercises;
DROP TABLE IF EXISTS user_workout_plans;
DROP TABLE IF EXISTS knowledge_series;

PRAGMA foreign_keys = ON;
