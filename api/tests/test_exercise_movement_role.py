"""Tests for exercise movement_role inference + ensure migrator."""

from sqlalchemy import create_engine, text

from app.core.migrations import ensure_exercise_movement_role
from app.services.exercise_movement_role import VALID_ROLES, infer_movement_role


def test_infer_compound_bench():
    assert (
        infer_movement_role(
            {"name_en": "Barbell Bench Press", "name_vi": "Ép ngực tạ đòn", "exercise_type": "main"}
        )
        == "compound"
    )


def test_infer_isolation_curl():
    assert (
        infer_movement_role(
            {"name_en": "Dumbbell Bicep Curl", "name_vi": "Cuốn tay tạ đơn", "exercise_type": "main"}
        )
        == "isolation"
    )


def test_infer_mobility_warmup():
    assert (
        infer_movement_role(
            {"name_en": "Arm Circles", "name_vi": "Xoay tay", "exercise_type": "warmup"}
        )
        == "mobility"
    )


def test_infer_cardio():
    assert (
        infer_movement_role(
            {"name_en": "Treadmill Run", "name_vi": "Chạy bộ", "exercise_type": "cardio"}
        )
        == "cardio"
    )


def test_infer_isolation_face_pull():
    assert (
        infer_movement_role(
            {"name_en": "Face Pull", "name_vi": "Kéo mặt", "exercise_type": "main"}
        )
        == "isolation"
    )


def test_infer_isolation_ep_nguc_fly():
    assert (
        infer_movement_role(
            {"name_en": "Pec Deck", "name_vi": "Ép ngực", "exercise_type": "main"}
        )
        == "isolation"
    )


def test_infer_fallback_isolation():
    assert infer_movement_role({"name_en": "Mystery Move", "exercise_type": "main"}) == "isolation"


def test_ensure_backfills_sqlite(tmp_path):
    db = tmp_path / "ex.db"
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
                "(2, 'Cuốn tay', 'Bicep Curl', 'main'), "
                "(3, 'Xoay khớp', 'Arm Circles', 'warmup'), "
                "(4, 'Chạy bộ', 'Jog', 'cardio')"
            )
        )

    ensure_exercise_movement_role(engine)
    with engine.connect() as conn:
        rows = {
            r[0]: r[1]
            for r in conn.execute(text("SELECT id, movement_role FROM exercises ORDER BY id"))
        }
        assert rows[1] == "compound"
        assert rows[2] == "isolation"
        assert rows[3] == "mobility"
        assert rows[4] == "cardio"
        assert all(v in VALID_ROLES for v in rows.values())

        # Manual override must not be overwritten
        with engine.begin() as conn:
            conn.execute(text("UPDATE exercises SET movement_role = 'compound' WHERE id = 2"))

    ensure_exercise_movement_role(engine)
    with engine.connect() as conn:
        role2 = conn.execute(text("SELECT movement_role FROM exercises WHERE id = 2")).scalar()
        assert role2 == "compound"
