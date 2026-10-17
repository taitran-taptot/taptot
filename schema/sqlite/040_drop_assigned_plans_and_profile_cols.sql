-- SQLite: drop unused assigned-plans table. Columns dropped in ensure leftover loop.
PRAGMA foreign_keys = OFF;
DROP TABLE IF EXISTS trainer_assigned_plans;
PRAGMA foreign_keys = ON;
