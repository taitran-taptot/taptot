-- Public share link + allow guest plans (nullable user_id)

ALTER TABLE user_daily_plans
    ADD COLUMN IF NOT EXISTS share_token VARCHAR(64);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_daily_plans_share_token
    ON user_daily_plans(share_token);

ALTER TABLE user_daily_plans
    ALTER COLUMN user_id DROP NOT NULL;
