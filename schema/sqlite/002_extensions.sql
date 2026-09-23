-- TAPTOT schema extensions: PT module, combined plans, payments, search

PRAGMA foreign_keys = ON;

-- ============================================================
-- FOOD ALIASES (search VN)
-- ============================================================

CREATE TABLE food_aliases (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    food_id     INTEGER NOT NULL REFERENCES foods(id) ON DELETE CASCADE,
    alias       TEXT NOT NULL,
    UNIQUE (food_id, alias)
);

CREATE INDEX idx_food_aliases_alias ON food_aliases(alias);

-- ============================================================
-- COMBINED DAILY PLANS (workout + meals)
-- ============================================================

CREATE TABLE user_daily_plans (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title_vi        TEXT NOT NULL,
    description_vi  TEXT,
    start_date      TEXT,
    end_date        TEXT,
    target_calories INTEGER,
    source          TEXT NOT NULL DEFAULT 'manual',
    is_template     INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE user_daily_plan_days (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id         INTEGER NOT NULL REFERENCES user_daily_plans(id) ON DELETE CASCADE,
    day_number      INTEGER NOT NULL,
    title_vi        TEXT,
    notes_vi        TEXT,
    UNIQUE (plan_id, day_number)
);

CREATE TABLE user_daily_plan_exercises (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_day_id     INTEGER NOT NULL REFERENCES user_daily_plan_days(id) ON DELETE CASCADE,
    exercise_id     TEXT NOT NULL REFERENCES exercises(id),
    sort_order      INTEGER NOT NULL,
    sets            INTEGER NOT NULL,
    reps            TEXT,
    rest_seconds    INTEGER NOT NULL DEFAULT 60,
    notes_vi        TEXT
);

CREATE TABLE user_daily_plan_meals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_day_id     INTEGER NOT NULL REFERENCES user_daily_plan_days(id) ON DELETE CASCADE,
    meal_type       TEXT NOT NULL,
    food_id         INTEGER NOT NULL REFERENCES foods(id),
    servings        REAL NOT NULL DEFAULT 1,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    notes_vi        TEXT
);

-- ============================================================
-- AUTH & AI QUOTA
-- ============================================================

CREATE TABLE auth_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash      TEXT NOT NULL UNIQUE,
    expires_at      TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    revoked_at      TEXT
);

CREATE TABLE user_ai_usage (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    usage_month         TEXT NOT NULL,
    generation_count    INTEGER NOT NULL DEFAULT 0,
    qa_message_count    INTEGER NOT NULL DEFAULT 0,
    tokens_used         INTEGER NOT NULL DEFAULT 0,
    UNIQUE (user_id, usage_month)
);

-- ============================================================
-- PAYMENTS
-- ============================================================

CREATE TABLE payment_transactions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             TEXT REFERENCES users(id) ON DELETE CASCADE,
    subscription_id     INTEGER REFERENCES subscriptions(id),
    amount_vnd          INTEGER NOT NULL,
    currency            TEXT NOT NULL DEFAULT 'VND',
    status              TEXT NOT NULL,
    payment_provider    TEXT NOT NULL,
    external_id         TEXT,
    description         TEXT,
    metadata            TEXT NOT NULL DEFAULT '{}',
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at        TEXT
);

CREATE INDEX idx_payment_transactions_user ON payment_transactions(user_id);

-- ============================================================
-- TRAINER / PT MODULE
-- ============================================================

CREATE TABLE trainer_profiles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    business_name   TEXT,
    bio_vi          TEXT,
    gym_name        TEXT,
    logo_url        TEXT,
    brand_color     TEXT DEFAULT '#22c55e',
    is_verified     INTEGER NOT NULL DEFAULT 0,
    max_clients     INTEGER NOT NULL DEFAULT 50,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    full_name       TEXT,
    age             INTEGER,
    years_experience INTEGER,
    share_token     TEXT UNIQUE
);

CREATE TABLE trainer_credentials (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    trainer_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT,
    image_urls      TEXT NOT NULL DEFAULT '[]',
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_trainer_credentials_trainer ON trainer_credentials(trainer_id);

CREATE TABLE trainer_clients (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    trainer_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    client_id       TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'active',
    started_at      TEXT NOT NULL DEFAULT (date('now')),
    ended_at        TEXT,
    full_name       TEXT,
    goal            TEXT,
    gender          TEXT,
    age             INTEGER,
    height_cm       REAL,
    weight_kg       REAL,
    UNIQUE (trainer_id, client_id)
);

CREATE TABLE trainer_assigned_plans (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    trainer_id          TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    client_id           TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    daily_plan_id       INTEGER REFERENCES user_daily_plans(id) ON DELETE SET NULL,
    title_vi            TEXT NOT NULL,
    notes_vi            TEXT,
    assigned_at         TEXT NOT NULL DEFAULT (datetime('now')),
    status              TEXT NOT NULL DEFAULT 'active'
);

-- ============================================================
-- FULL-TEXT SEARCH (exercises + foods)
-- ============================================================

CREATE VIRTUAL TABLE exercises_fts USING fts5(
    exercise_id UNINDEXED,
    name_en,
    name_vi,
    body_part,
    equipment,
    content='',
    tokenize='unicode61 remove_diacritics 2'
);

CREATE VIRTUAL TABLE foods_fts USING fts5(
    food_id UNINDEXED,
    name_vi,
    aliases,
    content='',
    tokenize='unicode61 remove_diacritics 2'
);
