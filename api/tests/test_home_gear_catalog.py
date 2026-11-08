"""Public catalog stays on bodyweight plus the five home-gear filters."""

from sqlalchemy import create_engine, text

from app.services.exercise_video_policy import deactivate_exercises_outside_home_gear


def _engine():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE equipment (
                    id INTEGER PRIMARY KEY,
                    slug TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE exercises (
                    id INTEGER PRIMARY KEY,
                    name_en TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    owner_user_id TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE exercise_equipment (
                    exercise_id INTEGER NOT NULL,
                    equipment_id INTEGER NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                "INSERT INTO equipment (id, slug) VALUES (1, 'barbell'), (2, 'dumbbell'), (3, 'bench')"
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO exercises (id, name_en, is_active, owner_user_id) VALUES
                    (1, 'Barbell Squat', 1, NULL),
                    (2, 'Push-up', 1, NULL),
                    (3, 'Dumbbell Press', 1, NULL),
                    (4, 'Trainer Barbell Row', 1, 'hlv-1')
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO exercise_equipment (exercise_id, equipment_id) VALUES
                    (1, 1),
                    (3, 2),
                    (3, 3),
                    (4, 1)
                """
            )
        )
    return engine


def test_deactivate_keeps_bodyweight_dumbbell_and_trainer_rows():
    engine = _engine()
    with engine.begin() as conn:
        dropped = deactivate_exercises_outside_home_gear(conn, is_sqlite=True)
        rows = {
            name: active
            for name, active in conn.execute(
                text("SELECT name_en, is_active FROM exercises ORDER BY id")
            )
        }
    assert dropped == 1
    assert rows == {
        "Barbell Squat": 0,
        "Push-up": 1,
        "Dumbbell Press": 1,
        "Trainer Barbell Row": 1,
    }
