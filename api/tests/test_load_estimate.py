from app.api.v1.ai import FitnessBaselineIn
from app.services.workout_generation.challenge_prompt import challenge_user_summary
from app.services.workout_generation.dose_bounds import dose_bounds_for_item
from app.services.workout_generation.load_estimate import (
    apply_challenge_load,
    epley_1rm,
    floor_from_knee_band,
    hint_for_item,
    progress_db_prescription,
    working_8_10,
    working_rep_band,
    round_kg,
)


def test_set_prescription_skips_engine_rpe_zero():
    import pytest
    from pydantic import ValidationError

    from app.schemas.plans import PlanExerciseIn, PlanSetPrescription
    from app.services.workout_generation.load_estimate import prescription_rpe

    assert prescription_rpe(0) is None
    assert prescription_rpe(7) == 7.0
    with pytest.raises(ValidationError):
        PlanSetPrescription(reps="10-15", rest_seconds=120, rpe=0, load_note_vi="Gợi ý: 10kg")
    PlanExerciseIn(
        exercise_id=1,
        sets=3,
        reps="10-15",
        rest_seconds=120,
        set_prescriptions=[
            PlanSetPrescription(
                reps="10-15",
                rest_seconds=120,
                rpe=prescription_rpe(0),
                load_note_vi="Gợi ý: 10kg",
            )
        ],
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
    assert press_hint["load_kg_each"] == 10


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
    assert challenge["reps_max"] == 18
    assert challenge.get("load_kg_each") == 5.0

    preset = dose_bounds_for_item(
        item,
        experience_level=2,
        fitness_baseline={"pushups_max": 20},
        home_session=True,
        challenge=False,
    )
    assert (preset["reps_min"], preset["reps_max"]) == (14, 18)


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
    assert "vàng" in pull["note_vi"].lower()
    press = next(h for h in loaded["_load_hints"] if h["pattern"] == "h_press")
    assert "đẩy ngực dây" in press["note_vi"].lower() or "band chest press" in press["note_vi"].lower()
    assert "chống đẩy" not in press["note_vi"].lower()
    assert not any(h["pattern"] == "h_press_floor" for h in loaded["_load_hints"])
    assert any("đẩy ngực dây" in t for t in loaded["_tests_vi"])
    assert pull.get("load_note_vi") == "Dây vàng · 10 lbs"
    assert pull.get("band_level") == "yellow"


def test_suggest_band_level_shifts():
    from app.services.workout_generation.load_estimate import (
        band_level_label_vi,
        suggest_band_level,
    )

    assert suggest_band_level("yellow") == "yellow"
    assert suggest_band_level("light") == "yellow"
    assert suggest_band_level("medium") == "blue"
    assert suggest_band_level("blue", role="isolation") == "red"
    assert suggest_band_level("blue", section="warmup") == "yellow"
    assert suggest_band_level("yellow", role="isolation") == "yellow"
    assert band_level_label_vi("green") == "Dây xanh lá · 25 lbs"


def test_attach_band_set_prescriptions_per_role():
    from types import SimpleNamespace

    from app.services.workout_generation.load_estimate import attach_band_set_prescriptions

    band_meta = {
        "name_en": "Band Chest Press",
        "name_vi": "Đẩy ngực với dây kháng lực",
        "movement_role": "compound",
        "equipment_slugs": ["resistance-band-2"],
    }
    iso_meta = {
        **band_meta,
        "name_en": "Band Fly",
        "name_vi": "Mở ngực dây",
        "movement_role": "isolation",
    }
    day = SimpleNamespace(
        exercises=[
            SimpleNamespace(
                exercise_id=1,
                sets=3,
                reps="12",
                rest_seconds=90,
                rpe=None,
                section="main",
                notes_vi="Làm đủ số cái.",
                set_prescriptions=None,
            ),
            SimpleNamespace(
                exercise_id=2,
                sets=2,
                reps="15",
                rest_seconds=60,
                rpe=None,
                section="main",
                notes_vi=None,
                set_prescriptions=None,
            ),
            SimpleNamespace(
                exercise_id=3,
                sets=2,
                reps="8",
                rest_seconds=60,
                rpe=None,
                section="warmup",
                notes_vi=None,
                set_prescriptions=None,
            ),
            SimpleNamespace(
                exercise_id=4,
                sets=3,
                reps="10",
                rest_seconds=90,
                rpe=None,
                section="main",
                notes_vi=None,
                set_prescriptions=None,
            ),
        ]
    )
    meta = {
        1: band_meta,
        2: iso_meta,
        3: band_meta,
        4: {
            "name_en": "Push Up",
            "name_vi": "Chống đẩy",
            "movement_role": "compound",
            "equipment_slugs": [],
        },
    }
    attach_band_set_prescriptions(
        day, meta_by_id=meta, fitness_baseline={"band_level": "blue"}
    )
    assert len(day.exercises[0].set_prescriptions) == 3
    assert day.exercises[0].set_prescriptions[0].load_note_vi == "Gợi ý: Dây xanh dương · 20 lbs"
    assert day.exercises[1].set_prescriptions[0].load_note_vi == "Gợi ý: Dây đỏ · 15 lbs"
    assert day.exercises[2].set_prescriptions[0].load_note_vi == "Gợi ý: Dây vàng · 10 lbs"
    assert day.exercises[3].set_prescriptions is None

    blank = SimpleNamespace(
        exercises=[
            SimpleNamespace(
                exercise_id=1,
                sets=3,
                reps="12",
                rest_seconds=90,
                rpe=None,
                section="main",
                notes_vi=None,
                set_prescriptions=None,
            )
        ]
    )
    attach_band_set_prescriptions(
        blank, meta_by_id={1: band_meta}, fitness_baseline={"band_level": None}
    )
    assert blank.exercises[0].set_prescriptions[0].load_note_vi == (
        "Gợi ý: Dây xanh dương · 20 lbs"
    )

    kept = day.exercises[0].set_prescriptions[0].load_note_vi
    attach_band_set_prescriptions(
        day, meta_by_id=meta, fitness_baseline={"band_level": "yellow"}
    )
    assert len(day.exercises[0].set_prescriptions) == 3
    assert day.exercises[0].set_prescriptions[0].load_note_vi == kept

    day.exercises[0].sets = 2
    day.exercises[0].reps = "8-12"
    day.exercises[0].rest_seconds = 150
    attach_band_set_prescriptions(
        day, meta_by_id=meta, fitness_baseline={"band_level": "yellow"}
    )
    rewritten = day.exercises[0].set_prescriptions
    assert len(rewritten) == 2
    assert rewritten[0].reps == "8-12"
    assert rewritten[0].rest_seconds == 150
    assert rewritten[1].rest_seconds == 150
    assert rewritten[0].load_note_vi == kept


def test_progress_band_bumps_and_stacks():
    from app.services.workout_generation.load_estimate import (
        attach_band_set_prescriptions,
        band_load_note_vi,
        progress_band_prescription,
    )

    assert progress_band_prescription("yellow", 25, section="main", role="compound") == (
        "red",
        None,
    )
    assert progress_band_prescription("yellow", 25, section="main", role="isolation") == (
        "yellow",
        None,
    )
    assert progress_band_prescription("black", 22, section="main", role="compound") == (
        "black",
        "yellow",
    )
    assert progress_band_prescription("black", 22, section="warmup", role="compound") == (
        "blue",
        None,
    )
    assert progress_band_prescription("yellow", 12, section="main", role="compound") == (
        "yellow",
        None,
    )
    assert progress_band_prescription("yellow", 35, section="main", role="compound") == (
        "blue",
        None,
    )
    assert progress_band_prescription("green", 40, section="main", role="compound") == (
        "black",
        None,
    )
    assert "xanh lá" in (band_load_note_vi("black", "green") or "")

    from types import SimpleNamespace

    press = {
        "name_en": "Band Chest Press",
        "name_vi": "Đẩy ngực với dây kháng lực",
        "movement_role": "compound",
        "movement_pattern": "h_press",
        "equipment_slugs": ["resistance-band-2"],
    }
    row = {
        "name_en": "Band Row",
        "name_vi": "Chèo dây",
        "movement_role": "compound",
        "movement_pattern": "h_pull",
        "equipment_slugs": ["resistance-band-2"],
    }
    day = SimpleNamespace(
        exercises=[
            SimpleNamespace(
                exercise_id=1,
                sets=3,
                reps="10",
                rest_seconds=90,
                rpe=None,
                section="main",
                notes_vi=None,
                set_prescriptions=None,
            ),
            SimpleNamespace(
                exercise_id=2,
                sets=3,
                reps="10",
                rest_seconds=90,
                rpe=None,
                section="main",
                notes_vi=None,
                set_prescriptions=None,
            ),
        ]
    )
    attach_band_set_prescriptions(
        day,
        meta_by_id={1: press, 2: row},
        fitness_baseline={
            "band_level_push": "yellow",
            "pushups_max": 25,
            "band_level_pull": "black",
            "pullups_max": 22,
        },
    )
    assert day.exercises[0].set_prescriptions[0].load_note_vi == "Gợi ý: Dây đỏ · 15 lbs"
    assert day.exercises[1].set_prescriptions[0].load_note_vi == (
        "Gợi ý: Dây đen · 30 lbs + vàng · 10 lbs"
    )


def test_progress_db_calibrates_10_20():
    from app.services.workout_generation.load_estimate import (
        compound_working_reps,
        isolation_working_reps,
    )

    keep, cal = progress_db_prescription(10, 16, slot="press")
    assert keep == 10
    assert cal == 16
    assert compound_working_reps(16) == (8, 12)
    squat, cal = progress_db_prescription(20, 25, slot="squat")
    assert squat == 22.5
    assert cal == 15
    assert compound_working_reps(15) == (8, 12)
    press, cal = progress_db_prescription(10, 25, slot="press")
    assert press == 12.5
    assert cal == 15
    press_hi, cal = progress_db_prescription(10, 35, slot="press")
    assert press_hi == 15.0
    assert cal == 15
    cap, cal = progress_db_prescription(20, 25, slot="press")
    assert cap == 17.5
    assert cal == 20
    drop, cal = progress_db_prescription(10, 8, slot="press")
    assert drop == 7.5
    assert cal == 15
    easy_same, cal = progress_db_prescription(10, 20, slot="press", easy=True)
    assert easy_same == 7.5
    assert cal == 20
    bench, _ = progress_db_prescription(
        10,
        16,
        slot="press",
        section="main",
        role="compound",
        item={
            "name_en": "Dumbbell Bench Press",
            "name_vi": "Đẩy ngực tạ đơn",
            "movement_pattern": "h_push",
        },
    )
    assert bench == 10
    ohp, _ = progress_db_prescription(
        10,
        16,
        slot="press",
        section="main",
        role="compound",
        item={
            "name_en": "Dumbbell Seated Overhead Press",
            "name_vi": "Đẩy vai ngồi tạ đơn",
            "movement_pattern": "v_push",
        },
    )
    assert ohp == 7.5
    wu, _ = progress_db_prescription(
        10,
        16,
        slot="press",
        section="warmup",
        role="compound",
        item={
            "name_en": "Dumbbell Bench Press",
            "name_vi": "Đẩy ngực tạ đơn",
            "movement_pattern": "h_push",
        },
    )
    assert wu == 5.0
    incline, _ = progress_db_prescription(
        10,
        16,
        slot="press",
        section="main",
        role="compound",
        item={
            "name_en": "Dumbbell Incline Bench Press",
            "name_vi": "Ép ngực dốc lên tạ đơn",
            "movement_pattern": "h_push",
        },
    )
    assert incline == 7.5
    iso, cal = progress_db_prescription(
        10, 25, slot="press", section="main", role="isolation"
    )
    assert iso == 7.5
    assert cal == 15
    assert isolation_working_reps(15) == (10, 16)


def test_dumbbell_hints_use_preset_steps_not_epley():
    loaded = apply_challenge_load(
        {
            "test_kit": "dumbbell",
            "db_press_reps": 16,
            "db_press_kg": 10,
            "db_row_reps": 16,
            "db_row_kg": 10,
            "goblet_reps": 16,
            "goblet_kg": 20,
        },
        weight_kg=70,
        equipment_list=["dumbbell"],
    )
    press = next(h for h in loaded["_load_hints"] if h["pattern"] == "h_press")
    row = next(h for h in loaded["_load_hints"] if h["pattern"] == "h_pull")
    squat = next(h for h in loaded["_load_hints"] if h["pattern"] == "squat")
    iso = next(h for h in loaded["_load_hints"] if h["pattern"] == "iso_chest")
    assert press["load_kg_each"] == 10
    assert press["working_reps"] == "8-12"
    assert row["load_kg_each"] == 10
    assert squat["load_kg_each"] == 20
    assert squat["working_reps"] == "8-12"
    assert iso["load_kg_each"] == 5.0
    assert iso["working_reps"] == "10-16"
    fly = hint_for_item(
        {
            "name_en": "Band Reverse Fly",
            "name_vi": "Bay vai sau dây",
            "movement_role": "isolation",
            "movement_pattern": "h_pull",
        },
        loaded["_load_hints"],
    )
    assert fly is None
    pushup = hint_for_item(
        {
            "name_en": "Push-up",
            "name_vi": "Chống đẩy",
            "movement_role": "compound",
            "movement_pattern": "h_push",
            "equipment_slugs": ["dumbbell"],
        },
        loaded["_load_hints"],
    )
    assert pushup is None
    db_press = hint_for_item(
        {
            "name_en": "Dumbbell Bench Press",
            "name_vi": "Đẩy ngực tạ đơn",
            "movement_role": "compound",
            "movement_pattern": "h_push",
        },
        loaded["_load_hints"],
    )
    assert db_press is not None
    assert db_press.get("load_kg_each") == 10
    bounds = dose_bounds_for_item(
        {
            "name_en": "Band Reverse Fly",
            "name_vi": "Bay vai sau dây",
            "movement_role": "isolation",
        },
        experience_level=2,
        home_session=True,
        fitness_baseline=loaded,
    )
    assert bounds["reps_max"] <= 20

    bumped = apply_challenge_load(
        {
            "test_kit": "dumbbell",
            "db_press_reps": 25,
            "db_press_kg": 10,
            "goblet_reps": 25,
            "goblet_kg": 20,
        },
        weight_kg=70,
        equipment_list=["dumbbell"],
        easy=True,
    )
    easy_press = next(h for h in bumped["_load_hints"] if h["pattern"] == "h_press")
    easy_squat = next(h for h in bumped["_load_hints"] if h["pattern"] == "squat")
    easy_iso = next(h for h in bumped["_load_hints"] if h["pattern"] == "iso_chest")
    assert easy_press["load_kg_each"] == 10
    assert easy_press["working_reps"] == "8-12"
    assert easy_squat["load_kg_each"] == 20
    assert easy_iso["load_kg_each"] == 5.0
    assert easy_iso["working_reps"] == "10-16"


def test_attach_db_set_prescriptions_is_suggestion():
    from types import SimpleNamespace

    from app.services.workout_generation.load_estimate import attach_db_set_prescriptions

    day = SimpleNamespace(
        exercises=[
            SimpleNamespace(
                exercise_id=1,
                sets=3,
                reps="12-15",
                rest_seconds=90,
                rpe=None,
                section="main",
                notes_vi=None,
                set_prescriptions=None,
            ),
            SimpleNamespace(
                exercise_id=2,
                sets=3,
                reps="12",
                rest_seconds=90,
                rpe=None,
                section="main",
                notes_vi=None,
                set_prescriptions=None,
            ),
        ]
    )
    attach_db_set_prescriptions(
        day,
        meta_by_id={
            1: {
                "name_en": "Dumbbell Bench Press",
                "name_vi": "Đẩy ngực tạ đơn",
                "movement_role": "compound",
                "movement_pattern": "h_push",
                "equipment_slugs": ["dumbbell"],
            },
            2: {
                "name_en": "Dumbbell Goblet Squat",
                "name_vi": "Ngồi xổm ôm tạ đơn",
                "movement_role": "compound",
                "movement_pattern": "squat",
                "equipment_slugs": ["dumbbell"],
            },
        },
        fitness_baseline={
            "test_kit": "dumbbell",
            "db_press_reps": 25,
            "db_press_kg": 10,
            "goblet_reps": 25,
            "goblet_kg": 20,
        },
    )
    assert day.exercises[0].set_prescriptions[0].load_note_vi == "Gợi ý: 12.5kg mỗi tay"
    assert day.exercises[1].set_prescriptions[0].load_note_vi == "Gợi ý: 22.5kg"


def test_attach_db_leg_curl_is_one_bell_not_each_hand():
    from types import SimpleNamespace

    from app.services.workout_generation.load_estimate import attach_db_set_prescriptions

    day = SimpleNamespace(
        exercises=[
            SimpleNamespace(
                exercise_id=1,
                sets=3,
                reps="10-16",
                rest_seconds=90,
                rpe=None,
                section="main",
                notes_vi=None,
                set_prescriptions=None,
            )
        ]
    )
    attach_db_set_prescriptions(
        day,
        meta_by_id={
            1: {
                "name_en": "Dumbbell Leg Curl",
                "name_vi": "Cuốn đùi sau tạ đơn",
                "movement_role": "isolation",
                "movement_pattern": "knee_flexion",
                "equipment_slugs": ["dumbbell"],
            }
        },
        fitness_baseline={
            "test_kit": "dumbbell",
            "db_press_reps": 15,
            "db_press_kg": 10,
        },
    )
    note = day.exercises[0].set_prescriptions[0].load_note_vi
    assert note.startswith("Gợi ý:")
    assert "kg" in note
    assert "mỗi tay" not in note


def test_attach_db_isolation_lighter_than_flat_press():
    from types import SimpleNamespace

    from app.services.workout_generation.load_estimate import attach_db_set_prescriptions

    day = SimpleNamespace(
        exercises=[
            SimpleNamespace(
                exercise_id=1,
                sets=3,
                reps="10-15",
                rest_seconds=120,
                rpe=None,
                section="main",
                notes_vi=None,
                set_prescriptions=None,
            ),
            SimpleNamespace(
                exercise_id=2,
                sets=3,
                reps="12-18",
                rest_seconds=90,
                rpe=None,
                section="main",
                notes_vi=None,
                set_prescriptions=None,
            ),
        ]
    )
    attach_db_set_prescriptions(
        day,
        meta_by_id={
            1: {
                "name_en": "Dumbbell Bench Press",
                "name_vi": "Đẩy ngực tạ đơn",
                "movement_role": "compound",
                "movement_pattern": "h_push",
                "equipment_slugs": ["dumbbell"],
            },
            2: {
                "name_en": "Dumbbell Fly",
                "name_vi": "Mở ngực tạ đơn",
                "movement_role": "isolation",
                "movement_pattern": "h_push",
                "equipment_slugs": ["dumbbell"],
            },
        },
        fitness_baseline={
            "test_kit": "dumbbell",
            "db_press_reps": 25,
            "db_press_kg": 10,
        },
    )
    press = day.exercises[0].set_prescriptions[0].load_note_vi
    fly = day.exercises[1].set_prescriptions[0].load_note_vi
    assert press != fly
    assert "12.5kg" in press
    assert "7.5kg" in fly


def test_attach_db_incline_between_flat_and_fly():
    from types import SimpleNamespace

    from app.services.workout_generation.load_estimate import attach_db_set_prescriptions

    day = SimpleNamespace(
        exercises=[
            SimpleNamespace(
                exercise_id=1, sets=3, reps="10-15", rest_seconds=120,
                rpe=None, section="main", notes_vi=None,
                set_prescriptions=[SimpleNamespace(load_note_vi="Gợi ý: 15kg")],
            ),
            SimpleNamespace(
                exercise_id=2, sets=3, reps="10-15", rest_seconds=120,
                rpe=None, section="main", notes_vi=None, set_prescriptions=None,
            ),
            SimpleNamespace(
                exercise_id=3, sets=3, reps="12-18", rest_seconds=90,
                rpe=None, section="main", notes_vi=None, set_prescriptions=None,
            ),
        ]
    )
    attach_db_set_prescriptions(
        day,
        meta_by_id={
            1: {
                "name_en": "Dumbbell Bench Press",
                "name_vi": "Đẩy ngực tạ đơn",
                "movement_role": "compound",
                "movement_pattern": "h_push",
                "equipment_slugs": ["dumbbell"],
            },
            2: {
                "name_en": "Incline Dumbbell Press",
                "name_vi": "Đẩy ngực dốc lên tạ đơn",
                "movement_role": "compound",
                "movement_pattern": "h_push",
                "equipment_slugs": ["dumbbell"],
            },
            3: {
                "name_en": "Dumbbell Fly",
                "name_vi": "Mở ngực tạ đơn",
                "movement_role": "isolation",
                "movement_pattern": "h_push",
                "equipment_slugs": ["dumbbell"],
            },
        },
        fitness_baseline={
            "test_kit": "dumbbell",
            "db_press_reps": 25,
            "db_press_kg": 10,
        },
    )
    flat = day.exercises[0].set_prescriptions[0].load_note_vi
    incline = day.exercises[1].set_prescriptions[0].load_note_vi
    fly = day.exercises[2].set_prescriptions[0].load_note_vi
    assert "12.5kg" in flat
    assert "10kg" in incline
    assert "7.5kg" in fly
    assert flat != incline != fly


def test_attach_db_covers_unnamed_db_lifts_not_plank():
    from types import SimpleNamespace

    from app.services.workout_generation.load_estimate import attach_db_set_prescriptions

    day = SimpleNamespace(
        exercises=[
            SimpleNamespace(
                exercise_id=1,
                sets=3,
                reps="12",
                rest_seconds=90,
                rpe=None,
                section="main",
                notes_vi=None,
                set_prescriptions=None,
            ),
            SimpleNamespace(
                exercise_id=2,
                sets=3,
                reps="12",
                rest_seconds=90,
                rpe=None,
                section="main",
                notes_vi=None,
                set_prescriptions=None,
            ),
            SimpleNamespace(
                exercise_id=3,
                sets=2,
                reps="40",
                rest_seconds=60,
                rpe=None,
                section="main",
                notes_vi=None,
                set_prescriptions=None,
            ),
        ]
    )
    attach_db_set_prescriptions(
        day,
        meta_by_id={
            1: {
                "name_en": "Overhead Press",
                "name_vi": "Đẩy vai",
                "movement_role": "compound",
                "movement_pattern": "v_push",
                "equipment_slugs": [],
            },
            2: {
                "name_en": "Walking Lunge",
                "name_vi": "Bước tới",
                "movement_role": "compound",
                "movement_pattern": "lunge",
                "equipment_slugs": [],
            },
            3: {
                "name_en": "Front Plank on Elbows",
                "name_vi": "Plank",
                "movement_role": "core",
                "movement_pattern": "core",
                "equipment_slugs": [],
            },
        },
        fitness_baseline={
            "test_kit": "dumbbell",
            "db_press_reps": 25,
            "db_press_kg": 10,
            "goblet_reps": 25,
            "goblet_kg": 20,
        },
    )
    assert day.exercises[0].set_prescriptions is None
    assert day.exercises[1].set_prescriptions is None
    assert day.exercises[2].set_prescriptions is None


def test_attach_db_skips_bodyweight_even_if_slug_lists_dumbbell():
    from types import SimpleNamespace

    from app.services.workout_generation.load_estimate import attach_db_set_prescriptions

    day = SimpleNamespace(
        exercises=[
            SimpleNamespace(
                exercise_id=1,
                sets=3,
                reps="10-15",
                rest_seconds=120,
                rpe=None,
                section="main",
                notes_vi=None,
                set_prescriptions=None,
            ),
        ]
    )
    attach_db_set_prescriptions(
        day,
        meta_by_id={
            1: {
                "name_en": "Walking Lunge",
                "name_vi": "Bước tới",
                "movement_role": "compound",
                "movement_pattern": "lunge",
                "equipment_slugs": ["dumbbell"],
            },
        },
        fitness_baseline={
            "test_kit": "dumbbell",
            "db_press_reps": 12,
            "db_press_kg": 10,
            "goblet_reps": 12,
            "goblet_kg": 16,
        },
    )
    assert day.exercises[0].set_prescriptions is None


def test_one_arm_row_is_half_not_one_step_heavier():
    from types import SimpleNamespace

    from app.services.workout_generation.load_estimate import (
        attach_db_set_prescriptions,
        hint_for_item,
        apply_challenge_load,
    )

    loaded = apply_challenge_load(
        {
            "test_kit": "dumbbell",
            "db_row_reps": 12,
            "db_row_kg": 10,
            "db_press_reps": 12,
            "db_press_kg": 10,
        },
        weight_kg=70,
        equipment_list=["dumbbell"],
    )
    two = hint_for_item(
        {
            "name_en": "Dumbbell Row Bilateral",
            "name_vi": "Chèo tạ đơn hai tay",
            "movement_pattern": "h_pull",
            "equipment_slugs": ["dumbbell"],
        },
        loaded["_load_hints"],
    )
    one = hint_for_item(
        {
            "name_en": "Dumbbell Single Arm Row",
            "name_vi": "Chèo tạ đơn một tay",
            "movement_pattern": "h_pull",
            "equipment_slugs": ["dumbbell"],
        },
        loaded["_load_hints"],
    )
    assert two["load_kg_each"] == 10
    assert one["load_kg_each"] == 5.0

    day = SimpleNamespace(
        exercises=[
            SimpleNamespace(
                exercise_id=1,
                sets=3,
                reps="10-15",
                rest_seconds=120,
                rpe=None,
                section="main",
                notes_vi=None,
                set_prescriptions=None,
            ),
            SimpleNamespace(
                exercise_id=2,
                sets=3,
                reps="10-15",
                rest_seconds=120,
                rpe=None,
                section="main",
                notes_vi=None,
                set_prescriptions=None,
            ),
        ]
    )
    attach_db_set_prescriptions(
        day,
        meta_by_id={
            1: {
                "name_en": "Dumbbell Row Bilateral",
                "name_vi": "Chèo tạ đơn hai tay",
                "movement_role": "compound",
                "movement_pattern": "h_pull",
                "equipment_slugs": ["dumbbell"],
            },
            2: {
                "name_en": "Dumbbell Single Arm Row",
                "name_vi": "Chèo tạ đơn một tay",
                "movement_role": "compound",
                "movement_pattern": "h_pull",
                "equipment_slugs": ["dumbbell"],
            },
        },
        fitness_baseline=loaded,
    )
    assert day.exercises[0].set_prescriptions[0].load_note_vi == "Gợi ý: 10kg mỗi tay"
    assert day.exercises[1].set_prescriptions[0].load_note_vi == "Gợi ý: 5kg"


def test_overhead_press_with_dumbbell_slug_gets_load():
    from types import SimpleNamespace

    from app.services.workout_generation.load_estimate import attach_db_set_prescriptions

    day = SimpleNamespace(
        exercises=[
            SimpleNamespace(
                exercise_id=1,
                sets=3,
                reps="10-15",
                rest_seconds=120,
                rpe=None,
                section="main",
                notes_vi=None,
                set_prescriptions=None,
            ),
        ]
    )
    attach_db_set_prescriptions(
        day,
        meta_by_id={
            1: {
                "name_en": "Overhead Press",
                "name_vi": "Đẩy vai",
                "movement_role": "compound",
                "movement_pattern": "v_push",
                "equipment_slugs": ["dumbbell"],
            },
        },
        fitness_baseline={
            "test_kit": "dumbbell",
            "db_press_reps": 12,
            "db_press_kg": 10,
        },
    )
    assert day.exercises[0].set_prescriptions
    assert "kg" in (day.exercises[0].set_prescriptions[0].load_note_vi or "")


def test_goblet_keeps_full_bell_lunge_is_half():
    from types import SimpleNamespace

    from app.services.workout_generation.load_estimate import attach_db_set_prescriptions

    day = SimpleNamespace(
        exercises=[
            SimpleNamespace(
                exercise_id=1,
                sets=3,
                reps="8-12",
                rest_seconds=90,
                rpe=None,
                section="main",
                notes_vi=None,
                set_prescriptions=None,
            ),
            SimpleNamespace(
                exercise_id=2,
                sets=3,
                reps="12-16",
                rest_seconds=90,
                rpe=None,
                section="main",
                notes_vi=None,
                set_prescriptions=None,
            ),
        ]
    )
    attach_db_set_prescriptions(
        day,
        meta_by_id={
            1: {
                "name_en": "Dumbbell Goblet Squat",
                "name_vi": "Ngồi xổm ôm tạ đơn",
                "movement_role": "compound",
                "movement_pattern": "squat",
                "equipment_slugs": ["dumbbell"],
            },
            2: {
                "name_en": "Dumbbell Lateral Lunge",
                "name_vi": "Chùng chân sang ngang tạ đơn",
                "movement_role": "compound",
                "movement_pattern": "lunge",
                "equipment_slugs": ["dumbbell"],
            },
        },
        fitness_baseline={
            "test_kit": "dumbbell",
            "goblet_reps": 12,
            "goblet_kg": 30,
        },
    )
    goblet = day.exercises[0].set_prescriptions[0].load_note_vi
    lunge = day.exercises[1].set_prescriptions[0].load_note_vi
    assert goblet == "Gợi ý: 30kg"
    assert "mỗi tay" not in goblet
    assert lunge == "Gợi ý: 15kg"


def test_press_does_not_snap_20kg_each_hand():
    from app.services.workout_generation.load_estimate import snap_db_kg

    assert snap_db_kg(20, "press") == 17.5
    assert snap_db_kg(20, "squat") == 20.0
    assert snap_db_kg(7.5, "press") == 7.5


def test_mixed_kit_hints_keep_band_and_db():
    loaded = apply_challenge_load(
        {
            "db_press_reps": 12,
            "db_press_kg": 10,
            "band_level_pull": "blue",
            "pullups_max": 12,
        },
        weight_kg=70,
        equipment_list=["dumbbell", "resistance-band"],
    )
    assert any(h.get("load_kg_each") for h in loaded["_load_hints"] if h["pattern"] == "h_press")
    pull = next(h for h in loaded["_load_hints"] if h["pattern"] == "v_pull" and h.get("band_level"))
    assert pull["band_level"] == "blue"
    band_item = {
        "name_en": "Band Pulldown",
        "name_vi": "Kéo xô dây",
        "movement_role": "compound",
        "movement_pattern": "v_pull",
        "equipment_slugs": ["resistance-band-2"],
    }
    db_item = {
        "name_en": "Dumbbell Bench Press",
        "name_vi": "Đẩy ngực tạ đơn",
        "movement_role": "compound",
        "movement_pattern": "h_push",
        "equipment_slugs": ["dumbbell"],
    }
    assert hint_for_item(band_item, loaded["_load_hints"]).get("band_level") == "blue"
    assert hint_for_item(db_item, loaded["_load_hints"]).get("load_kg_each") == 10


def test_black_band_stacks_when_amrap_over_20():
    from app.services.workout_generation.load_estimate import progress_band_prescription

    color, extra = progress_band_prescription("black", 24, role="compound")
    assert color == "black"
    assert extra == "yellow"


def test_easy_steps_band_and_db_lighter_than_l3():
    from app.services.workout_generation.load_estimate import progress_band_prescription

    work, extra = progress_band_prescription("blue", 12, role="compound")
    easy, easy_extra = progress_band_prescription("blue", 12, role="compound", easy=True)
    assert work == "blue"
    assert extra is None
    assert easy == "red"
    assert easy_extra is None
    l3, _ = progress_db_prescription(10, 16, slot="press")
    l1, _ = progress_db_prescription(10, 16, slot="press", easy=True)
    assert l3 == 10
    assert l1 == 7.5


def test_db_working_kg_does_not_scale_by_phase():
    import inspect

    kwargs = {
        "test_kg": 10,
        "test_reps": 16,
        "slot": "press",
        "section": "main",
        "role": "compound",
        "item": {
            "name_en": "Dumbbell Bench Press",
            "name_vi": "Đẩy ngực tạ đơn",
            "movement_pattern": "h_push",
        },
    }
    a, _ = progress_db_prescription(**kwargs)
    b, _ = progress_db_prescription(**kwargs)
    assert a == b == 10
    assert "phase" not in inspect.signature(progress_db_prescription).parameters


def test_attach_fallback_gender_level_does_not_override_test():
    from types import SimpleNamespace

    from app.services.workout_generation.load_estimate import (
        attach_band_set_prescriptions,
        attach_db_set_prescriptions,
        default_band_level,
        default_db_kg,
    )

    assert default_band_level(gender="female", experience_level=1) == "yellow"
    assert default_db_kg(gender="female", experience_level=1, slot="press") == 2.5
    assert default_db_kg(gender="female", experience_level=1, slot="squat") == 5.0

    band_meta = {
        "name_en": "Band Chest Press",
        "name_vi": "Đẩy ngực với dây kháng lực",
        "movement_role": "compound",
        "equipment_slugs": ["resistance-band-2"],
    }
    db_meta = {
        "name_en": "Dumbbell Bench Press",
        "name_vi": "Đẩy ngực tạ đơn",
        "movement_role": "compound",
        "movement_pattern": "h_push",
        "equipment_slugs": ["dumbbell"],
    }

    def _day():
        return SimpleNamespace(
            exercises=[
                SimpleNamespace(
                    exercise_id=1,
                    sets=3,
                    reps="10",
                    rest_seconds=90,
                    rpe=None,
                    section="main",
                    notes_vi=None,
                    set_prescriptions=None,
                )
            ]
        )

    missing = _day()
    attach_band_set_prescriptions(
        missing,
        meta_by_id={1: band_meta},
        fitness_baseline={"gender": "female", "experience_level": 1},
    )
    assert len(missing.exercises[0].set_prescriptions) == 3
    assert missing.exercises[0].set_prescriptions[0].load_note_vi == (
        "Gợi ý: Dây vàng · 10 lbs"
    )

    tested = _day()
    attach_band_set_prescriptions(
        tested,
        meta_by_id={1: band_meta},
        fitness_baseline={
            "gender": "female",
            "experience_level": 1,
            "band_level": "blue",
        },
    )
    assert tested.exercises[0].set_prescriptions[0].load_note_vi == (
        "Gợi ý: Dây đỏ · 15 lbs"
    )

    db_missing = _day()
    attach_db_set_prescriptions(
        db_missing,
        meta_by_id={1: db_meta},
        fitness_baseline={"gender": "female", "experience_level": 1},
    )
    assert db_missing.exercises[0].set_prescriptions[0].load_note_vi == "Gợi ý: 2.5kg mỗi tay"

    db_tested = _day()
    attach_db_set_prescriptions(
        db_tested,
        meta_by_id={1: db_meta},
        fitness_baseline={
            "gender": "female",
            "experience_level": 1,
            "_easy": True,
            "db_press_kg": 10,
            "db_press_reps": 16,
        },
    )
    assert db_tested.exercises[0].set_prescriptions[0].load_note_vi == "Gợi ý: 7.5kg mỗi tay"


def test_attach_after_kit_wipe_matches_set_count():
    from types import SimpleNamespace

    from app.services.workout_generation.load_estimate import attach_band_set_prescriptions

    day = SimpleNamespace(
        exercises=[
            SimpleNamespace(
                exercise_id=1,
                sets=4,
                reps="8-12",
                rest_seconds=90,
                rpe=None,
                section="main",
                notes_vi=None,
                set_prescriptions=None,
            )
        ]
    )
    attach_band_set_prescriptions(
        day,
        meta_by_id={
            1: {
                "name_en": "Band Chest Press",
                "name_vi": "Đẩy ngực với dây",
                "movement_role": "compound",
                "equipment_slugs": ["resistance-band"],
            }
        },
        fitness_baseline={"band_level": "green"},
    )
    assert len(day.exercises[0].set_prescriptions) == 4
    assert day.exercises[0].set_prescriptions[0].load_note_vi == (
        "Gợi ý: Dây xanh lá · 25 lbs"
    )


def test_rep_windows_are_2_4_or_6_even():
    from types import SimpleNamespace

    from app.services.workout_generation.load_estimate import (
        attach_band_set_prescriptions,
        attach_db_set_prescriptions,
        prescribed_rep_label,
        rep_span_width,
        rep_window,
    )

    assert rep_window(16, width=4) == (8, 12)
    assert rep_window(15, width=2) == (10, 12)
    assert rep_window(8, width=2) == (4, 6)
    assert rep_window(15, width=6, isolation=True) == (10, 16)
    assert rep_span_width(role="compound", test_reps=16) == 4
    assert rep_span_width(role="compound", test_reps=25) == 2
    assert rep_span_width(role="compound", test_reps=8) == 2
    assert rep_span_width(role="isolation", test_reps=16) == 6
    assert prescribed_rep_label(16, role="compound", test_reps=16) == "8-12"
    assert prescribed_rep_label(15, role="compound", test_reps=25) == "10-12"
    assert prescribed_rep_label(15, role="compound", test_reps=8) == "10-12"
    assert prescribed_rep_label(15, role="isolation", test_reps=16) == "10-16"
    assert prescribed_rep_label(15, role="compound", has_test=False) == "8-12"
    assert prescribed_rep_label(15, role="isolation", has_test=False) == "12-18"

    band_meta = {
        "name_en": "Band Chest Press",
        "name_vi": "Đẩy ngực với dây",
        "movement_role": "compound",
        "equipment_slugs": ["resistance-band"],
    }
    iso_meta = {
        **band_meta,
        "name_en": "Band Fly",
        "name_vi": "Ép ngực dây",
        "movement_role": "isolation",
    }
    db_meta = {
        "name_en": "Dumbbell Bench Press",
        "name_vi": "Đẩy ngực tạ đơn",
        "movement_role": "compound",
        "movement_pattern": "h_push",
        "equipment_slugs": ["dumbbell"],
    }

    def _ex(eid=1, sets=3, reps="8-12", section="main"):
        return SimpleNamespace(
            exercise_id=eid,
            sets=sets,
            reps=reps,
            rest_seconds=90,
            rpe=None,
            section=section,
            notes_vi=None,
            set_prescriptions=None,
        )

    in_zone = SimpleNamespace(exercises=[_ex()])
    attach_band_set_prescriptions(
        in_zone,
        meta_by_id={1: band_meta},
        fitness_baseline={"band_level_push": "blue", "pushups_max": 16},
    )
    assert in_zone.exercises[0].reps == "8-12"
    assert in_zone.exercises[0].set_prescriptions[0].reps == "8-12"
    assert "Gợi ý:" in (in_zone.exercises[0].set_prescriptions[0].load_note_vi or "")
    assert len(in_zone.exercises[0].set_prescriptions) == 3

    bumped = SimpleNamespace(exercises=[_ex(sets=4)])
    attach_band_set_prescriptions(
        bumped,
        meta_by_id={1: band_meta},
        fitness_baseline={"band_level_push": "blue", "pushups_max": 25},
    )
    assert bumped.exercises[0].reps == "10-12"
    assert len(bumped.exercises[0].set_prescriptions) == 4

    low = SimpleNamespace(exercises=[_ex()])
    attach_db_set_prescriptions(
        low,
        meta_by_id={1: db_meta},
        fitness_baseline={"db_press_kg": 10, "db_press_reps": 8},
    )
    lo, hi = (int(x) for x in str(low.exercises[0].reps).split("-"))
    assert hi - lo == 2

    iso = SimpleNamespace(exercises=[_ex(eid=2)])
    attach_band_set_prescriptions(
        iso,
        meta_by_id={2: iso_meta},
        fitness_baseline={"band_level_push": "blue", "pushups_max": 16},
    )
    ilo, ihi = (int(x) for x in str(iso.exercises[0].reps).split("-"))
    assert ihi - ilo == 6

    fallback = SimpleNamespace(exercises=[_ex()])
    attach_band_set_prescriptions(
        fallback,
        meta_by_id={1: band_meta},
        fitness_baseline={"gender": "female", "experience_level": 1},
    )
    assert fallback.exercises[0].reps == "8-12"
    assert "Gợi ý:" in (fallback.exercises[0].set_prescriptions[0].load_note_vi or "")

    timed = SimpleNamespace(
        exercises=[_ex(reps="30 giây", section="main")]
    )
    attach_band_set_prescriptions(
        timed,
        meta_by_id={1: band_meta},
        fitness_baseline={"band_level": "blue", "pushups_max": 16},
    )
    assert timed.exercises[0].reps == "30 giây"


