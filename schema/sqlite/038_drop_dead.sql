-- Drop unused tables/columns (SQLite). Safe to re-run.
PRAGMA foreign_keys = OFF;

DROP TABLE IF EXISTS subscriptions;
DROP TABLE IF EXISTS subscription_plans;
DROP TABLE IF EXISTS workout_sessions;
DROP TABLE IF EXISTS calculator_logs;
DROP TABLE IF EXISTS ai_qa_messages;
DROP TABLE IF EXISTS user_ai_usage;
DROP TABLE IF EXISTS pushup_challenge_entries;

PRAGMA foreign_keys = ON;
