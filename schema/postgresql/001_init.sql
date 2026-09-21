-- TAPTOT Database Schema (PostgreSQL / Supabase)
-- Run: psql $DATABASE_URL -f schema/postgresql/001_init.sql

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- EXERCISES (imported from exercises-dataset)
-- ============================================================

CREATE TABLE exercises (
    id                  VARCHAR(4) PRIMARY KEY,
    name_en             VARCHAR(255) NOT NULL,
    body_part           VARCHAR(50) NOT NULL,
    equipment           VARCHAR(50) NOT NULL,
    target_muscle       VARCHAR(100) NOT NULL,
    muscle_group        VARCHAR(100),
    secondary_muscles   JSONB NOT NULL DEFAULT '[]',
    difficulty          VARCHAR(20) NOT NULL DEFAULT 'beginner'
        CHECK (difficulty IN ('beginner', 'intermediate', 'advanced')),
    is_beginner_friendly BOOLEAN NOT NULL DEFAULT TRUE,
    media_id            VARCHAR(20),
    image_url           VARCHAR(500),
    gif_url             VARCHAR(500),
    attribution         TEXT,
    instruction_en      TEXT,
    instruction_steps_en JSONB,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_exercises_body_part ON exercises(body_part);
CREATE INDEX idx_exercises_equipment ON exercises(equipment);
CREATE INDEX idx_exercises_difficulty ON exercises(difficulty);
CREATE INDEX idx_exercises_beginner ON exercises(is_beginner_friendly) WHERE is_beginner_friendly = TRUE;

-- ============================================================
-- FOODS (Vietnamese nutrition database)
-- ============================================================

CREATE TABLE food_categories (
    id          SERIAL PRIMARY KEY,
    slug        VARCHAR(50) UNIQUE NOT NULL,
    name_vi     VARCHAR(100) NOT NULL,
    sort_order  INT NOT NULL DEFAULT 0
);

CREATE TABLE foods (
    id              SERIAL PRIMARY KEY,
    slug            VARCHAR(150) UNIQUE NOT NULL,
    name_vi         VARCHAR(255) NOT NULL,
    name_en         VARCHAR(255),
    category_id     INT REFERENCES food_categories(id),
    serving_size    VARCHAR(100) NOT NULL,
    serving_grams   DECIMAL(8, 2),
    calories        DECIMAL(8, 2) NOT NULL,
    protein_g       DECIMAL(8, 2) NOT NULL,
    carbs_g         DECIMAL(8, 2) NOT NULL,
    fat_g           DECIMAL(8, 2) NOT NULL,
    fiber_g         DECIMAL(8, 2),
    sugar_g         DECIMAL(8, 2),
    sodium_mg       DECIMAL(8, 2),
    is_verified     BOOLEAN NOT NULL DEFAULT FALSE,
    is_common       BOOLEAN NOT NULL DEFAULT FALSE,
    tags            JSONB NOT NULL DEFAULT '[]',
    image_url       VARCHAR(500),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_foods_category ON foods(category_id);
CREATE INDEX idx_foods_common ON foods(is_common) WHERE is_common = TRUE;

-- ============================================================
-- USERS & PROGRESS
-- ============================================================

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE,
    password_hash   VARCHAR(255),
    display_name    VARCHAR(100),
    role            VARCHAR(20) NOT NULL DEFAULT 'user',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE user_profiles (
    id                  SERIAL PRIMARY KEY,
    user_id             UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    gender              VARCHAR(10),
    birth_year          INT,
    height_cm           DECIMAL(5, 2),
    weight_kg           DECIMAL(5, 2),
    activity_level      VARCHAR(20),
    goal                VARCHAR(20),
    target_weight_kg    DECIMAL(5, 2),
    training_location   VARCHAR(20),
    available_equipment JSONB NOT NULL DEFAULT '[]',
    tdee                INT,
    target_calories     INT,
    target_protein_g    INT,
    target_carbs_g      INT,
    target_fat_g        INT,
    experience_level    VARCHAR(20) NOT NULL DEFAULT 'beginner',
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE workout_sessions (
    id                  SERIAL PRIMARY KEY,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title_vi            VARCHAR(255),
    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    duration_seconds    INT,
    notes               TEXT
);

-- ============================================================
-- MEAL PLANS & CALCULATORS
-- ============================================================

CREATE TABLE meal_plans (
    id              SERIAL PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title_vi        VARCHAR(255),
    target_calories INT,
    target_date     DATE,
    source          VARCHAR(20) NOT NULL DEFAULT 'manual',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE meal_plan_items (
    id              SERIAL PRIMARY KEY,
    meal_plan_id    INT NOT NULL REFERENCES meal_plans(id) ON DELETE CASCADE,
    meal_type       VARCHAR(20) NOT NULL,
    food_id         INT NOT NULL REFERENCES foods(id),
    servings        DECIMAL(4, 2) NOT NULL DEFAULT 1,
    sort_order      INT NOT NULL DEFAULT 0
);

CREATE TABLE calculator_logs (
    id                  SERIAL PRIMARY KEY,
    user_id             UUID REFERENCES users(id),
    session_id          VARCHAR(100),
    calculator_type     VARCHAR(30) NOT NULL,
    input_data          JSONB NOT NULL,
    result_data         JSONB NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- EXPORTS
-- ============================================================

CREATE TABLE exports (
    id              SERIAL PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    export_type     VARCHAR(20) NOT NULL,
    source_id       INT,
    format          VARCHAR(10) NOT NULL,
    template_id     VARCHAR(50) NOT NULL DEFAULT 'default',
    file_url        VARCHAR(500),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- SUBSCRIPTIONS & AI
-- ============================================================

CREATE TABLE subscription_plans (
    id                          SERIAL PRIMARY KEY,
    slug                        VARCHAR(50) UNIQUE NOT NULL,
    name_vi                     VARCHAR(100) NOT NULL,
    price_vnd                   INT NOT NULL,
    billing_period              VARCHAR(20) NOT NULL,
    ai_generations_per_month    INT,
    features                    JSONB NOT NULL DEFAULT '{}',
    is_active                   BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE subscriptions (
    id                  SERIAL PRIMARY KEY,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id             INT NOT NULL REFERENCES subscription_plans(id),
    status              VARCHAR(20) NOT NULL,
    started_at          TIMESTAMPTZ NOT NULL,
    expires_at          TIMESTAMPTZ,
    payment_provider    VARCHAR(30),
    external_id         VARCHAR(255)
);

CREATE TABLE ai_generations (
    id                  SERIAL PRIMARY KEY,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    generation_type     VARCHAR(30) NOT NULL,
    input_params        JSONB NOT NULL,
    output_data         JSONB NOT NULL,
    tokens_used         INT,
    cost_usd            DECIMAL(8, 4),
    is_paid             BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE ai_qa_messages (
    id                          SERIAL PRIMARY KEY,
    user_id                     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id             UUID NOT NULL,
    role                        VARCHAR(10) NOT NULL,
    content                     TEXT NOT NULL,
    referenced_exercise_ids     JSONB,
    referenced_food_ids         JSONB,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- KNOWLEDGE
-- ============================================================

CREATE TABLE knowledge_articles (
    id              SERIAL PRIMARY KEY,
    slug            VARCHAR(150) UNIQUE NOT NULL,
    title_vi        VARCHAR(255) NOT NULL,
    content_md      TEXT NOT NULL,
    level           VARCHAR(20) NOT NULL,
    read_time_min   INT,
    sort_order      INT NOT NULL DEFAULT 0,
    is_published    BOOLEAN NOT NULL DEFAULT FALSE,
    published_at    TIMESTAMPTZ,
    seo_title       VARCHAR(255),
    seo_description TEXT
);
