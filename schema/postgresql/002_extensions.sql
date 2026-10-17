-- TAPTOT schema extensions: PT module, combined plans, payments, search

-- ============================================================
-- FOOD ALIASES
-- ============================================================

CREATE TABLE food_aliases (
    id          SERIAL PRIMARY KEY,
    food_id     INT NOT NULL REFERENCES foods(id) ON DELETE CASCADE,
    alias       VARCHAR(255) NOT NULL,
    UNIQUE (food_id, alias)
);

CREATE INDEX idx_food_aliases_alias ON food_aliases(alias);

-- ============================================================
-- COMBINED DAILY PLANS
-- ============================================================

CREATE TABLE user_daily_plans (
    id              SERIAL PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title_vi        VARCHAR(255) NOT NULL,
    description_vi  TEXT,
    start_date      DATE,
    end_date        DATE,
    target_calories INT,
    source          VARCHAR(20) NOT NULL DEFAULT 'manual',
    is_template     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE user_daily_plan_days (
    id              SERIAL PRIMARY KEY,
    plan_id         INT NOT NULL REFERENCES user_daily_plans(id) ON DELETE CASCADE,
    day_number      INT NOT NULL,
    title_vi        VARCHAR(255),
    notes_vi        TEXT,
    UNIQUE (plan_id, day_number)
);

CREATE TABLE user_daily_plan_exercises (
    id              SERIAL PRIMARY KEY,
    plan_day_id     INT NOT NULL REFERENCES user_daily_plan_days(id) ON DELETE CASCADE,
    exercise_id     VARCHAR(4) NOT NULL REFERENCES exercises(id),
    sort_order      INT NOT NULL,
    sets            INT NOT NULL,
    reps            TEXT,
    rest_seconds    INT NOT NULL DEFAULT 60,
    notes_vi        TEXT
);

CREATE TABLE user_daily_plan_meals (
    id              SERIAL PRIMARY KEY,
    plan_day_id     INT NOT NULL REFERENCES user_daily_plan_days(id) ON DELETE CASCADE,
    meal_type       VARCHAR(20) NOT NULL,
    food_id         INT NOT NULL REFERENCES foods(id),
    servings        DECIMAL(4, 2) NOT NULL DEFAULT 1,
    sort_order      INT NOT NULL DEFAULT 0,
    notes_vi        TEXT
);

-- ============================================================
-- AUTH & AI QUOTA
-- ============================================================

CREATE TABLE auth_sessions (
    id              SERIAL PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash      VARCHAR(255) NOT NULL UNIQUE,
    expires_at      TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at      TIMESTAMPTZ
);

-- ============================================================
-- PAYMENTS
-- ============================================================

CREATE TABLE payment_transactions (
    id                  SERIAL PRIMARY KEY,
    user_id             UUID REFERENCES users(id) ON DELETE CASCADE,
    amount_vnd          INT NOT NULL,
    currency            VARCHAR(3) NOT NULL DEFAULT 'VND',
    status              VARCHAR(20) NOT NULL,
    payment_provider    VARCHAR(30) NOT NULL,
    external_id         VARCHAR(255),
    description         TEXT,
    metadata            JSONB NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ
);

CREATE INDEX idx_payment_transactions_user ON payment_transactions(user_id);
