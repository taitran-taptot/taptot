-- Public share link for daily plans (SQLite)
-- Note: SQLite cannot easily drop NOT NULL on user_id; share_token is the main addition.
-- Guest plans use a dedicated guest user or keep user_id when authenticated.

ALTER TABLE user_daily_plans ADD COLUMN share_token TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_daily_plans_share_token
    ON user_daily_plans(share_token);
