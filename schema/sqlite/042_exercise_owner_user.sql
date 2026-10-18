-- HLV-private exercises. Public catalog rows keep owner_user_id NULL.

ALTER TABLE exercises ADD COLUMN owner_user_id TEXT;

CREATE INDEX IF NOT EXISTS idx_exercises_owner_user ON exercises(owner_user_id);
