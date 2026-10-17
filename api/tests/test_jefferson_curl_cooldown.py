"""Bodyweight Jefferson curl is catalogued as giãn cơ (cooldown)."""

from datetime import datetime

from sqlalchemy import create_engine, text

from app.core.migrations.ensures import ensure_jefferson_curl_is_cooldown


def test_jefferson_curl_becomes_cooldown_mobility():
    engine = create_engine("sqlite:///:memory:")
    now = datetime.now().isoformat()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE exercises (
                    id INTEGER PRIMARY KEY,
                    name_vi TEXT NOT NULL,
                    name_en TEXT,
                    muscle_group_id INTEGER NOT NULL DEFAULT 1,
                    exercise_type TEXT NOT NULL DEFAULT 'main',
                    movement_role TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                "INSERT INTO exercises (id, name_vi, name_en, exercise_type, movement_role, "
                "created_at, updated_at) VALUES "
                "(1, 'Cuộn Cột Sống Jefferson Không Tạ', 'Bodyweight Spinal Jefferson Curl', "
                "'main', 'isolation', :c, :u),"
                "(2, 'Hít xà', 'Pull Ups', 'main', 'compound', :c, :u)"
            ),
            {"c": now, "u": now},
        )

    ensure_jefferson_curl_is_cooldown(engine)

    with engine.begin() as conn:
        rows = {
            str(r[0]): (str(r[1]), str(r[2]))
            for r in conn.execute(
                text("SELECT name_en, exercise_type, movement_role FROM exercises")
            ).fetchall()
        }
    assert rows["Bodyweight Spinal Jefferson Curl"] == ("cooldown", "mobility")
    assert rows["Pull Ups"] == ("main", "compound")
