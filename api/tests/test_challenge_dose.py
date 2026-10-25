from types import SimpleNamespace

from app.services.workout_generation.challenge_dose import allocate_challenge_sets
from app.services.workout_generation.dose_bounds import dose_bounds_for_item


def test_allocate_challenge_sets_floors_and_caps_l1():
    day = SimpleNamespace(
        exercises=[
            SimpleNamespace(
                exercise_id=1, sets=1, section="main", notes_vi="ok", set_prescriptions=None
            ),
            SimpleNamespace(
                exercise_id=2, sets=5, section="main", notes_vi="ok", set_prescriptions=None
            ),
            SimpleNamespace(
                exercise_id=3, sets=3, section="cardio", notes_vi="ok", set_prescriptions=None
            ),
        ]
    )
    meta = {
        1: {"movement_role": "compound"},
        2: {"movement_role": "isolation"},
        3: {"movement_role": "cardio"},
    }
    allocate_challenge_sets([day], meta_by_id=meta, experience_level=1)
    assert day.exercises[0].sets == 2
    assert day.exercises[1].sets == 3
    assert day.exercises[2].sets == 3


def test_allocate_phase2_keeps_l1_test_lift_at_four():
    day = SimpleNamespace(
        exercises=[
            SimpleNamespace(
                exercise_id=1, sets=4, section="main", notes_vi="ok", set_prescriptions=None
            ),
            SimpleNamespace(
                exercise_id=2, sets=3, section="main", notes_vi="ok", set_prescriptions=None
            ),
        ]
    )
    allocate_challenge_sets(
        [day],
        meta_by_id={
            1: {"movement_role": "compound", "muscle_slug": "chest-mid"},
            2: {"movement_role": "isolation", "muscle_slug": "chest-mid"},
        },
        experience_level=1,
        phase_index=1,
    )
    assert day.exercises[0].sets == 4
    assert day.exercises[1].sets == 3


def test_allocate_challenge_sets_l2_cap_4():
    day = SimpleNamespace(
        exercises=[
            SimpleNamespace(
                exercise_id=1, sets=6, section="main", notes_vi="ok", set_prescriptions=None
            ),
        ]
    )
    allocate_challenge_sets(
        [day],
        meta_by_id={1: {"movement_role": "resistance"}},
        experience_level=2,
    )
    assert day.exercises[0].sets == 4


def test_challenge_compound_sets_max_l1():
    bounds = dose_bounds_for_item(
        {"movement_role": "compound", "name_en": "Goblet Squat"},
        experience_level=1,
        home_session=True,
        challenge=True,
    )
    assert bounds["sets_min"] == 2
    assert bounds["sets_max"] == 3


def test_challenge_compound_with_db_hints_does_not_nameerror():
    from app.services.workout_generation.load_estimate import apply_challenge_load

    loaded = apply_challenge_load(
        {"test_kit": "dumbbell", "db_press_reps": 12, "db_press_kg": 10},
        weight_kg=70,
        equipment_list=["dumbbell"],
    )
    bounds = dose_bounds_for_item(
        {
            "name_en": "Dumbbell Bench Press",
            "name_vi": "Đẩy ngực tạ đơn",
            "movement_role": "compound",
            "movement_pattern": "h_push",
            "equipment_slugs": ["dumbbell"],
        },
        experience_level=2,
        fitness_baseline=loaded,
        home_session=True,
        challenge=True,
    )
    assert bounds["work_mode"] == "reps"
    assert bounds.get("load_kg_each") == 10


def test_regular_plan_isolation_preset_unchanged():
    bounds = dose_bounds_for_item(
        {
            "name_vi": "Ép ngực tạ đơn",
            "name_en": "Dumbbell Fly",
            "movement_role": "isolation",
        },
        experience_level=2,
        fitness_baseline={"pushups_max": 20},
        home_session=True,
        challenge=False,
    )
    assert (bounds["reps_min"], bounds["reps_max"]) == (14, 18)
