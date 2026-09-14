-- Muscle group hierarchy for granular exercise library filters.

ALTER TABLE muscle_groups
    ADD COLUMN IF NOT EXISTS parent_id INT REFERENCES muscle_groups(id) ON DELETE SET NULL;

ALTER TABLE muscle_groups
    ADD COLUMN IF NOT EXISTS is_filter_only BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_muscle_groups_parent ON muscle_groups(parent_id);
