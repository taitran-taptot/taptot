-- Extended nutrition: vitamins & minerals (JSON), sugar/sodium already in base schema
ALTER TABLE foods ADD COLUMN vitamins_json TEXT NOT NULL DEFAULT '{}';
