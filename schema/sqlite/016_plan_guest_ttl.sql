-- Guest plans expire 100 days after create (110 if 100-day challenge).
ALTER TABLE user_daily_plans ADD COLUMN challenge_100_days INTEGER NOT NULL DEFAULT 0;
