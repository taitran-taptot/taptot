"""Tests for exercise movement_pattern inference + ensure migrator."""

from sqlalchemy import create_engine, text

from app.core.migrations import ensure_exercise_movement_pattern
from app.services.exercise_movement_pattern import VALID_PATTERNS, infer_movement_pattern


def test_infer_h_push_bench():
    assert (
        infer_movement_pattern({"name_en": "Barbell Bench Press", "name_vi": "Ép ngực"})
        == "h_push"
    )


def test_infer_h_pull_row():
    assert (
        infer_movement_pattern({"name_en": "Barbell Row", "name_vi": "Chèo tạ đòn"})
        == "h_pull"
    )


def test_infer_v_push_ohp():
    assert (
        infer_movement_pattern({"name_en": "Overhead Press", "name_vi": "Ép vai"})
        == "v_push"
    )


def test_infer_v_pull_pulldown():
    assert (
        infer_movement_pattern({"name_en": "Lat Pulldown", "name_vi": "Kéo xô"})
        == "v_pull"
    )


def test_infer_squat():
    assert infer_movement_pattern({"name_en": "Back Squat", "name_vi": "Squat"}) == "squat"


def test_infer_hinge_rdl():
    assert (
        infer_movement_pattern({"name_en": "Romanian Deadlift", "name_vi": "RDL"})
        == "hinge"
    )


def test_infer_core_plank():
    assert infer_movement_pattern({"name_en": "Plank", "name_vi": "Plank"}) == "core"


def test_infer_vi_chest_press():
    assert (
        infer_movement_pattern({"name_vi": "Đẩy ngực dốc lên với tạ đơn", "name_en": ""})
        == "h_push"
    )


def test_infer_vi_biceps_curl():
    assert (
        infer_movement_pattern({"name_vi": "Cuốn bắp tay với tạ đơn", "name_en": "Dumbbell Curl"})
        == "other"
    )


def test_infer_pike_push_up_is_v_push():
    assert (
        infer_movement_pattern({"name_vi": "Chống đẩy kiểu pike", "name_en": "Pike Push-Up"})
        == "v_push"
    )
    assert (
        infer_movement_pattern(
            {"name_vi": "Chống đẩy pike chân cao", "name_en": "Elevated Pike Push-Up"}
        )
        == "v_push"
    )


def test_infer_pike_dip_stays_h_push():
    assert infer_movement_pattern({"name_vi": "Hít kiểu pike", "name_en": "Pike Dip"}) == "h_push"


def test_infer_dip_is_h_push_not_v_pull():
    assert (
        infer_movement_pattern({"name_vi": "Hít xà kép", "name_en": "Chest Dip"})
        == "h_push"
    )
    assert (
        infer_movement_pattern({"name_vi": "Hít xà kép trên ring", "name_en": "Ring Dip"})
        == "h_push"
    )


def test_infer_pull_up_stays_v_pull():
    assert infer_movement_pattern({"name_en": "Pull-Up", "name_vi": "Kéo xà"}) == "v_pull"


def test_infer_db_row_stays_h_pull():
    assert (
        infer_movement_pattern(
            {"name_en": "Single-Arm Dumbbell Row", "name_vi": "Kéo tạ đơn một tay"}
        )
        == "h_pull"
    )


def test_infer_muscle_slug_fallback():
    assert (
        infer_movement_pattern(
            {
                "name_vi": "Bài lạ không keyword",
                "name_en": "Unknown move",
                "exercise_type": "main",
                "muscle_slug": "chest",
            }
        )
        == "h_push"
    )


def test_infer_lateral_raise_other():
    assert (
        infer_movement_pattern(
            {"name_en": "Dumbbell Lateral Raise", "name_vi": "Dang vai tạ đơn"}
        )
        == "other"
    )


def test_infer_chest_fly_other():
    assert infer_movement_pattern({"name_en": "Cable Fly", "name_vi": "Ép ngực cáp"}) == "other"


def test_infer_floor_press_h_push():
    assert (
        infer_movement_pattern({"name_en": "Floor Press", "name_vi": "Ép ngực dưới sàn"})
        == "h_push"
    )
    assert (
        infer_movement_pattern(
            {"name_en": "Arm Circles", "name_vi": "Xoay tay", "exercise_type": "warmup"}
        )
        == "other"
    )


def test_ensure_backfills_sqlite(tmp_path):
    db = tmp_path / "pat.db"
    engine = create_engine(f"sqlite:///{db}")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE exercises (
                    id INTEGER PRIMARY KEY,
                    name_vi TEXT NOT NULL,
                    name_en TEXT,
                    exercise_type TEXT NOT NULL DEFAULT 'main'
                )
                """
            )
        )
        conn.execute(
            text(
                "INSERT INTO exercises (id, name_vi, name_en, exercise_type) VALUES "
                "(1, 'Ép ngực', 'Bench Press', 'main'), "
                "(2, 'Chèo', 'Seated Cable Row', 'main'), "
                "(3, 'Ép vai', 'Overhead Press', 'main'), "
                "(4, 'Kéo xô', 'Pull-up', 'main'), "
                "(5, 'Squat', 'Squat', 'main'), "
                "(6, 'RDL', 'Romanian Deadlift', 'main'), "
                "(7, 'Plank', 'Plank', 'main'), "
                "(8, 'Xoay', 'Arm Circles', 'warmup')"
            )
        )

    ensure_exercise_movement_pattern(engine)
    with engine.connect() as conn:
        rows = {
            r[0]: r[1]
            for r in conn.execute(text("SELECT id, movement_pattern FROM exercises ORDER BY id"))
        }
        assert rows[1] == "h_push"
        assert rows[2] == "h_pull"
        assert rows[3] == "v_push"
        assert rows[4] == "v_pull"
        assert rows[5] == "squat"
        assert rows[6] == "hinge"
        assert rows[7] == "core"
        assert rows[8] == "other"
        assert all(v in VALID_PATTERNS for v in rows.values())

        with engine.begin() as w:
            w.execute(text("UPDATE exercises SET movement_pattern = 'core' WHERE id = 1"))

    ensure_exercise_movement_pattern(engine)
    with engine.connect() as conn:
        assert (
            conn.execute(text("SELECT movement_pattern FROM exercises WHERE id = 1")).scalar()
            == "core"
        )
