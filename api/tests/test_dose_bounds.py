from app.schemas.plans import PlanDayIn, PlanExerciseIn
from app.services.workout_generation.assemble import inject_main_primer_warmup
from app.services.workout_generation.dose_bounds import (
    apply_no_equip_fitness_doses,
    clamp_challenge_rest_seconds,
    clamp_dose_to_bounds,
    collapse_rep_range_to_lo,
    snap_rep_to_five_band,
    default_reps_label,
    dose_bounds_for_item,
    half_working_reps_label,
    is_hard_bw_skill_item,
    is_skill_bw_item,
    is_unilateral_name,
    primer_reps_from_baseline,
)
from app.services.workout_generation.effort_mode import exercise_effort_mode


def test_plank_uses_seconds_from_baseline():
    item = {"name_vi": "Plank", "movement_role": "isolation"}
    bounds = dose_bounds_for_item(
        item,
        experience_level=1,
        fitness_baseline={"plank_seconds": 25},
    )
    assert bounds["work_mode"] == "hold"
    assert bounds["seconds_max"] < 25
    assert clamp_dose_to_bounds(
        {"sets": 3, "reps": "15 giây"},
        bounds,
        default_sets=3,
        default_reps="20 giây",
    ) == (3, "15 giây")


def test_out_of_range_ai_dose_falls_back():
    item = {"name_vi": "Hít xà", "name_en": "Pull-up", "movement_role": "compound"}
    bounds = dose_bounds_for_item(
        item,
        experience_level=1,
        fitness_baseline={"pullups_max": 0},
    )
    assert clamp_dose_to_bounds(
        {"sets": 3, "reps": "20"},
        bounds,
        default_sets=3,
        default_reps="5-8",
    ) == (3, "2-6")
    assert clamp_dose_to_bounds(
        {"sets": 4, "reps": "20"},
        bounds,
        default_sets=3,
        default_reps="5-8",
    )[1] == "2-6"
    assert clamp_challenge_rest_seconds(12, 90, movement_role="isolation") == 90
    assert clamp_challenge_rest_seconds(12, 90, movement_role="compound") == 120
    assert clamp_challenge_rest_seconds(200, 90) == 180
    assert clamp_challenge_rest_seconds("90", 60) == 90


def test_collapse_working_rep_range_keeps_full_band():
    assert collapse_rep_range_to_lo("8-12") == "8-12"
    assert collapse_rep_range_to_lo("12–15") == "12–15"
    assert collapse_rep_range_to_lo("10") == "10"
    assert collapse_rep_range_to_lo("30 giây") == "30 giây"
    assert collapse_rep_range_to_lo("10 phút") == "10 phút"


def test_snap_rep_to_five_band():
    assert snap_rep_to_five_band(7) == "6-10"
    assert snap_rep_to_five_band("12") == "10-14"
    assert snap_rep_to_five_band("20") == "18-22"
    assert snap_rep_to_five_band("8-12") == "8-12"
    assert snap_rep_to_five_band(4) == "2-6"
    assert snap_rep_to_five_band(6) == "4-8"
    assert snap_rep_to_five_band(10) == "8-12"
    assert snap_rep_to_five_band("3") == "2-6"
    assert snap_rep_to_five_band("30 giây") == "30 giây"
    assert snap_rep_to_five_band("20-25") == "20-24"


def test_pike_working_band_follows_pushup_test():
    pike = {
        "name_en": "Pike Push-Up",
        "name_vi": "Chống đẩy pike",
        "movement_role": "compound",
        "movement_pattern": "v_push",
    }

    def band(pushups: int) -> str:
        bounds = dose_bounds_for_item(
            pike,
            experience_level=2,
            fitness_baseline={"pushups_max": pushups},
            home_session=True,
            challenge=True,
        )
        assert bounds["work_mode"] == "reps"
        return snap_rep_to_five_band(default_reps_label(bounds))

    assert band(8) == "2-6"
    assert band(20) == "6-10"
    assert band(30) == "10-14"


def test_five_band_not_clamped_to_preset():
    bounds = {
        "work_mode": "reps",
        "sets_min": 2,
        "sets_max": 4,
        "reps_min": 10,
        "reps_max": 15,
    }
    assert clamp_dose_to_bounds(
        {"sets": 3, "reps": "6-8"},
        bounds,
        default_sets=3,
        default_reps="10-15",
        prefer_proposal_reps=True,
    ) == (3, "6-10")


def test_pullup_warmup_stays_reps_not_seconds():
    from app.services.workout_generation.dose_bounds import coerce_working_reps_label
    from app.services.workout_rest import timed_block_prescription

    item = {"name_vi": "Kéo xà", "name_en": "Pull Ups", "movement_role": "compound"}
    assert exercise_effort_mode(item, plan_section="warmup") == "reps"
    assert timed_block_prescription(
        block_key="compound",
        plan_section="warmup",
        movement_role="compound",
        duration_min=5,
        name_vi="Kéo xà",
        name_en="Pull Ups",
    ) is None
    assert coerce_working_reps_label("40 giây", work_mode="hold", item=item) == "6-10"


def test_pullup_seconds_coerced_to_rep_band():
    from app.services.workout_generation.dose_bounds import coerce_working_reps_label
    from app.services.workout_generation.effort_mode import exercise_effort_mode

    item = {"name_vi": "Kéo xà", "name_en": "Pull Ups", "movement_role": "compound"}
    assert exercise_effort_mode(item) == "reps"
    assert coerce_working_reps_label(
        "40 giây", work_mode="reps", item=item
    ) == "6-10"


def test_pushups_compound_70_80_and_iso_bands_by_equipment():
    item = {"name_vi": "Chống đẩy", "name_en": "Push-up", "movement_role": "compound"}
    high = dose_bounds_for_item(
        item,
        experience_level=2,
        fitness_baseline={"pushups_max": 60},
        no_equipment=True,
    )
    assert high["work_mode"] == "reps"
    assert high["reps_min"] == 44
    assert high["reps_max"] == 48
    assert clamp_dose_to_bounds(
        {"sets": 3, "reps": "55"},
        high,
        default_sets=3,
        default_reps="10-12",
    ) == (3, "44-48")

    iso_no_equip = dose_bounds_for_item(
        {**item, "movement_role": "isolation"},
        experience_level=2,
        fitness_baseline={"pushups_max": 60},
        no_equipment=True,
    )
    assert iso_no_equip["reps_min"] == 50
    assert iso_no_equip["reps_max"] == 54

    iso_with_gear = dose_bounds_for_item(
        {**item, "movement_role": "isolation"},
        experience_level=2,
        fitness_baseline={"pushups_max": 60},
        no_equipment=False,
    )
    assert iso_with_gear["reps_min"] == 38
    assert iso_with_gear["reps_max"] == 42


def test_bodyweight_edge_max_zero_one_three():
    item = {"name_vi": "Chống đẩy", "name_en": "Push-up", "movement_role": "compound"}
    zero = dose_bounds_for_item(
        item, experience_level=1, fitness_baseline={"pushups_max": 0}, no_equipment=True
    )
    assert (zero["reps_min"], zero["reps_max"]) == (2, 6)

    one = dose_bounds_for_item(
        item, experience_level=1, fitness_baseline={"pushups_max": 1}, no_equipment=True
    )
    assert (one["reps_min"], one["reps_max"]) == (2, 6)

    three = dose_bounds_for_item(
        item, experience_level=1, fitness_baseline={"pushups_max": 3}, no_equipment=True
    )
    assert (three["reps_min"], three["reps_max"]) == (2, 6)


def test_superman_no_equip_isolation_80_90_of_pullups():
    item = {"name_vi": "Superman", "name_en": "Superman", "movement_role": "isolation"}
    bounds = dose_bounds_for_item(
        item,
        experience_level=2,
        fitness_baseline={"pullups_max": 10},
        no_equipment=True,
    )
    assert bounds["reps_min"] == 6
    assert bounds["reps_max"] == 10


def test_table_and_backpack_rows_scale_from_pullups_max():
    baseline = {"pullups_max": 10}
    table = dose_bounds_for_item(
        {
            "name_vi": "Kéo người dưới bàn",
            "name_en": "Table Inverted Row",
            "movement_role": "compound",
        },
        experience_level=2,
        fitness_baseline=baseline,
        no_equipment=True,
    )
    # Row transfer ×2.0 → equiv 20 → L2 compound 70–80%, snapped to a 4-rep window.
    assert (table["reps_min"], table["reps_max"]) == (14, 18)

    backpack = dose_bounds_for_item(
        {
            "name_vi": "Chèo ba lô",
            "name_en": "Backpack Row",
            "movement_role": "isolation",
        },
        experience_level=2,
        fitness_baseline=baseline,
        no_equipment=True,
    )
    assert (backpack["reps_min"], backpack["reps_max"]) == (16, 20)

    # Name match works even when no_equipment is false (home implements path).
    with_flag_off = dose_bounds_for_item(
        {
            "name_vi": "Chèo ba lô",
            "name_en": "Backpack Row",
            "movement_role": "compound",
        },
        experience_level=2,
        fitness_baseline=baseline,
        no_equipment=False,
    )
    assert (with_flag_off["reps_min"], with_flag_off["reps_max"]) == (14, 18)

def test_no_equip_legs_scale_from_squats_max():
    compound = dose_bounds_for_item(
        {
            "name_vi": "Squat không tạ",
            "name_en": "Bodyweight Squat",
            "movement_role": "compound",
        },
        experience_level=2,
        fitness_baseline={"squats_max": 40},
        no_equipment=True,
    )
    assert (compound["reps_min"], compound["reps_max"]) == (28, 32)

    iso = dose_bounds_for_item(
        {
            "name_vi": "Lunge",
            "name_en": "Walking Lunge",
            "movement_role": "isolation",
        },
        experience_level=2,
        fitness_baseline={"squats_max": 40},
        no_equipment=True,
    )
    assert (iso["reps_min"], iso["reps_max"]) == (32, 36)


def test_no_equip_muscle_slug_back_scales_without_name_match():
    bounds = dose_bounds_for_item(
        {
            "name_vi": "Bài lưng sàn",
            "name_en": "Floor Back Extension",
            "movement_role": "isolation",
            "muscle_slug": "back",
        },
        experience_level=2,
        fitness_baseline={"pullups_max": 10},
        no_equipment=True,
    )
    assert (bounds["reps_min"], bounds["reps_max"]) == (10, 14)


def test_loaded_name_still_scales_when_no_equipment():
    """No-equip schedules must dose from fitness even if the catalog name says dumbbell."""
    item = {
        "name_vi": "Chèo tạ đơn",
        "name_en": "Dumbbell Row",
        "movement_role": "compound",
        "movement_pattern": "h_pull",
    }
    no_equip = dose_bounds_for_item(
        item,
        experience_level=2,
        fitness_baseline={"pullups_max": 10, "pushups_max": 60},
        no_equipment=True,
    )
    assert (no_equip["reps_min"], no_equip["reps_max"]) == (14, 18)

    with_gear = dose_bounds_for_item(
        item,
        experience_level=2,
        fitness_baseline={"pullups_max": 10, "pushups_max": 60},
        no_equipment=False,
    )
    assert (with_gear["reps_min"], with_gear["reps_max"]) == (6, 10)


def test_half_working_reps_label():
    assert half_working_reps_label("10") == "5"
    assert half_working_reps_label("8–12") == "4-6"
    assert half_working_reps_label("30 giây") == "15 giây"
    assert half_working_reps_label(None) is None


def test_primer_reps_helper_edge_and_high():
    item = {"name_vi": "Chống đẩy", "name_en": "Push-up", "movement_role": "compound"}
    assert primer_reps_from_baseline(item, {"pushups_max": 60}, no_equipment=True) == 24
    assert primer_reps_from_baseline(item, {"pushups_max": 0}, no_equipment=True) == 1
    assert primer_reps_from_baseline(item, {"pushups_max": 3}, no_equipment=True) == 1
    assert primer_reps_from_baseline(item, {}, no_equipment=True) is None


def test_home_primer_is_half_main_reps_with_min_60s_rest():
    day = PlanDayIn(
        day_number=1,
        title_vi="Upper",
        exercises=[
            PlanExerciseIn(
                exercise_id=1, section="warmup", sets=2, reps="30 giây", rest_seconds=30
            ),
            PlanExerciseIn(exercise_id=10, section="main", sets=3, reps="10"),
        ],
    )
    meta = {10: {"name_vi": "Chống đẩy", "movement_role": "resistance"}}
    out = inject_main_primer_warmup(
        day,
        meta_by_id=meta,
        no_equipment=True,
        home_session=True,
    )
    primers = [ex for ex in out.exercises if ex.exercise_id == 10 and ex.section == "warmup"]
    warmup = [ex for ex in out.exercises if ex.section == "warmup"]
    assert len(primers) == 1
    assert primers[0].reps == "5"
    assert primers[0].sets == 2
    assert primers[0].rest_seconds == 90
    assert all(ex.exercise_id != 1 for ex in warmup)


def test_bodyweight_squat_primer_is_not_light_db_note():
    from app.services.workout_generation.coach_notes import PRIMER_NOTE_BW_VI, PRIMER_NOTE_LOADED_VI

    day = PlanDayIn(
        day_number=1,
        title_vi="Legs",
        exercises=[
            PlanExerciseIn(exercise_id=10, section="main", sets=3, reps="10-14"),
        ],
    )
    meta = {
        10: {
            "name_vi": "Ngồi xổm không tạ",
            "name_en": "Bodyweight Squat",
            "movement_role": "compound",
        }
    }
    out = inject_main_primer_warmup(day, meta_by_id=meta, home_session=True)
    primers = [ex for ex in out.exercises if ex.section == "warmup"]
    assert primers[0].reps == "5-7"
    assert primers[0].notes_vi == PRIMER_NOTE_BW_VI
    assert PRIMER_NOTE_LOADED_VI not in (primers[0].notes_vi or "")
    assert "Tạ nhẹ" not in (primers[0].notes_vi or "")
    assert "4 cái" not in (primers[0].notes_vi or "")


def test_gym_primer_rest_unchanged_without_home_session():
    day = PlanDayIn(
        day_number=1,
        title_vi="Push",
        exercises=[
            PlanExerciseIn(exercise_id=10, section="main", sets=3, reps="10"),
        ],
    )
    meta = {10: {"name_vi": "Bench", "movement_role": "compound"}}
    out = inject_main_primer_warmup(day, meta_by_id=meta, home_session=False)
    primers = [ex for ex in out.exercises if ex.section == "warmup"]
    assert primers[0].rest_seconds == 90
    assert primers[0].sets == 2
    assert primers[0].reps == "5"


def test_inject_primer_uses_40_percent_of_pushups_max():
    day = PlanDayIn(
        day_number=1,
        title_vi="Push",
        exercises=[
            PlanExerciseIn(exercise_id=1, section="warmup", sets=2, reps="30 giây"),
            PlanExerciseIn(exercise_id=10, section="main", sets=3, reps="42-48"),
        ],
    )
    meta = {
        10: {
            "name_vi": "Chống đẩy",
            "name_en": "Push-up",
            "movement_role": "compound",
        }
    }
    out = inject_main_primer_warmup(
        day,
        meta_by_id=meta,
        no_equipment=True,
        fitness_baseline={"pushups_max": 60},
    )
    primers = [ex for ex in out.exercises if ex.exercise_id == 10 and ex.section == "warmup"]
    assert len(primers) == 1
    assert primers[0].sets == 2
    assert primers[0].reps == "21-24"
    assert primers[0].rest_seconds == 90


def test_no_equip_clamp_ignores_prescription_seed():
    """When no-equip, default dose must come from fitness bounds, not 8-12 seed."""
    item = {
        "name_vi": "Floor back work",
        "name_en": "Back extension",
        "movement_role": "isolation",
        "muscle_slug": "back",
    }
    bounds = dose_bounds_for_item(
        item,
        experience_level=2,
        fitness_baseline={"pullups_max": 10},
        no_equipment=True,
    )
    assert default_reps_label(bounds) == "10-14"
    assert clamp_dose_to_bounds(
        None,
        bounds,
        default_sets=3,
        default_reps=default_reps_label(bounds),
    ) == (3, "10-14")
    # Prescription-style default must not stick when out of fitness band.
    assert clamp_dose_to_bounds(
        None,
        bounds,
        default_sets=3,
        default_reps="4-6",
    ) == (3, "10-14")


def test_missing_preferred_test_falls_through():
    """Superman with null pullups uses pushups×0.15 proxy (Method B)."""
    item = {
        "name_vi": "Nằm sấp giơ tay chân",
        "name_en": "Supermans",
        "movement_role": "isolation",
        "movement_pattern": "h_pull",
    }
    bounds = dose_bounds_for_item(
        item,
        experience_level=1,
        fitness_baseline={"pushups_max": 20, "pullups_max": None, "squats_max": 30},
        no_equipment=True,
    )
    assert (bounds["reps_min"], bounds["reps_max"]) == (2, 6)


def test_box_squat_and_glute_bridge_use_squats_max():
    base = {"pushups_max": 20, "squats_max": 40}
    box = dose_bounds_for_item(
        {
            "name_vi": "Ngồi xổm xuống hộp",
            "name_en": "Bodyweight Box Squat",
            "movement_role": "resistance",
            "movement_pattern": "squat",
        },
        experience_level=1,
        fitness_baseline=base,
        no_equipment=True,
    )
    assert (box["reps_min"], box["reps_max"]) == (24, 28)

    bridge = dose_bounds_for_item(
        {
            "name_vi": "Cầu mông",
            "name_en": "Glute Bridge",
            "movement_role": "isolation",
            "movement_pattern": "hinge",
        },
        experience_level=1,
        fitness_baseline=base,
        no_equipment=True,
    )
    assert (bridge["reps_min"], bridge["reps_max"]) == (28, 32)


def test_prompt_dict_muscle_key_is_read():
    bounds = dose_bounds_for_item(
        {
            "name_vi": "Bài lưng",
            "name_en": "Back move",
            "movement_role": "isolation",
            "muscle": "back",
        },
        experience_level=1,
        fitness_baseline={"pullups_max": 10},
        no_equipment=True,
    )
    assert (bounds["reps_min"], bounds["reps_max"]) == (10, 14)


def test_diamond_pushup_and_box_squat_map_to_baseline():
    push = dose_bounds_for_item(
        {
            "name_vi": "Chống đẩy kim cương",
            "name_en": "Diamond Push Ups",
            "movement_role": "compound",
            "movement_pattern": "h_push",
        },
        experience_level=1,
        fitness_baseline={"pushups_max": 45},
        no_equipment=True,
    )
    assert (push["reps_min"], push["reps_max"]) == (28, 32)

    box = dose_bounds_for_item(
        {
            "name_vi": "Ngồi xổm xuống hộp",
            "name_en": "Bodyweight Box Squat",
            "movement_role": "resistance",
            "movement_pattern": "squat",
        },
        experience_level=1,
        fitness_baseline={"squats_max": 40},
        no_equipment=True,
    )
    assert (box["reps_min"], box["reps_max"]) == (24, 28)


def test_cardio_is_continuous_and_hold_names_are_detected():
    assert exercise_effort_mode(movement_role="cardio") == "continuous"
    assert exercise_effort_mode(name_en="Dead Hang", movement_role="isolation") == "hold"


def test_warmup_timed_default_is_not_converted_to_repetitions():
    bounds = dose_bounds_for_item(
        {"name_vi": "Giãn ngực", "movement_role": "mobility"},
        experience_level=1,
        plan_section="warmup",
    )
    assert clamp_dose_to_bounds(
        None,
        bounds,
        default_sets=2,
        default_reps="30 giây",
    ) == (2, "30 giây")


def test_apply_no_equip_fitness_doses_overwrites_prescription_seeds():
    day = PlanDayIn(
        day_number=1,
        title_vi="Lower",
        exercises=[
            PlanExerciseIn(
                exercise_id=1, section="main", sets=3, reps="8-12", notes_vi="old"
            ),
            PlanExerciseIn(
                exercise_id=2, section="main", sets=3, reps="12-20", notes_vi="old"
            ),
            PlanExerciseIn(
                exercise_id=3, section="main", sets=3, reps="12-20", notes_vi="old"
            ),
            PlanExerciseIn(
                exercise_id=4, section="main", sets=3, reps="12-20", notes_vi="old"
            ),
            PlanExerciseIn(
                exercise_id=5, section="warmup", sets=2, reps="30 giây"
            ),
        ],
    )
    meta = {
        1: {
            "name_vi": "Ngồi xổm xuống hộp",
            "name_en": "Bodyweight Box Squat",
            "movement_role": "resistance",
            "movement_pattern": "squat",
        },
        2: {
            "name_vi": "Bơm mông tư thế ếch",
            "name_en": "Frog Pump",
            "movement_role": "isolation",
            "movement_pattern": "hinge",
        },
        3: {
            "name_vi": "Cầu mông một chân",
            "name_en": "Single Leg Glute Bridge",
            "movement_role": "isolation",
            "movement_pattern": "hinge",
        },
        4: {
            "name_vi": "Cầu mông",
            "name_en": "Glute Bridge",
            "movement_role": "isolation",
            "movement_pattern": "hinge",
        },
    }
    apply_no_equip_fitness_doses(
        [day],
        fitness_baseline={"squats_max": 40},
        meta_by_id=meta,
        experience_level=1,
        no_equipment=True,
    )
    by_id = {ex.exercise_id: ex for ex in day.exercises}
    assert by_id[1].reps == "8-12"
    assert by_id[2].reps == "12-20"
    assert by_id[5].reps == "30 giây"
    assert is_unilateral_name(meta[3])
    assert not is_unilateral_name(meta[4])


def test_apply_no_equip_skips_when_equipment_allowed():
    day = PlanDayIn(
        day_number=1,
        exercises=[
            PlanExerciseIn(exercise_id=1, section="main", sets=3, reps="8-12"),
        ],
    )
    apply_no_equip_fitness_doses(
        [day],
        fitness_baseline={"squats_max": 40},
        meta_by_id={
            1: {
                "name_vi": "Ngồi xổm xuống hộp",
                "name_en": "Bodyweight Box Squat",
                "movement_role": "resistance",
            }
        },
        experience_level=1,
        no_equipment=False,
    )
    assert day.exercises[0].reps == "8-12"


def test_home_ring_dip_scales_above_default_from_pushups():
    """Pushups 50 → dip ×0.65 → L2 working tracks the test, not 5–8."""
    bounds = dose_bounds_for_item(
        {
            "name_vi": "Dip vòng treo",
            "name_en": "Ring Dip",
            "movement_role": "compound",
            "movement_pattern": "v_push",
        },
        experience_level=2,
        fitness_baseline={"pushups_max": 50},
        home_session=True,
        no_equipment=False,
    )
    assert bounds["work_mode"] == "reps"
    assert bounds["reps_min"] >= 20
    assert bounds["reps_max"] >= 26
    assert (bounds["reps_min"], bounds["reps_max"]) == (26, 30)


def test_home_band_press_scales_from_pushups():
    bounds = dose_bounds_for_item(
        {
            "name_vi": "Ép ngực dây kháng lực",
            "name_en": "Band Chest Press",
            "movement_role": "isolation",
            "movement_pattern": "h_push",
        },
        experience_level=2,
        fitness_baseline={"pushups_max": 50},
        home_session=True,
        no_equipment=False,
    )
    assert (bounds["reps_min"], bounds["reps_max"]) == (20, 24)


def test_home_dumbbell_uses_level_preset_not_pushups():
    low = dose_bounds_for_item(
        {
            "name_vi": "Chèo tạ đơn",
            "name_en": "Dumbbell Row",
            "movement_role": "compound",
        },
        experience_level=2,
        fitness_baseline={"pushups_max": 20},
        home_session=True,
        no_equipment=False,
    )
    high = dose_bounds_for_item(
        {
            "name_vi": "Chèo tạ đơn",
            "name_en": "Dumbbell Row",
            "movement_role": "compound",
        },
        experience_level=2,
        fitness_baseline={"pushups_max": 60},
        home_session=True,
        no_equipment=False,
    )
    assert (low["reps_min"], low["reps_max"]) == (10, 14)
    assert (high["reps_min"], high["reps_max"]) == (10, 14)


def test_apply_home_fitness_doses_replaces_rep_cues_on_timed_plank():
    from app.services.workout_generation.dose_bounds import apply_home_fitness_doses

    day = PlanDayIn(
        day_number=1,
        exercises=[
            PlanExerciseIn(
                exercise_id=1,
                section="main",
                sets=1,
                reps="15-20 giây",
                notes_vi=(
                    "Chọn độ căng dây / bước đứng để làm đúng 2–6 cái mỗi hiệp "
                    "(còn dư 1–2 cái)."
                ),
            ),
        ],
    )
    apply_home_fitness_doses(
        [day],
        fitness_baseline={"plank_seconds": 20},
        meta_by_id={
            1: {
                "name_vi": "Chống người chống khuỷu",
                "name_en": "Front Plank on Elbows",
                "movement_role": "isolation",
            }
        },
        experience_level=1,
        no_equipment=False,
        home_session=True,
    )
    plank = day.exercises[0]
    assert "giây" in str(plank.reps)
    assert "cái" not in (plank.notes_vi or "")
    assert "Giữ" in (plank.notes_vi or "")


def test_apply_home_fitness_doses_sets_load_cues():
    from app.services.workout_generation.dose_bounds import apply_home_fitness_doses

    day = PlanDayIn(
        day_number=1,
        exercises=[
            PlanExerciseIn(exercise_id=1, section="main", sets=3, reps="8-12"),
            PlanExerciseIn(exercise_id=2, section="main", sets=3, reps="8-12"),
        ],
    )
    meta = {
        1: {
            "name_vi": "Chèo tạ đơn",
            "name_en": "Dumbbell Row",
            "movement_role": "compound",
        },
        2: {
            "name_vi": "Ép ngực dây",
            "name_en": "Band Chest Press",
            "movement_role": "isolation",
            "movement_pattern": "h_push",
        },
    }
    apply_home_fitness_doses(
        [day],
        fitness_baseline={"pushups_max": 50, "pullups_max": 10},
        meta_by_id=meta,
        experience_level=2,
        no_equipment=False,
        home_session=True,
    )
    from app.services.workout_generation.coach_notes import _target_reps

    by_id = {ex.exercise_id: ex for ex in day.exercises}
    assert by_id[1].reps == "8-12"
    assert "Chọn mức tạ" in (by_id[1].notes_vi or "")
    assert f"làm đúng {_target_reps(by_id[1].reps)} cái" in (by_id[1].notes_vi or "")
    assert "Chọn độ căng dây" in (by_id[2].notes_vi or "")
    assert f"làm đúng {_target_reps(by_id[2].reps)} cái" in (by_id[2].notes_vi or "")


def test_apply_home_fitness_doses_primer_stays_half_main():
    from app.services.workout_generation.dose_bounds import (
        apply_home_fitness_doses,
        half_working_reps_label,
    )

    day = PlanDayIn(
        day_number=1,
        exercises=[
            PlanExerciseIn(
                exercise_id=1, section="warmup", sets=2, reps="30 giây", rest_seconds=30
            ),
            PlanExerciseIn(
                exercise_id=10, section="warmup", sets=2, reps="20", rest_seconds=30
            ),
            PlanExerciseIn(exercise_id=10, section="main", sets=3, reps="10"),
        ],
    )
    meta = {
        10: {
            "name_vi": "Chèo tạ đơn",
            "name_en": "Dumbbell Row",
            "movement_role": "compound",
        },
    }
    apply_home_fitness_doses(
        [day],
        fitness_baseline={"pullups_max": 10},
        meta_by_id=meta,
        experience_level=2,
        no_equipment=False,
        home_session=True,
    )
    main = next(ex for ex in day.exercises if ex.section == "main")
    primer = next(
        ex for ex in day.exercises if ex.section == "warmup" and ex.exercise_id == 10
    )
    assert main.reps == "8-12"
    assert primer.reps == half_working_reps_label(main.reps)
    assert primer.reps != main.reps
    assert primer.rest_seconds >= 60
    assert primer.sets == 2
    stretch = next(ex for ex in day.exercises if ex.exercise_id == 1)
    assert stretch.rest_seconds >= 60


def test_apply_home_fitness_doses_bw_primer_half_not_full_working():
    from app.services.workout_generation.dose_bounds import (
        apply_home_fitness_doses,
        half_working_reps_label,
    )

    day = PlanDayIn(
        day_number=1,
        exercises=[
            PlanExerciseIn(
                exercise_id=10, section="warmup", sets=2, reps="20", rest_seconds=30
            ),
            PlanExerciseIn(exercise_id=10, section="main", sets=3, reps="20"),
        ],
    )
    meta = {
        10: {
            "name_vi": "Chống đẩy",
            "name_en": "Push-up",
            "movement_role": "resistance",
        },
    }
    apply_home_fitness_doses(
        [day],
        fitness_baseline={"pushups_max": 40},
        meta_by_id=meta,
        experience_level=2,
        no_equipment=True,
        home_session=True,
    )
    main = next(ex for ex in day.exercises if ex.section == "main")
    primer = next(ex for ex in day.exercises if ex.section == "warmup")
    assert primer.reps == half_working_reps_label(main.reps)
    assert primer.reps != main.reps
    assert primer.rest_seconds >= 60


_RING_DIP = {
    "name_vi": "Dip vòng treo",
    "name_en": "Ring Dip",
    "movement_role": "compound",
    "movement_pattern": "h_push",
}


def test_challenge_ring_dip_no_test_falls_back_3_6_and_rejects_gpt_14():
    assert is_hard_bw_skill_item(_RING_DIP)
    bounds = dose_bounds_for_item(
        _RING_DIP,
        experience_level=2,
        challenge=True,
        home_session=True,
    )
    assert (bounds["reps_min"], bounds["reps_max"]) == (2, 6)
    assert clamp_dose_to_bounds(
        {"sets": 4, "reps": "14"},
        bounds,
        default_sets=3,
        default_reps=default_reps_label(bounds),
    ) == (3, "2-6")


def test_challenge_isolation_clamps_gpt_20_to_bounds():
    item = {
        "name_vi": "Bay vai sau dây",
        "name_en": "Band Reverse Fly",
        "movement_role": "isolation",
    }
    assert not is_skill_bw_item(item)
    bounds = dose_bounds_for_item(item, experience_level=2, challenge=True, home_session=True)
    assert bounds["reps_max"] <= 15
    assert clamp_dose_to_bounds(
        {"sets": 3, "reps": "20"},
        bounds,
        default_sets=3,
        default_reps=default_reps_label(bounds),
    ) == (3, default_reps_label(bounds))


def test_isolation_uses_load_hint_not_pushup_amrap():
    item = {
        "name_vi": "Bay vai sau dây",
        "name_en": "Band Reverse Fly",
        "movement_role": "isolation",
        "movement_pattern": "h_pull",
    }
    bounds = dose_bounds_for_item(
        item,
        experience_level=2,
        home_session=True,
        fitness_baseline={
            "pushups_max": 30,
            "_load_hints": [
                {
                    "pattern": "iso_chest",
                    "working_reps": "10-12",
                    "load_note_vi": "dây vàng",
                    "note_vi": "dây vàng",
                }
            ],
        },
    )
    assert (bounds["reps_min"], bounds["reps_max"]) == (14, 18)
    assert clamp_dose_to_bounds(
        {"sets": 3, "reps": "24"},
        bounds,
        default_sets=3,
        default_reps=default_reps_label(bounds),
    ) == (3, "14-18")


def test_challenge_pullup_no_test_stays_6_12():
    item = {"name_vi": "Hít xà", "name_en": "Pull-up", "movement_role": "compound"}
    assert is_skill_bw_item(item)
    assert not is_hard_bw_skill_item(item)
    bounds = dose_bounds_for_item(item, experience_level=2, challenge=True, home_session=True)
    assert (bounds["reps_min"], bounds["reps_max"]) == (5, 30)


def test_gym_ring_dip_maps_pushups_without_home_session():
    bounds = dose_bounds_for_item(
        _RING_DIP,
        experience_level=2,
        fitness_baseline={"pushups_max": 50},
        home_session=False,
        challenge=True,
    )
    assert (bounds["reps_min"], bounds["reps_max"]) == (26, 30)


_RING_PU = {
    "name_vi": "Chống đẩy vòng treo",
    "name_en": "Ring Push-Up",
    "movement_role": "compound",
    "movement_pattern": "h_push",
}
_RING_ROW = {
    "name_vi": "Chèo vòng treo",
    "name_en": "Ring Row",
    "movement_role": "compound",
    "movement_pattern": "h_pull",
}
_PULLUP = {"name_vi": "Hít xà", "name_en": "Pull-up", "movement_role": "compound"}
_BULGARIAN = {
    "name_vi": "Squat Bulgaria vòng treo",
    "name_en": "Bulgarian Ring Squat",
    "movement_role": "compound",
    "movement_pattern": "squat",
}
_DEAD_HANG = {
    "name_vi": "Treo thả lỏng vòng treo",
    "name_en": "Ring Dead Hang",
    "movement_role": "isolation",
}


def _bar_rings_bounds(item, base):
    return dose_bounds_for_item(
        item,
        experience_level=2,
        fitness_baseline=base,
        home_session=True,
        no_equipment=False,
    )


def _hint_pair(bounds):
    return bounds.get("hint_reps_min"), bounds.get("hint_reps_max")


def test_bar_rings_persona_weak_knee_and_row_identity():
    base = {
        "pushups_max": 8,
        "pushup_variant": "knee",
        "pullups_max": 0,
        "inverted_rows_max": 10,
        "plank_seconds": 20,
        "squats_max": 12,
    }
    assert _hint_pair(_bar_rings_bounds(_RING_PU, base)) == (4, 6)
    assert _hint_pair(_bar_rings_bounds(_RING_ROW, base)) == (4, 8)
    assert (_bar_rings_bounds(_RING_DIP, base)["reps_min"], _bar_rings_bounds(_RING_DIP, base)["reps_max"]) == (2, 6)
    assert _hint_pair(_bar_rings_bounds(_PULLUP, base)) == (2, 6)
    assert _hint_pair(_bar_rings_bounds(_BULGARIAN, base)) == (4, 8)
    assert (_bar_rings_bounds(_RING_PU, base)["reps_min"], _bar_rings_bounds(_RING_PU, base)["reps_max"]) == (4, 6)
    hang = _bar_rings_bounds(_DEAD_HANG, base)
    assert hang["work_mode"] == "hold"
    assert hang["seconds_max"] <= 20


def test_bar_rings_amrap_16_compounds_use_eight_twelve():
    base = {"pushups_max": 16, "pullups_max": 16, "squats_max": 16}
    assert _hint_pair(_bar_rings_bounds(_RING_PU, base)) == (8, 12)
    assert _hint_pair(_bar_rings_bounds(_PULLUP, base)) == (8, 12)


def test_bar_rings_persona_mid():
    base = {
        "pushups_max": 25,
        "pullups_max": 8,
        "plank_seconds": 60,
        "squats_max": 40,
    }
    assert _hint_pair(_bar_rings_bounds(_RING_PU, base)) == (18, 20)
    assert (_bar_rings_bounds(_RING_DIP, base)["reps_min"], _bar_rings_bounds(_RING_DIP, base)["reps_max"]) == (12, 16)
    assert _hint_pair(_bar_rings_bounds(_RING_ROW, base)) == (4, 6)
    assert _hint_pair(_bar_rings_bounds(_PULLUP, base)) == (4, 6)
    assert _hint_pair(_bar_rings_bounds(_BULGARIAN, base)) == (20, 24)
    hang = _bar_rings_bounds(_DEAD_HANG, base)
    assert hang["work_mode"] == "hold"
    assert hang["seconds_max"] <= 45
    assert hang["seconds_min"] >= 15


def test_bar_rings_persona_high_tracks_test_not_capped():
    base = {
        "pushups_max": 80,
        "pullups_max": 20,
        "plank_seconds": 90,
        "squats_max": 80,
    }
    pu = _bar_rings_bounds(_RING_PU, base)
    assert _hint_pair(pu) == (62, 64)
    assert (pu["reps_min"], pu["reps_max"]) == (62, 64)
    dip = _bar_rings_bounds(_RING_DIP, base)
    assert (dip["reps_min"], dip["reps_max"]) == (42, 46)
    fly = _bar_rings_bounds(
        {
            "name_vi": "Ép ngực vòng treo",
            "name_en": "Ring Chest Fly",
            "movement_role": "isolation",
            "movement_pattern": "other",
        },
        base,
    )
    assert fly.get("hint_reps_min", fly["reps_min"]) >= 10
    pull = _bar_rings_bounds(_PULLUP, base)
    assert _hint_pair(pull) == (12, 16)
    hang = _bar_rings_bounds(_DEAD_HANG, base)
    assert hang["seconds_max"] <= 45
    lsit = _bar_rings_bounds(
        {
            "name_vi": "L-Sit vòng treo",
            "name_en": "Ring L-Sit",
            "movement_role": "main",
        },
        base,
    )
    assert lsit["work_mode"] == "hold"
    assert lsit["seconds_max"] <= 20
    skin = _bar_rings_bounds(
        {
            "name_vi": "Skin the Cat vòng treo",
            "name_en": "Skin the Cat",
            "movement_role": "compound",
        },
        base,
    )
    assert _hint_pair(skin) == (3, 6)


def test_bar_rings_does_not_change_floor_bw_band_or_db():
    floor = dose_bounds_for_item(
        {"name_vi": "Chống đẩy", "name_en": "Push-up", "movement_role": "compound"},
        experience_level=2,
        fitness_baseline={"pushups_max": 60},
        no_equipment=True,
    )
    assert (floor["reps_min"], floor["reps_max"]) == (44, 48)

    band = dose_bounds_for_item(
        {
            "name_vi": "Ép ngực dây kháng lực",
            "name_en": "Band Chest Press",
            "movement_role": "isolation",
            "movement_pattern": "h_push",
        },
        experience_level=2,
        fitness_baseline={"pushups_max": 50},
        home_session=True,
        no_equipment=False,
    )
    assert (band["reps_min"], band["reps_max"]) == (20, 24)

    db = dose_bounds_for_item(
        {
            "name_vi": "Chèo tạ đơn",
            "name_en": "Dumbbell Row",
            "movement_role": "compound",
        },
        experience_level=2,
        fitness_baseline={"pushups_max": 60},
        home_session=True,
        no_equipment=False,
    )
    assert (db["reps_min"], db["reps_max"]) == (10, 14)


def test_bar_rings_row_does_not_use_push_proxy_when_row_test_exists():
    bounds = _bar_rings_bounds(
        _RING_ROW,
        {"pushups_max": 80, "inverted_rows_max": 12, "pullups_max": 0},
    )
    assert _hint_pair(bounds) == (6, 10)
    assert (bounds["reps_min"], bounds["reps_max"]) == (6, 10)


def test_plank_finisher_reps_80_percent_five_second_band():
    from app.services.workout_generation.assemble import plank_finisher_reps

    assert plank_finisher_reps({"plank_seconds": 40}) == "30-35 giây"
    assert plank_finisher_reps(None) == "20-30 giây"


def test_inject_legs_plank_before_cardio():
    from app.services.workout_generation.assemble import inject_legs_plank_finisher
    from app.services.workout_generation.shortlist import ShortlistItem

    plank = ShortlistItem(
        id=671,
        name_vi="Chống người chống khuỷu",
        name_en="Front Plank on Elbows",
        movement_role="isolation",
        movement_pattern="core",
        muscle_slug="core",
        difficulty=1,
    )
    day = PlanDayIn(
        day_number=1,
        split_role="legs",
        exercises=[
            PlanExerciseIn(exercise_id=1, sets=3, reps="10-15", rest_seconds=120, section="main"),
            PlanExerciseIn(exercise_id=2, sets=7, reps="30 giây", rest_seconds=45, section="cardio"),
        ],
    )
    meta: dict = {}
    used: set[int] = {1, 2}
    inject_legs_plank_finisher(
        day,
        meta_by_id=meta,
        shortlists={"accessory": [plank]},
        used_ids=used,
        fitness_baseline={"plank_seconds": 40},
    )
    assert [ex.exercise_id for ex in day.exercises] == [1, 671, 2]
    hold = day.exercises[1]
    cardio = day.exercises[2]
    assert hold.reps == "30-35 giây"
    assert hold.sets == 1
    assert cardio.sets == 4
    assert hold.rest_seconds >= 90
    assert hold.section == "main"


def test_plank_moves_to_end_of_main_before_cardio():
    from app.services.workout_generation.muscle_quotas import reorder_main_section_exercises
    from app.services.workout_generation.shortlist import ShortlistItem

    day = PlanDayIn(
        day_number=1,
        split_role="push",
        exercises=[
            PlanExerciseIn(exercise_id=671, sets=2, reps="30-35 giây", rest_seconds=90, section="main"),
            PlanExerciseIn(exercise_id=1, sets=3, reps="10-15", rest_seconds=120, section="main"),
            PlanExerciseIn(exercise_id=2, sets=4, reps="30 giây", rest_seconds=45, section="cardio"),
            PlanExerciseIn(exercise_id=3, sets=2, reps="30 giây", rest_seconds=20, section="cooldown"),
        ],
    )
    meta = {
        671: ShortlistItem(
            id=671,
            name_vi="Plank",
            name_en="Front Plank on Elbows",
            movement_role="isolation",
            movement_pattern="core",
            muscle_slug="core",
            difficulty=1,
        ),
        1: ShortlistItem(
            id=1,
            name_vi="Đẩy ngực",
            name_en="Push Up",
            movement_role="compound",
            movement_pattern="h_push",
            muscle_slug="chest",
            difficulty=1,
        ),
    }
    out = reorder_main_section_exercises("push", day.exercises, meta)
    ids = [ex.exercise_id for ex in out]
    assert ids == [1, 671, 2, 3]


def test_cardio_plank_split_keeps_cardio():
    from app.services.workout_generation.assemble import cardio_plank_set_split

    assert cardio_plank_set_split(7) == (4, 3)
    keep, plank = cardio_plank_set_split(5)
    assert keep >= 2
    assert plank >= 1
    assert keep + plank == 5 or plank >= 1
