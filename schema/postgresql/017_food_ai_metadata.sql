-- Food AI metadata for workout schedule meal generation

ALTER TABLE foods ADD COLUMN IF NOT EXISTS macro_roles JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE foods ADD COLUMN IF NOT EXISTS meal_slots JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE foods ADD COLUMN IF NOT EXISTS ai_eligible BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE foods ADD COLUMN IF NOT EXISTS ai_priority SMALLINT NOT NULL DEFAULT 0;
ALTER TABLE foods ADD COLUMN IF NOT EXISTS is_complete_meal BOOLEAN;
ALTER TABLE foods ADD COLUMN IF NOT EXISTS default_for_ai BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_foods_ai_eligible_priority ON foods (ai_eligible, ai_priority DESC);
