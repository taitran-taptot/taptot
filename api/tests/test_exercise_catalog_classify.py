"""Tests for exercise venue / difficulty classifier + ensure migration."""

from sqlalchemy import create_engine, text

from app.core.migrations import ensure_exercise_venue_and_difficulty_v2
from app.services.exercise_catalog_classify import (
    classify_exercise,
    clamp_difficulty_1_4,
    difficulty_band_for_experience,
    roles_for_block,
    target_difficulty_for_experience,
    venues_for_location,
)


def test_clamp_difficulty_maps_5_to_4():
    assert clamp_difficulty_1_4(5) == 4
    assert clamp_difficulty_1_4(0) == 1
    assert clamp_difficulty_1_4(3) == 3


def test_experience_bands():
    assert difficulty_band_for_experience(1) == frozenset({1, 2})
    assert difficulty_band_for_experience(2) == frozenset({1, 2, 3})
    assert difficulty_band_for_experience(3) == frozenset({1, 2, 3, 4})
    assert target_difficulty_for_experience(1) == 2
    assert target_difficulty_for_experience(2) == 2
    assert target_difficulty_for_experience(3) == 3


def test_venues_for_location():
    assert venues_for_location("gym") == frozenset({"gym", "both"})
    assert venues_for_location("home") == frozenset({"home", "both"})
    assert venues_for_location("gym", no_equipment=True) == frozenset({"home", "both"})


def test_roles_for_block_home_expands_resistance():
    assert "resistance" in roles_for_block("compound", location="home")
    assert "compound" in roles_for_block("compound", location="home")
    assert roles_for_block("compound", location="gym") == frozenset({"compound"})


def test_classify_gym_machine():
    r = classify_exercise(
        {
            "name_en": "Leg Press",
            "name_vi": "Đạp chân máy",
            "exercise_type": "main",
            "movement_role": "compound",
            "difficulty": 3,
        },
        [{"slug": "leg-press", "name_en": "Leg Press Machine"}],
    )
    assert r.venue == "gym"
    assert r.movement_role == "compound"
    assert 1 <= r.difficulty <= 4


def test_classify_home_bodyweight_to_resistance():
    r = classify_exercise(
        {
            "name_en": "Push Up",
            "name_vi": "Chống đẩy",
            "exercise_type": "main",
            "movement_role": "compound",
            "difficulty": 2,
        },
        [],
    )
    # no equipment → both/home path; compound stays unless venue forced home-only
    assert r.venue in {"home", "both"}
    assert r.difficulty <= 4


def test_classify_home_only_maps_to_resistance():
    r = classify_exercise(
        {
            "name_en": "Home Floor Push Up",
            "name_vi": "Chống đẩy tại nhà",
            "exercise_type": "main",
            "movement_role": "compound",
            "difficulty": 2,
        },
        [{"slug": "bodyweight", "name_en": "Bodyweight"}],
    )
    assert r.venue == "home"
    assert r.movement_role == "resistance"


def test_classify_conditioning():
    r = classify_exercise(
        {
            "name_en": "Burpee",
            "name_vi": "Burpee",
            "exercise_type": "main",
            "movement_role": "compound",
            "difficulty": 3,
        },
        [],
    )
    assert r.movement_role == "conditioning"


def test_classify_advanced_skill():
    r = classify_exercise(
        {
            "name_en": "Muscle Up",
            "name_vi": "Hít xà nâng người",
            "exercise_type": "main",
            "difficulty": 2,
        },
        [{"slug": "pull-up-bar"}],
    )
    assert r.difficulty == 4


def test_ensure_venue_and_clamp_sqlite(tmp_path):
    db = tmp_path / "ex.db"
    engine = create_engine(f"sqlite:///{db}")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE exercises (
                    id INTEGER PRIMARY KEY,
                    name_vi TEXT NOT NULL,
                    difficulty INTEGER NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                "INSERT INTO exercises (id, name_vi, difficulty) VALUES "
                "(1, 'A', 5), (2, 'B', 2)"
            )
        )

    ensure_exercise_venue_and_difficulty_v2(engine)
    with engine.connect() as conn:
        rows = {
            r[0]: (r[1], r[2])
            for r in conn.execute(text("SELECT id, difficulty, venue FROM exercises"))
        }
        assert rows[1][0] == 4
        assert rows[1][1] == "both"
        assert rows[2][0] == 2
        assert rows[2][1] == "both"
