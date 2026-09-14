from app.schemas.plans import PlanDayIn, PlanExerciseIn
from app.services.workout_generation.assemble import inject_main_primer_warmup
from app.services.workout_generation.dose_bounds import (
    apply_no_equip_fitness_doses,
    clamp_openai_dose,
    default_reps_label,
    dose_bounds_for_item,
    half_working_reps_label,
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
    assert clamp_openai_dose(
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
    assert clamp_openai_dose(
        {"sets": 3, "reps": "20"},
        bounds,
        default_sets=3,
        default_reps="5-8",
    ) == (3, "1-3")


def test_pushups_compound_70_80_and_iso_bands_by_equipment():
    item = {"name_vi": "Chống đẩy", "name_en": "Push-up", "movement_role": "compound"}
    high = dose_bounds_for_item(
        item,
        experience_level=2,
        fitness_baseline={"pushups_max": 60},
        no_equipment=True,
    )
    assert high["work_mode"] == "reps"
    assert high["reps_min"] == 42
    assert high["reps_max"] == 48
    assert clamp_openai_dose(
        {"sets": 3, "reps": "55"},
        high,
        default_sets=3,
        default_reps="10-12",
    ) == (3, "42-48")

    iso_no_equip = dose_bounds_for_item(
        {**item, "movement_role": "isolation"},
        experience_level=2,
        fitness_baseline={"pushups_max": 60},
        no_equipment=True,
    )
    assert iso_no_equip["reps_min"] == 48
    assert iso_no_equip["reps_max"] == 54

    iso_with_gear = dose_bounds_for_item(
        {**item, "movement_role": "isolation"},
        experience_level=2,
        fitness_baseline={"pushups_max": 60},
        no_equipment=False,
    )
    assert iso_with_gear["reps_min"] == 36
    assert iso_with_gear["reps_max"] == 42


def test_bodyweight_edge_max_zero_one_three():
    item = {"name_vi": "Chống đẩy", "name_en": "Push-up", "movement_role": "compound"}
    zero = dose_bounds_for_item(
        item, experience_level=1, fitness_baseline={"pushups_max": 0}, no_equipment=True
    )
    assert (zero["reps_min"], zero["reps_max"]) == (1, 3)

    one = dose_bounds_for_item(
        item, experience_level=1, fitness_baseline={"pushups_max": 1}, no_equipment=True
    )
    assert (one["reps_min"], one["reps_max"]) == (1, 1)

    three = dose_bounds_for_item(
        item, experience_level=1, fitness_baseline={"pushups_max": 3}, no_equipment=True
    )
    assert (three["reps_min"], three["reps_max"]) == (1, 2)


def test_superman_no_equip_isolation_80_90_of_pullups():
    item = {"name_vi": "Superman", "name_en": "Superman", "movement_role": "isolation"}
    bounds = dose_bounds_for_item(
        item,
        experience_level=2,
        fitness_baseline={"pullups_max": 10},
        no_equipment=True,
    )
    assert bounds["reps_min"] == 8
    assert bounds["reps_max"] == 9


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
    # Row transfer ×2.0 → equiv 20 → L2 compound 70–80%.
    assert (table["reps_min"], table["reps_max"]) == (14, 16)

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
    assert (backpack["reps_min"], backpack["reps_max"]) == (16, 18)

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
    assert (with_flag_off["reps_min"], with_flag_off["reps_max"]) == (14, 16)

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
    assert (bounds["reps_min"], bounds["reps_max"]) == (12, 13)


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
    assert (no_equip["reps_min"], no_equip["reps_max"]) == (14, 16)

    with_gear = dose_bounds_for_item(
        item,
        experience_level=2,
        fitness_baseline={"pullups_max": 10, "pushups_max": 60},
        no_equipment=False,
    )
    assert (with_gear["reps_min"], with_gear["reps_max"]) == (5, 12)


def test_half_working_reps_label():
    assert half_working_reps_label("10") == "5"
    assert half_working_reps_label("8–12") == "5"
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
    assert len(primers) == 1
    assert primers[0].reps == "5"
    assert primers[0].rest_seconds >= 60
    stretch = next(ex for ex in out.exercises if ex.exercise_id == 1)
    assert stretch.rest_seconds >= 60


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
    assert primers[0].rest_seconds == 45
    # Gym loaded path still uses fixed light primer reps when no baseline.
    assert primers[0].reps in {"4", "5"}


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
    assert primers[0].reps == "24"


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
    assert default_reps_label(bounds) == "12-13"
    assert clamp_openai_dose(
        None,
        bounds,
        default_sets=3,
        default_reps=default_reps_label(bounds),
    ) == (3, "12-13")
    # Prescription-style default must not stick when out of fitness band.
    assert clamp_openai_dose(
        None,
        bounds,
        default_sets=3,
        default_reps="10-12",
    ) == (3, "12-13")


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
    assert (bounds["reps_min"], bounds["reps_max"]) == (2, 3)


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
    assert (bounds["reps_min"], bounds["reps_max"]) == (10, 12)


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
    assert (push["reps_min"], push["reps_max"]) == (27, 31)

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
    assert clamp_openai_dose(
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
    assert by_id[1].reps == "24-28"
    assert by_id[1].reps != "8-12"
    assert by_id[2].reps == "28-32"
    assert by_id[3].reps == "14-16"
    assert "mỗi chân" in (by_id[3].notes_vi or "")
    assert "đổi chân" in (by_id[3].notes_vi or "")
    assert by_id[4].reps == "28-32"
    assert "mỗi chân" not in (by_id[4].notes_vi or "")
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
    """Pushups 50 → dip ×0.35 → L2 working > default 5–8."""
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
    assert bounds["reps_min"] > 8
    assert bounds["reps_max"] >= bounds["reps_min"]
    assert (bounds["reps_min"], bounds["reps_max"]) == (11, 13)


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
    assert (bounds["reps_min"], bounds["reps_max"]) == (21, 24)


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
    assert (low["reps_min"], low["reps_max"]) == (6, 10)
    assert (high["reps_min"], high["reps_max"]) == (6, 10)


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
    by_id = {ex.exercise_id: ex for ex in day.exercises}
    assert by_id[1].reps == "6-10"
    assert "Chọn mức tạ" in (by_id[1].notes_vi or "")
    assert "Chọn độ căng dây" in (by_id[2].notes_vi or "")


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
    assert main.reps == "6-10"
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
