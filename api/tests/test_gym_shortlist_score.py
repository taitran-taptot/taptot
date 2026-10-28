"""Gym implement detection + shortlist scoring for loaded vs calisthenics."""

from app.services.workout_generation.gym_implements import has_gym_load, is_gym_load_slug
from app.services.workout_generation.shortlist import coerce_wizard_gen_equipment


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


def test_coerce_wizard_accepts_vietnamese_shop_slugs():
    assert coerce_wizard_gen_equipment(["ta-don"]) == ["dumbbell"]
    assert coerce_wizard_gen_equipment(["day-khang-luc"]) == ["resistance-band-2"]
    assert set(coerce_wizard_gen_equipment(["xa-don-va-vong-treo"])) == {
        "pull-up-bar",
        "gymnastic-rings",
    }
