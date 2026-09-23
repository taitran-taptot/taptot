"""Kit-aware challenge capacity: DB / knee / ring-row / pulldown cuts."""

from app.services.workout_generation.capacity import (
    capacity_test_scores,
    resolve_capacity,
)


def test_db_press_is_scored():
    scores = capacity_test_scores(
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
        kit="dumbbell",
        gender="male",
        weight_kg=70,
    )
    assert len(scores) >= 3
    assert all(s in (0, 1, 2) for s in scores)


def test_ten_ring_rows_not_as_strong_as_ten_pullups():
    row = capacity_test_scores(
        {
            "test_kit": "bar_rings",
            "pull_test_variant": "inverted_row",
            "inverted_rows_max": 10,
            "pushups_max": 12,
            "pushup_variant": "standard",
            "squats_max": 20,
            "plank_seconds": 40,
        },
        kit="bar_rings",
        gender="male",
    )
    pull = capacity_test_scores(
        {
            "test_kit": "bar_rings",
            "pull_test_variant": "strict",
            "pullups_max": 10,
            "pushups_max": 12,
            "pushup_variant": "standard",
            "squats_max": 20,
            "plank_seconds": 40,
        },
        kit="bar_rings",
        gender="male",
    )
    assert row[1] < pull[1]


def test_eight_knee_pushups_use_knee_cuts_not_pullup_cuts():
    knee = capacity_test_scores(
        {
            "test_kit": "bar_rings",
            "pushup_variant": "knee",
            "pushups_max": 8,
            "pull_test_variant": "inverted_row",
            "inverted_rows_max": 6,
            "squats_max": 15,
            "plank_seconds": 30,
        },
        kit="bar_rings",
        gender="male",
    )
    # 8 knee sits in the novice band (8, 20) → score 1, not the pull-up high cut.
    assert knee[0] == 1
    cap = resolve_capacity(
        2,
        {
            "test_kit": "bar_rings",
            "pushup_variant": "knee",
            "pushups_max": 8,
            "inverted_rows_max": 6,
            "pull_test_variant": "inverted_row",
            "squats_max": 15,
            "plank_seconds": 30,
        },
        gender="male",
    )
    assert "pullups_max" not in (
        {
            "test_kit": "bar_rings",
            "pushup_variant": "knee",
            "pushups_max": 8,
            "inverted_rows_max": 6,
        }
    )
    assert cap.tests_used >= 2


def test_pulldown_12_not_scored_as_pullup_12():
    down = capacity_test_scores(
        {
            "test_kit": "band",
            "pull_test_variant": "band_pulldown",
            "pullups_max": 12,
            "band_level": "medium",
            "pushups_max": 10,
            "pushup_variant": "standard",
            "squats_max": 20,
            "plank_seconds": 40,
        },
        kit="band",
        gender="male",
    )
    pull = capacity_test_scores(
        {
            "test_kit": "bar_rings",
            "pull_test_variant": "strict",
            "pullups_max": 12,
            "pushups_max": 10,
            "pushup_variant": "standard",
            "squats_max": 20,
            "plank_seconds": 40,
        },
        kit="bar_rings",
        gender="male",
    )
    assert down[1] < pull[1]


def test_resolve_capacity_does_not_write_fake_pullups_max():
    base = {
        "test_kit": "bar_rings",
        "pushup_variant": "knee",
        "pushups_max": 8,
        "pull_test_variant": "inverted_row",
        "inverted_rows_max": 10,
        "squats_max": 18,
        "plank_seconds": 35,
    }
    resolve_capacity(1, base, gender="female")
    assert "pullups_max" not in base or base.get("pullups_max") in (None, 0)


def test_bw_only_without_test_kit_keeps_legacy_keys():
    cap = resolve_capacity(
        2,
        {"pushups_max": 20, "squats_max": 30, "plank_seconds": 70, "pullups_max": 10},
    )
    assert cap.tests_used == 4
    assert cap.strength_tier == "strong"


def test_female_pullup_cuts_softer_than_male():
    female = capacity_test_scores(
        {
            "test_kit": "bar_rings",
            "pull_test_variant": "strict",
            "pullups_max": 5,
            "pushups_max": 8,
            "squats_max": 20,
            "plank_seconds": 40,
        },
        kit="bar_rings",
        gender="female",
    )
    male = capacity_test_scores(
        {
            "test_kit": "bar_rings",
            "pull_test_variant": "strict",
            "pullups_max": 5,
            "pushups_max": 8,
            "squats_max": 20,
            "plank_seconds": 40,
        },
        kit="bar_rings",
        gender="male",
    )
    # Female high cut is 5 so 5 pull-ups score 2; male high cut is 8 so 5 scores 1.
    assert female[1] > male[1]
