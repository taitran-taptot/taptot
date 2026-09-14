"""Equipment subset, session recipes, carb floor, and review swaps."""

from app.schemas.plans import PlanDayIn, PlanExerciseIn
from app.services.session_blocks import get_master_session_recipe
from app.services.workout_generation.coach_advice import (
    apply_duration_tweaks,
    apply_schedule_swaps,
)
from app.services.workout_generation.focus import focus_muscle_slugs
from app.services.workout_generation.nutrition_targets import estimate_targets
from app.services.workout_generation.session_duration import (
    clamp_session_to_target,
    estimate_day_minutes,
)
from app.services.workout_generation.session_templates import slots_for_session
from app.services.workout_generation.shortlist import (
    exercise_gear_allowed,
    expand_equipment_aliases,
    is_home_denied_exercise,
)
from app.services.workout_generation.weekly_volume import (
    _drop_duplicate_lifts,
    apply_weekly_dose,
    main_exercise_count,
    main_lift_floor,
)


def test_band_aliases_are_bidirectional():
    a = expand_equipment_aliases(["resistance-band-1"])
    b = expand_equipment_aliases(["resistance-band"])
    assert "resistance-band" in a
    assert "resistance-band-1" in b
    assert "resistance-band-2" in a


def test_expand_selected_equipment_unifies_band_family():
    from app.services.workout_generation.shortlist import expand_selected_equipment

    both = expand_selected_equipment(["dumbbell", "resistance-band"])
    assert both == ["dumbbell", "resistance-band-1", "resistance-band-2"]
    assert expand_selected_equipment(["resistance-band-1"]) == [
        "resistance-band-1",
        "resistance-band-2",
    ]
    assert expand_selected_equipment(["pull-up-bar"]) == ["pull-up-bar"]


def test_band_only_does_not_allow_bar_plus_band_move():
    user = expand_equipment_aliases(["resistance-band-1"])
    assert exercise_gear_allowed({"resistance-band"}, user)
    assert not exercise_gear_allowed({"pull-up-bar", "resistance-band"}, user)
    assert not exercise_gear_allowed({"pull-up-bar"}, user)
    assert exercise_gear_allowed(set(), user)


def test_bodyweight_and_bar_names():
    assert is_home_denied_exercise(
        name_en="Band-Assisted Pull-Up",
        location="home",
        no_equipment=False,
        user_slugs=["resistance-band-1"],
    )
    assert not is_home_denied_exercise(
        name_vi="Chống đẩy",
        location="home",
        no_equipment=False,
        user_slugs=["resistance-band-1"],
    )


def test_gym_60_lift_vs_cardio_core_recipes():
    lift = get_master_session_recipe(
        location="gym", session_minutes=60, split_role="push", experience_level=1
    )
    core = get_master_session_recipe(
        location="gym", session_minutes=60, split_role="core", experience_level=1
    )
    lift_cardio = [b for b in lift if b.block_key == "cardio"]
    assert len(lift_cardio) == 1
    assert lift_cardio[0].count_max == 1
    assert "nhẹ" in (lift_cardio[0].label_vi or "").lower()
    compounds = sum(b.count_max for b in lift if b.block_key == "compound")
    isolates = sum(b.count_max for b in lift if b.block_key == "accessory")
    assert compounds + isolates + 1 == 6
    core_work_cardio = sum(
        b.count_max for b in core if b.block_key in {"cardio", "conditioning"}
    )
    core_core = sum(b.count_max for b in core if b.block_key == "core")
    assert core_work_cardio == 1
    assert core_core == 2


def test_sedentary_cut_keeps_carb_floor():
    targets = estimate_targets(
        {
            "gender": "male",
            "weight_kg": 80,
            "height_cm": 175,
            "age": 30,
            "activity": "sedentary",
            "goal": "lose_weight",
            "kg_per_week": 0.8,
        }
    )
    assert targets is not None
    floor = min(80 * 1.5, 0.20 * targets.target_calories / 4)
    floor = max(floor, min(40.0, 0.15 * targets.target_calories / 4))
    assert targets.carbs_g + 0.15 >= floor
    assert targets.protein_g >= 80 * 1.6 - 0.15
    kcal = targets.protein_g * 4 + targets.carbs_g * 4 + targets.fat_g * 9
    assert abs(kcal - targets.target_calories) < 40


def test_apply_schedule_swaps_only_shortlist_ids():
    day = PlanDayIn(
        day_number=1,
        title_vi="Pull",
        split_role="pull",
        exercises=[
            PlanExerciseIn(exercise_id=10, sets=3, reps="10", rest_seconds=90, section="main"),
        ],
        meals=[],
    )
    apply_schedule_swaps(
        [day],
        [{"day_number": 1, "from_id": 10, "to_id": 99}],
        {1: {10, 11}},
    )
    assert day.exercises[0].exercise_id == 10
    apply_schedule_swaps(
        [day],
        [{"day_number": 1, "from_id": 10, "to_id": 11}],
        {1: {10, 11}},
    )
    assert day.exercises[0].exercise_id == 11


def test_apply_duration_tweaks_validates_rest_and_sets():
    day = PlanDayIn(
        day_number=1,
        split_role="push",
        exercises=[
            PlanExerciseIn(
                exercise_id=10, sets=3, reps="10", rest_seconds=180, section="main"
            ),
            PlanExerciseIn(
                exercise_id=20, sets=1, reps="12 phút", rest_seconds=0, section="cardio"
            ),
        ],
        meals=[],
    )
    apply_duration_tweaks(
        [day],
        [
            {"day_number": 1, "exercise_id": 10, "sets": 2, "rest_seconds": 90},
            {"day_number": 1, "exercise_id": 10, "sets": 9},
            {"day_number": 1, "exercise_id": 20, "reps": "8 phút"},
        ],
    )
    lift = day.exercises[0]
    assert lift.sets == 2
    assert lift.rest_seconds == 90
    assert day.exercises[1].reps == "8 phút"


def test_main_lift_floor_gym_60_and_cardio_core():
    assert main_lift_floor(60, "gym", "push") == 5
    assert main_lift_floor(60, "gym", "core") == 2
    assert main_lift_floor(45, "gym", "legs") == 4


def test_drop_duplicate_keeps_fly_and_pushdown():
    day = PlanDayIn(
        day_number=1,
        split_role="push",
        exercises=[
            PlanExerciseIn(exercise_id=1, sets=3, reps="10", rest_seconds=180, section="main"),
            PlanExerciseIn(exercise_id=2, sets=3, reps="10", rest_seconds=180, section="main"),
            PlanExerciseIn(exercise_id=3, sets=3, reps="12", rest_seconds=90, section="main"),
            PlanExerciseIn(exercise_id=4, sets=3, reps="12", rest_seconds=90, section="main"),
        ],
        meals=[],
    )
    meta = {
        1: {
            "movement_role": "compound",
            "movement_pattern": "h_push",
            "muscle_slug": "chest",
        },
        2: {
            "movement_role": "compound",
            "movement_pattern": "v_push",
            "muscle_slug": "shoulders",
        },
        3: {
            "movement_role": "isolation",
            "movement_pattern": "h_push",
            "muscle_slug": "chest",
        },
        4: {
            "movement_role": "isolation",
            "movement_pattern": "h_push",
            "muscle_slug": "triceps",
        },
    }
    _drop_duplicate_lifts([day], meta_by_id=meta, session_minutes=60)
    ids = [ex.exercise_id for ex in day.exercises if (ex.section or "main") == "main"]
    assert 3 in ids and 4 in ids


def test_drop_duplicate_compounds_same_pattern_and_step_up_stem():
    day = PlanDayIn(
        day_number=1,
        split_role="legs",
        exercises=[
            PlanExerciseIn(exercise_id=1, sets=3, reps="8", rest_seconds=180, section="main"),
            PlanExerciseIn(exercise_id=2, sets=3, reps="8", rest_seconds=180, section="main"),
            PlanExerciseIn(exercise_id=3, sets=3, reps="10", rest_seconds=90, section="main"),
        ],
        meals=[],
    )
    meta = {
        1: {
            "movement_role": "compound",
            "movement_pattern": "squat",
            "muscle_slug": "quads",
            "name_vi": "Bước lên mục tạ đòn",
        },
        2: {
            "movement_role": "compound",
            "movement_pattern": "squat",
            "muscle_slug": "quads",
            "name_vi": "Bước lên hộp tạ đòn",
        },
        3: {
            "movement_role": "compound",
            "movement_pattern": "hinge",
            "muscle_slug": "hamstrings",
            "name_vi": "Deadlift Romania",
        },
    }
    _drop_duplicate_lifts([day], meta_by_id=meta, session_minutes=60)
    ids = [ex.exercise_id for ex in day.exercises if (ex.section or "main") == "main"]
    assert ids.count(1) + ids.count(2) == 1
    assert 3 in ids


def test_lppl_dose_keeps_push_equal_to_other_lift_days():
    meta = {
        1: {"movement_role": "compound", "movement_pattern": "squat", "muscle_slug": "quads"},
        2: {"movement_role": "compound", "movement_pattern": "hinge", "muscle_slug": "hamstrings"},
        3: {"movement_role": "isolation", "movement_pattern": "squat", "muscle_slug": "quads"},
        4: {"movement_role": "isolation", "movement_pattern": "hinge", "muscle_slug": "glutes"},
        5: {"movement_role": "isolation", "movement_pattern": "other", "muscle_slug": "calves"},
        10: {"movement_role": "compound", "movement_pattern": "h_push", "muscle_slug": "chest"},
        11: {"movement_role": "compound", "movement_pattern": "v_push", "muscle_slug": "shoulders"},
        12: {"movement_role": "isolation", "movement_pattern": "other", "muscle_slug": "chest"},
        13: {"movement_role": "isolation", "movement_pattern": "other", "muscle_slug": "shoulders"},
        14: {"movement_role": "isolation", "movement_pattern": "h_push", "muscle_slug": "triceps"},
        20: {"movement_role": "compound", "movement_pattern": "v_pull", "muscle_slug": "back"},
        21: {"movement_role": "compound", "movement_pattern": "h_pull", "muscle_slug": "back"},
        22: {"movement_role": "isolation", "movement_pattern": "h_pull", "muscle_slug": "back"},
        23: {"movement_role": "isolation", "movement_pattern": "other", "muscle_slug": "biceps"},
        24: {"movement_role": "isolation", "movement_pattern": "other", "muscle_slug": "shoulders"},
        30: {"movement_role": "compound", "movement_pattern": "squat", "muscle_slug": "quads"},
        31: {"movement_role": "compound", "movement_pattern": "hinge", "muscle_slug": "hamstrings"},
        32: {"movement_role": "isolation", "movement_pattern": "squat", "muscle_slug": "quads"},
        33: {"movement_role": "isolation", "movement_pattern": "hinge", "muscle_slug": "glutes"},
        34: {"movement_role": "isolation", "movement_pattern": "other", "muscle_slug": "calves"},
    }

    def day(role: str, eids: list[int]) -> PlanDayIn:
        return PlanDayIn(
            day_number=1,
            split_role=role,
            exercises=[
                PlanExerciseIn(
                    exercise_id=i, sets=3, reps="10", rest_seconds=90, section="main"
                )
                for i in eids
            ],
            meals=[],
        )

    days = [
        day("legs", [1, 2, 3, 4, 5]),
        day("push", [10, 11, 12, 13, 14]),
        day("pull", [20, 21, 22, 23, 24]),
        day("legs", [30, 31, 32, 33, 34]),
    ]
    out, _note = apply_weekly_dose(
        days,
        meta_by_id=meta,
        effective_level=1,
        session_minutes=60,
        location="gym",
    )
    counts = [main_exercise_count(d) for d in out]
    assert counts[1] == counts[0]
    assert counts[1] == 5


def test_focus_chan_not_injected_on_push():
    focus = focus_muscle_slugs(["chan", "eo"])
    push = slots_for_session(
        "push", compound_n=2, accessory_n=3, location="gym", focus_slugs=focus
    )
    assert all(s.key != "focus_iso" for s in push)
    legs = slots_for_session(
        "legs", compound_n=2, accessory_n=3, location="gym", focus_slugs=focus
    )
    assert any(s.key == "focus_iso" for s in legs)


def test_cardio_core_recipe_one_cardio_and_clamp():
    core = get_master_session_recipe(
        location="gym", session_minutes=60, split_role="core", experience_level=1
    )
    cardio_n = sum(b.count_max for b in core if b.block_key in {"cardio", "conditioning"})
    assert cardio_n == 1
    day = PlanDayIn(
        day_number=1,
        split_role="core",
        exercises=[
            PlanExerciseIn(
                exercise_id=1, sets=1, reps="5 phút", rest_seconds=30, section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=2, sets=1, reps="35 phút", rest_seconds=0, section="cardio"
            ),
            PlanExerciseIn(
                exercise_id=3, sets=3, reps="15", rest_seconds=90, section="main"
            ),
            PlanExerciseIn(
                exercise_id=4, sets=3, reps="15", rest_seconds=90, section="main"
            ),
            PlanExerciseIn(
                exercise_id=5, sets=1, reps="5 phút", rest_seconds=30, section="cooldown"
            ),
        ],
        meals=[],
    )
    meta = {
        2: {"movement_role": "cardio", "muscle_slug": "core"},
        3: {"movement_role": "isolation", "muscle_slug": "core"},
        4: {"movement_role": "isolation", "muscle_slug": "core"},
    }
    out = clamp_session_to_target(
        [day], session_minutes=60, meta_by_id=meta, location="gym"
    )[0]
    assert estimate_day_minutes(out) <= 60
    cardio = [e for e in out.exercises if (e.section or "") == "cardio"]
    assert len(cardio) == 1


def test_upper_denies_glute_muscle():
    from app.services.workout_generation.split_map import is_denied_for_split

    assert is_denied_for_split("upper", muscle_slug="glutes")
    assert is_denied_for_split("push", muscle_slug="co-mong")
    assert is_denied_for_split("pull", muscle_slug="glutes")
    assert not is_denied_for_split("legs", muscle_slug="glutes")
    assert is_denied_for_split("push", muscle_slug="biceps")
    assert is_denied_for_split("push", muscle_slug="co-tay-truoc")
    assert not is_denied_for_split("pull", muscle_slug="biceps")
    assert is_denied_for_split("pull", muscle_slug="triceps")
    assert is_denied_for_split("push", muscle_slug="shoulders-rear")
    assert is_denied_for_split("push", muscle_slug="back-lats")
    assert is_denied_for_split("push", muscle_slug="back-middle")
    assert is_denied_for_split("pull", muscle_slug="chest")
    assert is_denied_for_split("pull", muscle_slug="chest-upper")
    assert not is_denied_for_split("pull", muscle_slug="shoulders-rear")


def test_drop_hip_abduction_from_upper_day():
    from app.services.workout_generation.weekly_volume import _drop_denied_split_leaks

    day = PlanDayIn(
        day_number=1,
        split_role="upper",
        exercises=[
            PlanExerciseIn(
                exercise_id=1, sets=3, reps="8", rest_seconds=120, section="main"
            ),
            PlanExerciseIn(
                exercise_id=99, sets=3, reps="12", rest_seconds=60, section="main"
            ),
        ],
        meals=[],
    )
    meta = {
        1: {
            "movement_role": "compound",
            "movement_pattern": "h_push",
            "muscle_slug": "chest",
            "name_vi": "Bench",
        },
        99: {
            "movement_role": "isolation",
            "movement_pattern": "other",
            "muscle_slug": "glutes",
            "name_vi": "Dạng hông",
            "name_en": "Bodyweight Hip Abduction",
        },
    }
    _drop_denied_split_leaks([day], meta_by_id=meta)
    assert [e.exercise_id for e in day.exercises] == [1]


def test_drop_biceps_curl_from_push_day():
    from app.services.workout_generation.weekly_volume import _drop_denied_split_leaks

    day = PlanDayIn(
        day_number=1,
        split_role="push",
        exercises=[
            PlanExerciseIn(
                exercise_id=1, sets=3, reps="8", rest_seconds=120, section="main"
            ),
            PlanExerciseIn(
                exercise_id=50, sets=3, reps="12", rest_seconds=60, section="main"
            ),
        ],
        meals=[],
    )
    meta = {
        1: {
            "movement_role": "compound",
            "movement_pattern": "h_push",
            "muscle_slug": "chest",
            "name_vi": "Chống đẩy",
        },
        50: {
            "movement_role": "isolation",
            "movement_pattern": "other",
            "muscle_slug": "biceps",
            "name_vi": "Cuốn tay với dây",
            "name_en": "Band Curl",
        },
    }
    _drop_denied_split_leaks([day], meta_by_id=meta)
    assert [e.exercise_id for e in day.exercises] == [1]


def test_drop_rear_delt_and_back_from_push_day():
    from app.services.workout_generation.weekly_volume import _drop_denied_split_leaks

    day = PlanDayIn(
        day_number=1,
        split_role="push",
        exercises=[
            PlanExerciseIn(
                exercise_id=1, sets=3, reps="8", rest_seconds=120, section="main"
            ),
            PlanExerciseIn(
                exercise_id=842, sets=3, reps="12", rest_seconds=60, section="main"
            ),
            PlanExerciseIn(
                exercise_id=843, sets=3, reps="12", rest_seconds=60, section="main"
            ),
            PlanExerciseIn(
                exercise_id=200, sets=3, reps="10", rest_seconds=90, section="main"
            ),
        ],
        meals=[],
    )
    meta = {
        1: {
            "movement_role": "compound",
            "movement_pattern": "h_push",
            "muscle_slug": "chest",
            "name_vi": "Chống đẩy",
        },
        842: {
            "movement_role": "isolation",
            "movement_pattern": "other",
            "muscle_slug": "shoulders-rear",
            "name_vi": "Face pull vòng treo",
            "name_en": "Ring Face Pull",
        },
        843: {
            "movement_role": "isolation",
            "movement_pattern": "h_pull",
            "muscle_slug": "shoulders-rear",
            "name_vi": "Bay vai sau vòng treo",
            "name_en": "Ring Rear Delt Fly",
        },
        200: {
            "movement_role": "compound",
            "movement_pattern": "other",
            "muscle_slug": "back-middle",
            "name_vi": "Row sai tag",
            "name_en": "Mis-tagged Row",
        },
    }
    _drop_denied_split_leaks([day], meta_by_id=meta)
    assert [e.exercise_id for e in day.exercises] == [1]


def test_prefer_knee_pushups_only_home_no_equip_weak():
    from app.services.workout_generation.weekly_volume import prefer_knee_pushups

    assert prefer_knee_pushups(location="home", no_equipment=True, pushups_max=0)
    assert prefer_knee_pushups(location="home", no_equipment=True, pushups_max=3)
    assert not prefer_knee_pushups(location="home", no_equipment=True, pushups_max=8)
    assert not prefer_knee_pushups(location="gym", no_equipment=True, pushups_max=0)
    assert not prefer_knee_pushups(location="home", no_equipment=False, pushups_max=0)
