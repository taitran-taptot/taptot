from app.api.v1.ai import FitnessBaselineIn
from app.services.workout_generation.challenge_prompt import challenge_user_summary
from app.services.workout_generation.dose_bounds import dose_bounds_for_item
from app.services.workout_generation.load_estimate import (
    apply_challenge_load,
    epley_1rm,
    floor_from_knee_band,
    hint_for_item,
    working_8_10,
    working_rep_band,
    round_kg,
)


def test_epley_12x10kg_working_about_11kg():
    one_rm = epley_1rm(10, 12)
    assert abs(one_rm - 14.0) < 1e-9
    working = working_8_10(one_rm)
    assert round_kg(working) == 11


def test_dumbbell_brief_mentions_press_not_pullup():
    loaded = apply_challenge_load(
        {
            "test_kit": "dumbbell",
            "db_press_reps": 12,
            "db_press_kg": 10,
            "db_row_reps": 10,
            "db_row_kg": 12,
            "goblet_reps": 15,
            "goblet_kg": 16,
            "plank_seconds": 40,
        },
        weight_kg=70,
        gender="male",
        equipment_list=["dumbbell"],
    )
    brief = challenge_user_summary(
        {
            "goal": "lose_weight",
            "test_kit": loaded["test_kit"],
            "tests_vi": loaded["_tests_vi"],
            "fitness_baseline": loaded,
        }
    )
    assert "đẩy ngực tạ đơn" in brief
    assert "kéo xà" not in brief
    assert loaded["test_kit"] == "dumbbell"
    press_hint = next(h for h in loaded["_load_hints"] if h["pattern"] == "h_press")
    assert press_hint["load_kg_each"] == 11


def test_challenge_db_isolation_uses_test_band_not_8_12_preset():
    loaded = apply_challenge_load(
        {
            "test_kit": "dumbbell",
            "db_press_reps": 20,
            "db_press_kg": 10,
        },
        weight_kg=70,
        equipment_list=["dumbbell"],
    )
    item = {
        "name_vi": "Ép ngực tạ đơn",
        "name_en": "Dumbbell Fly",
        "movement_role": "isolation",
        "movement_pattern": "h_push",
    }
    challenge = dose_bounds_for_item(
        item,
        experience_level=2,
        fitness_baseline=loaded,
        home_session=True,
        challenge=True,
    )
    assert challenge["reps_min"] == 14
    assert challenge["reps_max"] == 16
    assert challenge.get("load_kg_each") == 7

    preset = dose_bounds_for_item(
        item,
        experience_level=2,
        fitness_baseline={"pushups_max": 20},
        home_session=True,
        challenge=False,
    )
    assert (preset["reps_min"], preset["reps_max"]) == (8, 12)


def test_bar_rings_brief_mentions_ring_row_not_pullup():
    loaded = apply_challenge_load(
        {
            "test_kit": "bar_rings",
            "pushups_max": 12,
            "pushup_variant": "standard",
            "pull_test_variant": "inverted_row",
            "inverted_rows_max": 8,
            "plank_seconds": 40,
        },
        weight_kg=70,
        gender="female",
        equipment_list=["pull-up-bar", "gymnastic-rings"],
    )
    brief = challenge_user_summary(
        {
            "goal": "lose_weight",
            "test_kit": loaded["test_kit"],
            "tests_vi": loaded["_tests_vi"],
            "fitness_baseline": loaded,
        }
    )
    assert "chèo vòng treo 8 cái" in brief
    assert "kéo người nằm" not in brief
    assert "kéo xà" not in brief


def test_fitness_baseline_in_accepts_kit_fields():
    row = FitnessBaselineIn(
        test_kit="dumbbell",
        db_press_reps=12,
        db_press_kg=10,
        goblet_reps=8,
        band_level=None,
    )
    dumped = row.model_dump()
    assert dumped["test_kit"] == "dumbbell"
    assert dumped["db_press_kg"] == 10
    assert dumped["db_press_reps"] == 12


def test_working_rep_band_beginner_is_60_75():
    assert working_rep_band(20) == (14, 16)
    assert working_rep_band(20, easy=True) == (12, 15)
    assert working_rep_band(10, easy=True) == (6, 7)


def test_floor_from_knee_band_not_seventy_percent():
    lo, hi = floor_from_knee_band(10)
    assert lo >= 3
    assert hi <= 6
    assert (lo, hi) != working_rep_band(10)
    assert (lo, hi) != working_rep_band(10, easy=True)


def test_inverted_row_hints_only_h_pull():
    loaded = apply_challenge_load(
        {
            "test_kit": "bar_rings",
            "pushups_max": 8,
            "pushup_variant": "knee",
            "pull_test_variant": "inverted_row",
            "inverted_rows_max": 10,
        },
        weight_kg=70,
        gender="female",
        equipment_list=["pull-up-bar", "gymnastic-rings"],
        easy=True,
    )
    patterns = {h["pattern"] for h in loaded["_load_hints"]}
    assert "h_pull" in patterns
    assert "v_pull" not in patterns
    assert "h_press_floor" in patterns
    pullup = hint_for_item(
        {"name_en": "Pull Ups", "name_vi": "Kéo xà", "movement_pattern": "v_pull"},
        loaded["_load_hints"],
    )
    assert pullup is None
    row = hint_for_item(
        {"name_en": "Ring Row", "name_vi": "Chèo vòng treo", "movement_pattern": "h_pull"},
        loaded["_load_hints"],
    )
    assert row is not None
    assert row["pattern"] == "h_pull"


def test_band_level_in_pulldown_hint():
    loaded = apply_challenge_load(
        {
            "test_kit": "band",
            "pushups_max": 10,
            "pullups_max": 12,
            "band_level": "light",
            "squats_max": 20,
        },
        equipment_list=["resistance-band"],
        easy=True,
    )
    pull = next(h for h in loaded["_load_hints"] if h["pattern"] == "v_pull")
    assert "dây" in pull["note_vi"]
    assert "nhẹ" in pull["note_vi"]

