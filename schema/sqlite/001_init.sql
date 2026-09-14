-- TAPTOT Database Schema (SQLite - local development)
-- Applied automatically by scripts/setup_db.py

PRAGMA foreign_keys = ON;

CREATE TABLE exercises (
    id                  TEXT PRIMARY KEY CHECK(length(id) = 4),
    name_en             TEXT NOT NULL,
    body_part           TEXT NOT NULL,
    equipment           TEXT NOT NULL,
    target_muscle       TEXT NOT NULL,
    muscle_group        TEXT,
    secondary_muscles   TEXT NOT NULL DEFAULT '[]',
    difficulty          TEXT NOT NULL DEFAULT 'beginner'
        CHECK (difficulty IN ('beginner', 'intermediate', 'advanced')),
    is_beginner_friendly INTEGER NOT NULL DEFAULT 1,
    media_id            TEXT,
    image_url           TEXT,
    gif_url             TEXT,
    attribution         TEXT,
    instruction_en      TEXT,
    instruction_steps_en TEXT,
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_exercises_body_part ON exercises(body_part);
CREATE INDEX idx_exercises_equipment ON exercises(equipment);
CREATE INDEX idx_exercises_difficulty ON exercises(difficulty);
CREATE INDEX idx_exercises_beginner ON exercises(is_beginner_friendly);

CREATE TABLE exercise_localizations (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_id         TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    locale              TEXT NOT NULL DEFAULT 'vi',
    name                TEXT NOT NULL,
    instruction         TEXT,
    instruction_steps   TEXT,
    common_mistakes     TEXT,
    tips                TEXT,
    UNIQUE (exercise_id, locale)
);

CREATE TABLE body_part_labels (
    key         TEXT PRIMARY KEY,
    label_vi    TEXT NOT NULL
);

CREATE TABLE equipment_labels (
    key         TEXT PRIMARY KEY,
    label_vi    TEXT NOT NULL
);

CREATE TABLE food_categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    slug        TEXT UNIQUE NOT NULL,
    name_vi     TEXT NOT NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE foods (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT UNIQUE NOT NULL,
    name_vi         TEXT NOT NULL,
    name_en         TEXT,
    category_id     INTEGER REFERENCES food_categories(id),
    serving_size    TEXT NOT NULL,
    serving_grams   REAL,
    calories        REAL NOT NULL,
    protein_g       REAL NOT NULL,
    carbs_g         REAL NOT NULL,
    fat_g           REAL NOT NULL,
    fiber_g         REAL,
    sugar_g         REAL,
    sodium_mg       REAL,
    is_verified     INTEGER NOT NULL DEFAULT 0,
    is_common       INTEGER NOT NULL DEFAULT 0,
    tags            TEXT NOT NULL DEFAULT '[]',
    image_url       TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_foods_category ON foods(category_id);
CREATE INDEX idx_foods_common ON foods(is_common);

CREATE TABLE programs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    slug                TEXT UNIQUE NOT NULL,
    title_vi            TEXT NOT NULL,
    description_vi      TEXT,
    goal                TEXT NOT NULL,
    level               TEXT NOT NULL,
    location            TEXT NOT NULL,
    duration_days       INTEGER NOT NULL,
    days_per_week       INTEGER NOT NULL,
    equipment_filter    TEXT,
    is_free             INTEGER NOT NULL DEFAULT 1,
    is_published        INTEGER NOT NULL DEFAULT 0,
    cover_image_url     TEXT,
    sort_order          INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE program_days (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id      INTEGER NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    day_number      INTEGER NOT NULL,
    title_vi        TEXT,
    is_rest_day     INTEGER NOT NULL DEFAULT 0,
    notes_vi        TEXT,
    UNIQUE (program_id, day_number)
);

CREATE TABLE program_day_exercises (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    program_day_id  INTEGER NOT NULL REFERENCES program_days(id) ON DELETE CASCADE,
    exercise_id     TEXT NOT NULL REFERENCES exercises(id),
    sort_order      INTEGER NOT NULL,
    sets            INTEGER NOT NULL,
    reps            TEXT,
    rest_seconds    INTEGER NOT NULL DEFAULT 60,
    notes_vi        TEXT,
    UNIQUE (program_day_id, sort_order)
);

CREATE TABLE users (
    id              TEXT PRIMARY KEY,
    email           TEXT UNIQUE,
    password_hash   TEXT,
    display_name    TEXT,
    role            TEXT NOT NULL DEFAULT 'user',
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE user_profiles (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    gender              TEXT,
    birth_year          INTEGER,
    height_cm           REAL,
    weight_kg           REAL,
    activity_level      TEXT,
    goal                TEXT,
    target_weight_kg    REAL,
    training_location   TEXT,
    available_equipment TEXT NOT NULL DEFAULT '[]',
    tdee                INTEGER,
    target_calories     INTEGER,
    target_protein_g    INTEGER,
    target_carbs_g      INTEGER,
    target_fat_g        INTEGER,
    experience_level    TEXT NOT NULL DEFAULT 'beginner',
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE user_program_enrollments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    program_id      INTEGER NOT NULL REFERENCES programs(id),
    started_at      TEXT NOT NULL DEFAULT (date('now')),
    current_day     INTEGER NOT NULL DEFAULT 1,
    status          TEXT NOT NULL DEFAULT 'active',
    completed_at    TEXT
);

CREATE TABLE workout_sessions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    program_day_id      INTEGER REFERENCES program_days(id),
    enrollment_id       INTEGER REFERENCES user_program_enrollments(id),
    title_vi            TEXT,
    started_at          TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at        TEXT,
    duration_seconds    INTEGER,
    notes               TEXT
);

CREATE TABLE workout_session_sets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES workout_sessions(id) ON DELETE CASCADE,
    exercise_id     TEXT NOT NULL REFERENCES exercises(id),
    set_number      INTEGER NOT NULL,
    target_reps     TEXT,
    actual_reps     INTEGER,
    weight_kg       REAL,
    is_completed    INTEGER NOT NULL DEFAULT 0,
    rest_seconds    INTEGER
);

CREATE TABLE meal_plans (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title_vi        TEXT,
    target_calories INTEGER,
    target_date     TEXT,
    source          TEXT NOT NULL DEFAULT 'manual',
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE meal_plan_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    meal_plan_id    INTEGER NOT NULL REFERENCES meal_plans(id) ON DELETE CASCADE,
    meal_type       TEXT NOT NULL,
    food_id         INTEGER NOT NULL REFERENCES foods(id),
    servings        REAL NOT NULL DEFAULT 1,
    sort_order      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE calculator_logs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             TEXT REFERENCES users(id),
    session_id          TEXT,
    calculator_type     TEXT NOT NULL,
    input_data          TEXT NOT NULL,
    result_data         TEXT NOT NULL,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE user_workout_plans (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title_vi        TEXT NOT NULL,
    description_vi  TEXT,
    is_template     INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE user_workout_plan_exercises (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id         INTEGER NOT NULL REFERENCES user_workout_plans(id) ON DELETE CASCADE,
    exercise_id     TEXT NOT NULL REFERENCES exercises(id),
    day_of_week     INTEGER,
    sort_order      INTEGER NOT NULL,
    sets            INTEGER NOT NULL,
    reps            TEXT,
    rest_seconds    INTEGER NOT NULL DEFAULT 60,
    notes_vi        TEXT
);

CREATE TABLE exports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    export_type     TEXT NOT NULL,
    source_id       INTEGER,
    format          TEXT NOT NULL,
    template_id     TEXT NOT NULL DEFAULT 'default',
    file_url        TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE subscription_plans (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    slug                        TEXT UNIQUE NOT NULL,
    name_vi                     TEXT NOT NULL,
    price_vnd                   INTEGER NOT NULL,
    billing_period              TEXT NOT NULL,
    ai_generations_per_month    INTEGER,
    features                    TEXT NOT NULL DEFAULT '{}',
    is_active                   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE subscriptions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id             INTEGER NOT NULL REFERENCES subscription_plans(id),
    status              TEXT NOT NULL,
    started_at          TEXT NOT NULL,
    expires_at          TEXT,
    payment_provider    TEXT,
    external_id         TEXT
);

CREATE TABLE ai_generations (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    generation_type     TEXT NOT NULL,
    input_params        TEXT NOT NULL,
    output_data         TEXT NOT NULL,
    tokens_used         INTEGER,
    cost_usd            REAL,
    is_paid             INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE ai_qa_messages (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id                     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id             TEXT NOT NULL,
    role                        TEXT NOT NULL,
    content                     TEXT NOT NULL,
    referenced_exercise_ids     TEXT,
    referenced_food_ids         TEXT,
    created_at                  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE equipment_products (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT UNIQUE NOT NULL,
    name_vi         TEXT NOT NULL,
    equipment_type  TEXT,
    shopee_url      TEXT,
    lazada_url      TEXT,
    image_url       TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE exercise_equipment_suggestions (
    exercise_id     TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    product_id      INTEGER NOT NULL REFERENCES equipment_products(id) ON DELETE CASCADE,
    PRIMARY KEY (exercise_id, product_id)
);

CREATE TABLE knowledge_series (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT UNIQUE NOT NULL,
    title_vi        TEXT NOT NULL,
    description_vi  TEXT,
    level           TEXT NOT NULL,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    is_published    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE knowledge_articles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id       INTEGER REFERENCES knowledge_series(id),
    slug            TEXT UNIQUE NOT NULL,
    title_vi        TEXT NOT NULL,
    content_md      TEXT NOT NULL,
    level           TEXT NOT NULL,
    read_time_min   INTEGER,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    is_published    INTEGER NOT NULL DEFAULT 0,
    published_at    TEXT,
    seo_title       TEXT,
    seo_description TEXT
);
