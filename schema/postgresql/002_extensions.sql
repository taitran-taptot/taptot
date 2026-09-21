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
    reps            VARCHAR(50),
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

CREATE TABLE user_ai_usage (
    id                  SERIAL PRIMARY KEY,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    usage_month         VARCHAR(7) NOT NULL,
    generation_count    INT NOT NULL DEFAULT 0,
    qa_message_count    INT NOT NULL DEFAULT 0,
    tokens_used         INT NOT NULL DEFAULT 0,
    UNIQUE (user_id, usage_month)
);

-- ============================================================
-- PAYMENTS
-- ============================================================

CREATE TABLE payment_transactions (
    id                  SERIAL PRIMARY KEY,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subscription_id     INT REFERENCES subscriptions(id),
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

-- ============================================================
-- TRAINER / PT MODULE
-- ============================================================

CREATE TABLE trainer_profiles (
    id              SERIAL PRIMARY KEY,
    user_id         UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    business_name   VARCHAR(255),
    bio_vi          TEXT,
    gym_name        VARCHAR(255),
    logo_url        VARCHAR(500),
    brand_color     VARCHAR(20) DEFAULT '#22c55e',
    is_verified     BOOLEAN NOT NULL DEFAULT FALSE,
    max_clients     INT NOT NULL DEFAULT 50,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    full_name       TEXT,
    age             INTEGER,
    years_experience INTEGER,
    share_token     VARCHAR(64) UNIQUE
);

CREATE TABLE trainer_credentials (
    id              SERIAL PRIMARY KEY,
    trainer_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind            VARCHAR(20) NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT,
    image_urls      JSONB NOT NULL DEFAULT '[]',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_trainer_credentials_trainer ON trainer_credentials(trainer_id);

CREATE TABLE trainer_clients (
    id              SERIAL PRIMARY KEY,
    trainer_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    client_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status          VARCHAR(20) NOT NULL DEFAULT 'active',
    started_at      DATE NOT NULL DEFAULT CURRENT_DATE,
    ended_at        DATE,
    full_name       TEXT,
    goal            TEXT,
    gender          TEXT,
    age             INTEGER,
    height_cm       DECIMAL(6, 2),
    weight_kg       DECIMAL(6, 2),
    UNIQUE (trainer_id, client_id)
);

CREATE TABLE trainer_assigned_plans (
    id                  SERIAL PRIMARY KEY,
    trainer_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    client_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    daily_plan_id       INT REFERENCES user_daily_plans(id) ON DELETE SET NULL,
    title_vi            VARCHAR(255) NOT NULL,
    notes_vi            TEXT,
    assigned_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status              VARCHAR(20) NOT NULL DEFAULT 'active'
);
