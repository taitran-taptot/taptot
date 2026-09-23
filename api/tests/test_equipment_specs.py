"""Equipment specs_vi column, seed, and challenge profile brief."""

from sqlalchemy import create_engine, text

from app.core.migrations.ensures import (
    PUBLIC_EQUIPMENT_SPECS_VI,
    ensure_equipment_image_columns,
)
from app.services.workout_generation.challenge_prompt import challenge_user_summary


def test_ensure_adds_specs_and_seeds_public_slugs(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'eq.db'}")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE equipment (
                    id INTEGER PRIMARY KEY,
                    slug TEXT NOT NULL UNIQUE,
                    name_vi TEXT NOT NULL,
                    name_en TEXT,
                    category TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    sort_order INTEGER NOT NULL DEFAULT 0
                )
                """
            )
        )
        conn.execute(
            text(
                "INSERT INTO equipment (id, slug, name_vi) VALUES "
                "(1, 'dumbbell', 'Tạ đơn'),"
                "(2, 'pull-up-bar', 'Xà đơn')"
            )
        )
    ensure_equipment_image_columns(engine)
    with engine.begin() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(equipment)")).fetchall()]
        assert "specs_vi" in cols
        dumbbell = conn.execute(
            text("SELECT specs_vi FROM equipment WHERE slug = 'dumbbell'")
        ).scalar()
        bar = conn.execute(
            text("SELECT specs_vi FROM equipment WHERE slug = 'pull-up-bar'")
        ).scalar()
    assert dumbbell == PUBLIC_EQUIPMENT_SPECS_VI["dumbbell"]
    assert bar == PUBLIC_EQUIPMENT_SPECS_VI["pull-up-bar"]
    assert "50" in dumbbell

    with engine.begin() as conn:
        conn.execute(
            text("UPDATE equipment SET specs_vi = 'bộ custom 30kg' WHERE slug = 'dumbbell'")
        )
    ensure_equipment_image_columns(engine)
    with engine.begin() as conn:
        again = conn.execute(
            text("SELECT specs_vi FROM equipment WHERE slug = 'dumbbell'")
        ).scalar()
    assert again == "bộ custom 30kg"


def test_challenge_user_summary_includes_body_tests_and_specs():
    brief = challenge_user_summary(
        {
            "goal": "lose_weight",
            "height_cm": 173,
            "weight_kg": 80,
            "age": 30,
            "session_minutes": 45,
            "focus_areas": ["nguc"],
            "fitness_baseline": {
                "pushups_max": 15,
                "pullups_max": 4,
                "squats_max": 50,
                "plank_seconds": 90,
            },
            "equipment_specs": [
                {
                    "slug": "dumbbell",
                    "name_vi": "Tạ đơn",
                    "specs_vi": "bộ 50kg",
                }
            ],
        }
    )
    assert "giảm cân" in brief
    assert "173cm/80kg" in brief
    assert "chống đẩy 15" in brief
    assert "kéo xà 4" in brief
    assert "squat 50" in brief
    assert "plank 90s" in brief
    assert "45 phút" in brief
    assert "bộ 50kg" in brief
    assert "ngực" in brief


def test_challenge_user_summary_includes_fat_loss_back_focus():
    brief = challenge_user_summary(
        {
            "goal": "lose_weight",
            "focus_areas": ["mo_lung", "vai_thon"],
            "session_minutes": 45,
        }
    )
    assert "ưu tiên giảm mỡ lưng, vai thon gọn" in brief
