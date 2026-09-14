-- Exercise catalog v2: muscle_groups + equipment + exercises + exercise_equipment
-- Replaces old VARCHAR(4) exercise IDs with integer PKs.
-- Dependent exercise rows must be cleared before applying (see import script).

CREATE TABLE IF NOT EXISTS muscle_groups (
    id          SERIAL PRIMARY KEY,
    slug        VARCHAR(100) NOT NULL UNIQUE,
    name_vi     VARCHAR(255) NOT NULL,
    name_en     VARCHAR(255),
    sort_order  INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS equipment (
    id          SERIAL PRIMARY KEY,
    slug        VARCHAR(120) NOT NULL UNIQUE,
    name_vi     VARCHAR(255) NOT NULL,
    name_en     VARCHAR(255),
    category    VARCHAR(80),
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order  INT NOT NULL DEFAULT 0,
    image_url   TEXT,
    image_source TEXT,
    image_attribution TEXT
);

ALTER TABLE equipment ADD COLUMN IF NOT EXISTS sort_order INT NOT NULL DEFAULT 0;
ALTER TABLE equipment ADD COLUMN IF NOT EXISTS image_url TEXT;
ALTER TABLE equipment ADD COLUMN IF NOT EXISTS image_source TEXT;
ALTER TABLE equipment ADD COLUMN IF NOT EXISTS image_attribution TEXT;

-- New exercises table is created by migration script after dropping the old one.
