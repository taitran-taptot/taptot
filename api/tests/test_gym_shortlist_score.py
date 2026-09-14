"""Gym implement detection + shortlist scoring for loaded vs calisthenics."""

from app.services.workout_generation.gym_implements import has_gym_load, is_gym_load_slug
from app.services.workout_generation.shortlist import score_candidate
from app.services.workout_generation.split_map import muscle_hints_for_split, patterns_for_split


def test_smith_and_barbell_are_gym_load():
    assert is_gym_load_slug("smith-machine")
    assert is_gym_load_slug("barbell")
    assert is_gym_load_slug("dumbbell")
    assert is_gym_load_slug("chest-press-machine")
    assert is_gym_load_slug("lying-leg-curl")
    assert is_gym_load_slug("seated-leg-curl")
    assert has_gym_load({"utility-bench", "smith-machine"})


def test_pike_gear_is_not_gym_load():
    assert not is_gym_load_slug("parallel-bars")
    assert not is_gym_load_slug("gymnastic-rings")
    assert not has_gym_load(set())
    assert not has_gym_load({"yoga-mat-exercise-mat"})


def _score(**over) -> int:
    kw = dict(
        pattern="h_push",
        muscle_slug="chest",
        difficulty=2,
        movement_role="compound",
        venue="both",
        equipment_slugs=set(),
        preferred_patterns=patterns_for_split("upper"),
        muscle_hints=muscle_hints_for_split("upper"),
        focus_slugs=None,
        allowed_diff=frozenset({1, 2}),
        experience_level=1,
        block_role="compound",
        block_key="compound",
        location="gym",
    )
    kw.update(over)
    return score_candidate(**kw)


def test_gym_upper_prefers_smith_and_db_over_pike():
    smith = _score(
        venue="gym",
        equipment_slugs={"smith-machine", "utility-bench"},
        muscle_slug="chest",
        pattern="h_push",
    )
    db_press = _score(
        pattern="v_push",
        muscle_slug="shoulders",
        venue="both",
        equipment_slugs={"dumbbell", "utility-bench"},
    )
    pike = _score(
        pattern="v_push",
        muscle_slug="shoulders",
        venue="home",
        equipment_slugs=set(),
    )
    assert smith > pike
    assert db_press > pike
