from datetime import UTC, datetime

from sqlalchemy import create_engine, text

from app.services.familiarization_exercise_seed import (
    BEGINNER_MARKER_PREFIX,
    ensure_beginner_placeholders,
)
from app.services.muscle_group_hierarchy_seed import seed_muscle_group_hierarchy


def _build_sqlite():
    engine = create_engine("sqlite:///:memory:")
    now = datetime.now(UTC).isoformat()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE muscle_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slug TEXT NOT NULL UNIQUE,
                    name_vi TEXT NOT NULL,
                    name_en TEXT,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    parent_id INTEGER,
                    is_filter_only INTEGER NOT NULL DEFAULT 0
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE equipment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slug TEXT NOT NULL UNIQUE,
                    name_vi TEXT NOT NULL,
                    name_en TEXT,
                    category TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    image_url TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE exercises (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name_vi TEXT NOT NULL,
                    name_en TEXT,
                    muscle_group_id INTEGER NOT NULL,
                    exercise_type TEXT NOT NULL DEFAULT 'main',
                    movement_role TEXT,
                    movement_pattern TEXT,
                    venue TEXT,
                    difficulty INTEGER NOT NULL DEFAULT 2,
                    difficulty_label TEXT,
                    notes_vi TEXT,
                    secondary_muscles TEXT NOT NULL DEFAULT '[]',
                    instruction_steps_vi TEXT,
                    tips_vi TEXT,
                    image_url TEXT,
                    gif_url TEXT,
                    video_url TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE exercise_equipment (
                    exercise_id INTEGER NOT NULL,
                    equipment_id INTEGER NOT NULL,
                    PRIMARY KEY (exercise_id, equipment_id)
                )
                """
            )
        )
        seed_muscle_group_hierarchy(conn, is_sqlite=True)
        conn.execute(
            text(
                """
                INSERT INTO exercises (
                    name_vi, name_en, muscle_group_id, notes_vi, video_url,
                    is_active, created_at, updated_at
                ) VALUES
                ('Ngồi xổm không tạ', 'Bodyweight Squat', 1, 'catalog squat',
                 'complete-exercise-library/bodyweight-squat.mp4', 1, :now, :now),
                ('Squat thể trọng', 'Bodyweight Squat', 1, :squat_marker,
                 NULL, 1, :now, :now),
                ('Chống đẩy chống gối', 'Bodyweight Knee Push Ups', 1, 'catalog knee',
                 'complete-exercise-library/bodyweight-knee-push-ups.mp4', 1, :now, :now),
                ('Chống đẩy quỳ gối', 'Knee Push-up', 1, :knee_marker,
                 'complete-exercise-library/bodyweight-knee-push-ups.mp4', 1, :now, :now),
                ('Treo xà thả lỏng', 'Dead Hang', 1, 'catalog hang',
                 'complete-exercise-library/dead-hang.mp4', 1, :now, :now),
                ('Treo người trên xà', 'Dead Hang', 1, :hang_marker,
                 NULL, 1, :now, :now)
                """
            ),
            {
                "now": now,
                "squat_marker": f"{BEGINNER_MARKER_PREFIX}bodyweight-squat",
                "knee_marker": f"{BEGINNER_MARKER_PREFIX}knee-push-up",
                "hang_marker": f"{BEGINNER_MARKER_PREFIX}dead-hang",
            },
        )
    return engine


def test_deletes_seed_duplicates_when_catalog_already_has_video():
    engine = _build_sqlite()
    with engine.begin() as conn:
        ensure_beginner_placeholders(conn, is_sqlite=True)
        names = [
            tuple(row)
            for row in conn.execute(
                text(
                    """
                    SELECT name_en, name_vi, notes_vi
                    FROM exercises
                    WHERE name_en IN (
                        'Bodyweight Squat', 'Knee Push-up',
                        'Bodyweight Knee Push Ups', 'Dead Hang'
                    )
                    ORDER BY id
                    """
                )
            ).fetchall()
        ]

    assert names == [
        ("Bodyweight Squat", "Ngồi xổm không tạ", "catalog squat"),
        ("Bodyweight Knee Push Ups", "Chống đẩy chống gối", "catalog knee"),
        ("Dead Hang", "Treo xà thả lỏng", "catalog hang"),
    ]
    markers = {row[2] for row in names}
    assert f"{BEGINNER_MARKER_PREFIX}bodyweight-squat" not in markers
    assert f"{BEGINNER_MARKER_PREFIX}knee-push-up" not in markers
    assert f"{BEGINNER_MARKER_PREFIX}dead-hang" not in markers


def test_purge_keeps_listed_no_video_and_deletes_others():
    from app.services.exercise_video_policy import purge_exercises_missing_video

    engine = _build_sqlite()
    now = datetime.now(UTC).isoformat()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO exercises (
                    name_vi, name_en, muscle_group_id, notes_vi, video_url,
                    is_active, created_at, updated_at
                ) VALUES
                ('Ép ngực với dây kháng lực', 'Band Chest Press', 1, 'seed:keep',
                 NULL, 0, :now, :now),
                ('Giữ thân rỗng', 'Hollow Body Hold', 1, 'seed:drop',
                 NULL, 1, :now, :now),
                ('Ngồi xổm không tạ', 'Bodyweight Squat', 1, 'has video',
                 'complete-exercise-library/bodyweight-squat.mp4', 1, :now, :now)
                """
            ),
            {"now": now},
        )
        dropped = purge_exercises_missing_video(conn, is_sqlite=True)
        assert dropped >= 1
        rows = {
            str(r[0]): (int(r[1]), r[2])
            for r in conn.execute(
                text("SELECT name_en, is_active, video_url FROM exercises")
            ).fetchall()
        }
        assert "Band Chest Press" in rows
        assert rows["Band Chest Press"][0] == 1
        assert "Hollow Body Hold" not in rows
        assert "Bodyweight Squat" in rows

