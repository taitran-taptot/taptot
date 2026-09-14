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

CREATE TABLE exercise_localizations (
    id                  SERIAL PRIMARY KEY,
    exercise_id         VARCHAR(4) NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    locale              VARCHAR(5) NOT NULL DEFAULT 'vi',
    name                VARCHAR(255) NOT NULL,
    instruction         TEXT,
    instruction_steps   JSONB,
    common_mistakes     TEXT,
    tips                TEXT,
    UNIQUE (exercise_id, locale)
);

CREATE TABLE body_part_labels (
    key         VARCHAR(50) PRIMARY KEY,
    label_vi    VARCHAR(100) NOT NULL
);

CREATE TABLE equipment_labels (
    key         VARCHAR(50) PRIMARY KEY,
    label_vi    VARCHAR(100) NOT NULL
);

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
-- PROGRAMS (Coach 30 ngày)
-- ============================================================

CREATE TABLE programs (
    id                  SERIAL PRIMARY KEY,
    slug                VARCHAR(100) UNIQUE NOT NULL,
    title_vi            VARCHAR(255) NOT NULL,
    description_vi      TEXT,
    goal                VARCHAR(50) NOT NULL,
    level               VARCHAR(20) NOT NULL,
    location            VARCHAR(20) NOT NULL,
    duration_days       INT NOT NULL,
    days_per_week       INT NOT NULL,
    equipment_filter    JSONB,
    is_free             BOOLEAN NOT NULL DEFAULT TRUE,
    is_published        BOOLEAN NOT NULL DEFAULT FALSE,
    cover_image_url     VARCHAR(500),
    sort_order          INT NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE program_days (
    id              SERIAL PRIMARY KEY,
    program_id      INT NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    day_number      INT NOT NULL,
    title_vi        VARCHAR(255),
    is_rest_day     BOOLEAN NOT NULL DEFAULT FALSE,
    notes_vi        TEXT,
    UNIQUE (program_id, day_number)
);

CREATE TABLE program_day_exercises (
    id              SERIAL PRIMARY KEY,
    program_day_id  INT NOT NULL REFERENCES program_days(id) ON DELETE CASCADE,
    exercise_id     VARCHAR(4) NOT NULL REFERENCES exercises(id),
    sort_order      INT NOT NULL,
    sets            INT NOT NULL,
    reps            VARCHAR(50),
    rest_seconds    INT NOT NULL DEFAULT 60,
    notes_vi        TEXT,
    UNIQUE (program_day_id, sort_order)
);

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

CREATE TABLE user_program_enrollments (
    id              SERIAL PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    program_id      INT NOT NULL REFERENCES programs(id),
    started_at      DATE NOT NULL DEFAULT CURRENT_DATE,
    current_day     INT NOT NULL DEFAULT 1,
    status          VARCHAR(20) NOT NULL DEFAULT 'active',
    completed_at    TIMESTAMPTZ
);

CREATE TABLE workout_sessions (
    id                  SERIAL PRIMARY KEY,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    program_day_id      INT REFERENCES program_days(id),
    enrollment_id       INT REFERENCES user_program_enrollments(id),
    title_vi            VARCHAR(255),
    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    duration_seconds    INT,
    notes               TEXT
);

CREATE TABLE workout_session_sets (
    id              SERIAL PRIMARY KEY,
    session_id      INT NOT NULL REFERENCES workout_sessions(id) ON DELETE CASCADE,
    exercise_id     VARCHAR(4) NOT NULL REFERENCES exercises(id),
    set_number      INT NOT NULL,
    target_reps     VARCHAR(50),
    actual_reps     INT,
    weight_kg       DECIMAL(6, 2),
    is_completed    BOOLEAN NOT NULL DEFAULT FALSE,
    rest_seconds    INT
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
-- MANUAL WORKOUT PLANS & EXPORTS
-- ============================================================

CREATE TABLE user_workout_plans (
    id              SERIAL PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title_vi        VARCHAR(255) NOT NULL,
    description_vi  TEXT,
    is_template     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE user_workout_plan_exercises (
    id              SERIAL PRIMARY KEY,
    plan_id         INT NOT NULL REFERENCES user_workout_plans(id) ON DELETE CASCADE,
    exercise_id     VARCHAR(4) NOT NULL REFERENCES exercises(id),
    day_of_week     INT,
    sort_order      INT NOT NULL,
    sets            INT NOT NULL,
    reps            VARCHAR(50),
    rest_seconds    INT NOT NULL DEFAULT 60,
    notes_vi        TEXT
);

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
-- AFFILIATE & KNOWLEDGE
-- ============================================================

CREATE TABLE equipment_products (
    id              SERIAL PRIMARY KEY,
    slug            VARCHAR(100) UNIQUE NOT NULL,
    name_vi         VARCHAR(255) NOT NULL,
    equipment_type  VARCHAR(50),
    shopee_url      VARCHAR(500),
    lazada_url      VARCHAR(500),
    image_url       VARCHAR(500),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE exercise_equipment_suggestions (
    exercise_id     VARCHAR(4) NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    product_id      INT NOT NULL REFERENCES equipment_products(id) ON DELETE CASCADE,
    PRIMARY KEY (exercise_id, product_id)
);

CREATE TABLE knowledge_series (
    id              SERIAL PRIMARY KEY,
    slug            VARCHAR(100) UNIQUE NOT NULL,
    title_vi        VARCHAR(255) NOT NULL,
    description_vi  TEXT,
    level           VARCHAR(20) NOT NULL,
    sort_order      INT NOT NULL DEFAULT 0,
    is_published    BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE knowledge_articles (
    id              SERIAL PRIMARY KEY,
    series_id       INT REFERENCES knowledge_series(id),
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
