"""Tests for set/rep prescription defaults seed + helper."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.migrations import ensure_exercise_prescription_defaults
from app.services.exercise_prescription import clamp_experience_level, get_prescription
from app.services.exercise_prescription_seed import PRESCRIPTION_SEED


def test_seed_has_six_rows_levels_1_to_3():
    assert len(PRESCRIPTION_SEED) == 6
    assert {r[0] for r in PRESCRIPTION_SEED} == {1, 2, 3}
    assert {r[1] for r in PRESCRIPTION_SEED} == {"compound", "isolation"}


def test_clamp_experience_level():
    assert clamp_experience_level(1) == 1
    assert clamp_experience_level(3) == 3
    assert clamp_experience_level(4) == 3
    assert clamp_experience_level(0) == 1
    assert clamp_experience_level(None) == 2


def test_ensure_and_get_prescription_sqlite(tmp_path):
    db = tmp_path / "epd.db"
    engine = create_engine(f"sqlite:///{db}")
    ensure_exercise_prescription_defaults(engine)

    with engine.connect() as conn:
        n = conn.execute(text("SELECT COUNT(*) FROM exercise_prescription_defaults")).scalar()
        assert int(n) == 6

        # Idempotent upsert
        ensure_exercise_prescription_defaults(engine)
        n2 = conn.execute(text("SELECT COUNT(*) FROM exercise_prescription_defaults")).scalar()
        assert int(n2) == 6

    Session = sessionmaker(bind=engine)
    db_session = Session()
    try:
        assert get_prescription(db_session, 1, "compound") == (3, "8-12", 7)
        assert get_prescription(db_session, 1, "isolation") == (3, "12-18", 7)
        assert get_prescription(db_session, 2, "compound") == (3, "6-10", 8)
        assert get_prescription(db_session, 2, "isolation") == (3, "9-15", 8)
        assert get_prescription(db_session, 3, "compound") == (3, "5-8", 8)
        assert get_prescription(db_session, 3, "isolation") == (3, "7-13", 7)
        # L4 clamps to L3
        assert get_prescription(db_session, 4, "compound") == (3, "5-8", 8)
        rx = get_prescription(db_session, 1, "isolation", goal="lose_weight")
        assert rx is not None and rx.reps == "12-20"
        assert get_prescription(db_session, 2, "mobility") is None
        assert get_prescription(db_session, 2, "cardio") is None
        assert get_prescription(db_session, 2, None) is None
        hyp = get_prescription(db_session, 3, "compound", goal="gain_muscle")
        assert hyp == (3, "8-12", 8)
        strength = get_prescription(
            db_session, 3, "compound", goal="gain_muscle", extra_goals=["strength"]
        )
        assert strength == (3, "5-8", 8)
        calm = get_prescription(
            db_session, 2, "compound", extra_goals=["mental_health"]
        )
        assert calm == (3, "6-10", 7)
    finally:
        db_session.close()
