"""Beginner-friendly Vietnamese exercise copy overlay."""

from datetime import UTC, datetime

from sqlalchemy import create_engine, text

from app.core.migrations import ensure_exercise_copy_vi
from app.services.exercise_copy_seed import (
    load_exercise_copy_seed,
    seed_exercise_copy,
    validate_copy_seed,
)


def _build_sqlite():
    engine = create_engine("sqlite:///:memory:")
    now = datetime.now(UTC).isoformat()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE exercises (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name_vi TEXT NOT NULL,
                    name_en TEXT,
                    muscle_group_id INTEGER NOT NULL DEFAULT 1,
                    exercise_type TEXT NOT NULL DEFAULT 'main',
                    instruction_vi TEXT,
                    instruction_steps_vi TEXT,
                    common_mistakes_vi TEXT,
                    tips_vi TEXT,
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
                INSERT INTO exercises
                    (id, name_vi, name_en, instruction_vi, instruction_steps_vi,
                     common_mistakes_vi, tips_vi, created_at, updated_at)
                VALUES
                    (25, 'Ngồi xổm không tạ', 'Bodyweight Squat',
                     'old', '["old"]',
                     '[''Cong lưng.'']',
                     'Placeholder tạm — sẽ bổ sung video sau.',
                     :now, :now),
                    (554, 'Nhấc tạ đòn từ đất', 'Barbell Deadlift',
                     'old', '["old"]',
                     '[''Cong lưng khi nâng, làm yếu cột sống dưới tải trọng nặng.'']',
                     NULL,
                     :now, :now),
                    (63, 'Ép ngực tạ đơn', 'Dumbbell Bench Press',
                     'old', '["old"]',
                     '[''Nảy tạ.'']',
                     NULL,
                     :now, :now)
                """
            ),
            {"now": now},
        )
    return engine


def test_copy_seed_file_covers_active_catalog_and_passes_hygiene():
    items = load_exercise_copy_seed()
    assert len(items) == 353
    names = {str(item["name_en"]) for item in items}
    for required in (
        "Bodyweight Squat",
        "Barbell Bench Press",
        "Barbell Deadlift",
        "Wall Push-up",
        "Ring Push-Up",
        "Pull Ups",
    ):
        assert required in names
    problems = validate_copy_seed(items)
    assert problems == []


def test_seed_updates_instruction_fields_and_is_idempotent():
    engine = _build_sqlite()
    with engine.begin() as conn:
        first = seed_exercise_copy(conn, is_sqlite=True)
        second = seed_exercise_copy(conn, is_sqlite=True)
    assert first == 3
    assert second == 3

    with engine.begin() as conn:
        squat = conn.execute(
            text(
                "SELECT instruction_vi, instruction_steps_vi, common_mistakes_vi, tips_vi "
                "FROM exercises WHERE name_en = 'Bodyweight Squat'"
            )
        ).fetchone()
        deadlift = conn.execute(
            text(
                "SELECT common_mistakes_vi, tips_vi FROM exercises "
                "WHERE name_en = 'Barbell Deadlift'"
            )
        ).fetchone()

    assert squat is not None
    assert squat[0] and "ngồi xổm" in squat[0].lower()
    assert squat[1].startswith("[")
    assert "gối sụp" in squat[2].lower()
    assert not squat[2].lstrip().startswith("[")
    assert squat[3]
    assert "placeholder" not in squat[3].lower()

    assert deadlift is not None
    assert not deadlift[0].lstrip().startswith("[")
    assert "cong lưng" in deadlift[0].lower()
    assert deadlift[1]


def test_ensure_exercise_copy_vi_wrapper():
    engine = _build_sqlite()
    ensure_exercise_copy_vi(engine)
    with engine.begin() as conn:
        tips = conn.execute(
            text("SELECT tips_vi FROM exercises WHERE name_en = 'Bodyweight Squat'")
        ).scalar()
        press_name = conn.execute(
            text("SELECT name_vi FROM exercises WHERE name_en = 'Dumbbell Bench Press'")
        ).scalar()
    assert tips
    assert "placeholder" not in str(tips).lower()
    assert press_name == "Đẩy ngực tạ đơn"
