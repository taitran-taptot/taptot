-- Food AI metadata for workout schedule meal generation

ALTER TABLE foods ADD COLUMN macro_roles TEXT NOT NULL DEFAULT '[]';
ALTER TABLE foods ADD COLUMN meal_slots TEXT NOT NULL DEFAULT '[]';
ALTER TABLE foods ADD COLUMN ai_eligible INTEGER NOT NULL DEFAULT 1;
ALTER TABLE foods ADD COLUMN ai_priority INTEGER NOT NULL DEFAULT 0;
ALTER TABLE foods ADD COLUMN is_complete_meal INTEGER;
ALTER TABLE foods ADD COLUMN default_for_ai INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_foods_ai_eligible_priority ON foods (ai_eligible, ai_priority DESC);
