"""Unit tests for challenge_100_days chest A/B + phase exercise variation."""

from app.schemas.plans import PlanDayIn, PlanExerciseIn
from app.services.workout_generation.challenge_variation import (
    ChallengeVariationReport,
    apply_challenge_within_week_chest_ab,
    apply_phase_exercise_swaps,
    build_variation_pool,
    classify_bench_angle,
    ensure_chest_session_angles,
)
from app.services.workout_generation.phase_templates import build_mesocycle_week_templates


def test_classify_bench_angle_keywords():
    assert classify_bench_angle("Bench press", "Barbell Bench Press") == "flat"
    assert classify_bench_angle("Đẩy ngực dốc lên", "Incline DB Press") == "incline"
    assert classify_bench_angle("Đẩy ngực dốc xuống", "Decline Bench") == "decline"
    assert classify_bench_angle("Dip ngực", "Chest Dip") == "decline"
    assert classify_bench_angle("Lateral raise", None) == "unknown"


def _chest_meta():
    return {
        1: {
            "name_vi": "Đẩy ngực nằm",
            "name_en": "Flat Bench Press",
            "muscle_slug": "chest",
            "movement_pattern": "h_push",
            "movement_role": "compound",
        },
        2: {
            "name_vi": "Đẩy ngực dốc lên",
            "name_en": "Incline Press",
            "muscle_slug": "chest",
            "movement_pattern": "h_push",
            "movement_role": "compound",
        },
        3: {
            "name_vi": "Đẩy ngực dốc xuống",
            "name_en": "Decline Press",
            "muscle_slug": "chest",
            "movement_pattern": "h_push",
            "movement_role": "compound",
        },
        4: {
            "name_vi": "Đẩy vai",
            "name_en": "OHP",
            "muscle_slug": "shoulders",
            "movement_pattern": "v_push",
            "movement_role": "compound",
        },
        5: {
            "name_vi": "Ép ngực cáp",
            "name_en": "Cable Fly",
            "muscle_slug": "chest",
            "movement_pattern": "other",
            "movement_role": "isolation",
        },
        6: {
            "name_vi": "Ép ngực máy",
            "name_en": "Pec Deck",
            "muscle_slug": "chest",
            "movement_pattern": "other",
            "movement_role": "isolation",
        },
        7: {
            "name_vi": "Đẩy ngực dốc lên tạ đơn",
            "name_en": "Incline Dumbbell Press",
            "muscle_slug": "chest",
            "movement_pattern": "h_push",
            "movement_role": "compound",
        },
        8: {
            "name_vi": "Dip ngực",
            "name_en": "Chest Dip",
            "muscle_slug": "chest",
            "movement_pattern": "h_push",
            "movement_role": "compound",
        },
    }


def test_chest1_flat_plus_incline():
    meta = _chest_meta()
    pool = build_variation_pool(meta_by_id=meta)
    day = PlanDayIn(
        day_number=1,
        split_role="push",
        exercises=[
            PlanExerciseIn(exercise_id=1, sets=3, section="main"),
            PlanExerciseIn(exercise_id=1, sets=3, section="main"),  # duplicate flat
            PlanExerciseIn(exercise_id=4, sets=3, section="main"),
        ],
    )
    report = ChallengeVariationReport()
    out = ensure_chest_session_angles(
        day, variant="A", pool=pool, meta_by_id=meta, report=report
    )
    angles = [
        classify_bench_angle(
            meta[int(ex.exercise_id)].get("name_vi"),
            meta[int(ex.exercise_id)].get("name_en"),
        )
        for ex in out.exercises
        if (meta.get(int(ex.exercise_id)) or {}).get("muscle_slug") == "chest"
    ]
    assert "flat" in angles
    assert "incline" in angles
    assert out.exercises[2].exercise_id == 4  # OHP untouched


def test_chest2_flat_plus_incline_not_decline():
    meta = _chest_meta()
    pool = build_variation_pool(meta_by_id=meta)
    day = PlanDayIn(
        day_number=2,
        split_role="push",
        exercises=[
            PlanExerciseIn(exercise_id=1, sets=3, section="main"),
            PlanExerciseIn(exercise_id=2, sets=3, section="main"),
            PlanExerciseIn(exercise_id=4, sets=3, section="main"),
        ],
    )
    out = ensure_chest_session_angles(
        day, variant="B", pool=pool, meta_by_id=meta, report=ChallengeVariationReport()
    )
    chest_ids = [
        int(ex.exercise_id)
        for ex in out.exercises
        if (meta.get(int(ex.exercise_id)) or {}).get("muscle_slug") == "chest"
    ]
    angles = {
        classify_bench_angle(meta[i]["name_vi"], meta[i]["name_en"]) for i in chest_ids
    }
    assert "flat" in angles
    assert "incline" in angles
    assert "decline" not in angles
    assert 3 not in chest_ids
    assert 8 not in chest_ids
    assert out.exercises[2].exercise_id == 4  # OHP untouched


def test_missing_incline_fallback_logged():
    meta = {
        1: {
            "name_vi": "Flat bench",
            "name_en": "Flat Bench",
            "muscle_slug": "chest",
            "movement_pattern": "h_push",
            "movement_role": "compound",
        },
        9: {
            "name_vi": "Flat DB",
            "name_en": "Dumbbell Bench",
            "muscle_slug": "chest",
            "movement_pattern": "h_push",
            "movement_role": "compound",
        },
    }
    pool = build_variation_pool(meta_by_id=meta)
    day = PlanDayIn(
        day_number=1,
        split_role="push",
        exercises=[
            PlanExerciseIn(exercise_id=1, sets=3, section="main"),
            PlanExerciseIn(exercise_id=9, sets=3, section="main"),
        ],
    )
    report = ChallengeVariationReport()
    ensure_chest_session_angles(
        day, variant="B", pool=pool, meta_by_id=meta, report=report
    )
    assert any("no incline" in f for f in report.fallbacks)


def test_within_week_ab_two_push_days():
    meta = _chest_meta()
    pool = build_variation_pool(meta_by_id=meta)
    days = [
        PlanDayIn(
            day_number=1,
            split_role="push",
            exercises=[
                PlanExerciseIn(exercise_id=1, sets=3, section="main"),
                PlanExerciseIn(exercise_id=2, sets=3, section="main"),
            ],
        ),
        PlanDayIn(
            day_number=2,
            split_role="pull",
            exercises=[PlanExerciseIn(exercise_id=4, sets=3, section="main")],
        ),
        PlanDayIn(
            day_number=3,
            split_role="push",
            exercises=[
                PlanExerciseIn(exercise_id=1, sets=3, section="main"),
                PlanExerciseIn(exercise_id=2, sets=3, section="main"),
            ],
        ),
    ]
    report = ChallengeVariationReport()
    out = apply_challenge_within_week_chest_ab(
        days, pool=pool, meta_by_id=meta, report=report
    )
    assert report.chest_ab[0]["variant"] == "A"
    assert report.chest_ab[1]["variant"] == "B"
    a_angles = {
        classify_bench_angle(
            meta[int(ex.exercise_id)]["name_vi"], meta[int(ex.exercise_id)]["name_en"]
        )
        for ex in out[0].exercises
    }
    b_angles = {
        classify_bench_angle(
            meta[int(ex.exercise_id)]["name_vi"], meta[int(ex.exercise_id)]["name_en"]
        )
        for ex in out[2].exercises
    }
    assert "flat" in a_angles and "incline" in a_angles
    assert "flat" in b_angles and "incline" in b_angles
    assert "decline" not in b_angles


def test_phase_templates_diverge_exercise_ids():
    meta = _chest_meta()
    pool = build_variation_pool(meta_by_id=meta)
    day = PlanDayIn(
        day_number=1,
        split_role="push",
        exercises=[
            PlanExerciseIn(exercise_id=1, sets=3, rest_seconds=90, section="main"),
            PlanExerciseIn(exercise_id=2, sets=3, rest_seconds=90, section="main"),
            PlanExerciseIn(exercise_id=5, sets=3, rest_seconds=60, section="main"),
            PlanExerciseIn(exercise_id=4, sets=3, rest_seconds=90, section="main"),
        ],
    )
    report = ChallengeVariationReport()
    base = apply_challenge_within_week_chest_ab(
        [day], pool=pool, meta_by_id=meta, report=report
    )
    phases = build_mesocycle_week_templates(
        base,
        meta_by_id=meta,
        focus_slugs={"chest"},
        pool=pool,
        report=report,
    )
    p1_ids = [int(e.exercise_id) for e in phases[0][0].exercises]
    p2_ids = [int(e.exercise_id) for e in phases[1][0].exercises]
    # Flat neo (first chest compound that is flat) should stay across phases.
    flat_id = next(
        eid
        for eid in p1_ids
        if classify_bench_angle(meta[eid]["name_vi"], meta[eid]["name_en"]) == "flat"
    )
    assert flat_id in p2_ids
    # Secondary or iso should differ somewhere between phase1 and phase2 when pool allows.
    assert p1_ids != p2_ids or report.swaps_per_phase.get("intensification")
    assert "còn làm thêm" not in (phases[0][0].exercises[0].notes_vi or "")


def test_phase_swap_keeps_flat_neo():
    meta = _chest_meta()
    pool = build_variation_pool(meta_by_id=meta)
    day = PlanDayIn(
        day_number=1,
        split_role="push",
        exercises=[
            PlanExerciseIn(exercise_id=1, sets=3, section="main"),
            PlanExerciseIn(exercise_id=2, sets=3, section="main"),
            PlanExerciseIn(exercise_id=5, sets=3, section="main"),
        ],
    )
    report = ChallengeVariationReport()
    out = apply_phase_exercise_swaps(
        [day],
        phase_key="intensification",
        pool=pool,
        meta_by_id=meta,
        focus_slugs={"chest"},
        report=report,
    )
    assert out[0].exercises[0].exercise_id == 1


def test_lower_day_phases_rotate_accessories():
    meta = {
        20: {
            "name_vi": "Squat",
            "muscle_slug": "quads",
            "movement_pattern": "squat",
            "movement_role": "resistance",
        },
        21: {
            "name_vi": "Glute bridge",
            "muscle_slug": "glutes",
            "movement_pattern": "hinge",
            "movement_role": "isolation",
        },
        22: {
            "name_vi": "Hip thrust",
            "muscle_slug": "glutes",
            "movement_pattern": "other",
            "movement_role": "resistance",
        },
        23: {
            "name_vi": "RDL",
            "muscle_slug": "hamstrings",
            "movement_pattern": "hinge",
            "movement_role": "isolation",
        },
        24: {
            "name_vi": "Good morning",
            "muscle_slug": "hamstrings",
            "movement_pattern": "hinge",
            "movement_role": "resistance",
        },
    }
    pool = build_variation_pool(meta_by_id=meta)
    day = PlanDayIn(
        day_number=2,
        split_role="lower",
        exercises=[
            PlanExerciseIn(exercise_id=20, sets=3, section="main"),
            PlanExerciseIn(exercise_id=21, sets=3, section="main"),
            PlanExerciseIn(exercise_id=22, sets=3, section="main"),
        ],
    )
    phases = build_mesocycle_week_templates([day], meta_by_id=meta, pool=pool)
    p1 = [int(e.exercise_id) for e in phases[0][0].exercises]
    p2 = [int(e.exercise_id) for e in phases[1][0].exercises]
    p3 = [int(e.exercise_id) for e in phases[2][0].exercises]
    assert p1[0] == p2[0] == p3[0] == 20
    assert p1 != p2
    assert p2 != p3


def test_phase_specialization_does_not_keep_tate_as_neo():
    from app.services.workout_generation.muscle_quotas import CHEST_SLUGS

    meta = {
        **_chest_meta(),
        90: {
            "name_vi": "Ép tay sau nằm xoay cổ tay",
            "name_en": "Tate Press",
            "muscle_slug": "triceps",
            "movement_pattern": "h_push",
            "movement_role": "compound",
        },
    }
    pool = build_variation_pool(meta_by_id=meta)
    day = PlanDayIn(
        day_number=1,
        split_role="push",
        exercises=[
            PlanExerciseIn(exercise_id=90, sets=1, reps="4", section="warmup"),
            PlanExerciseIn(exercise_id=90, sets=3, section="main"),
            PlanExerciseIn(exercise_id=4, sets=3, section="main"),
            PlanExerciseIn(exercise_id=5, sets=3, section="main"),
        ],
    )
    report = ChallengeVariationReport()
    out = apply_phase_exercise_swaps(
        [day],
        phase_key="specialization",
        pool=pool,
        meta_by_id=meta,
        focus_slugs={"chest"},
        report=report,
    )
    first_main = next(e for e in out[0].exercises if e.section == "main")
    assert first_main.exercise_id != 90
    neo_meta = meta[int(first_main.exercise_id)]
    assert str(neo_meta.get("muscle_slug") or "") in CHEST_SLUGS
    primer = next(e for e in out[0].exercises if e.section == "warmup")
    assert primer.exercise_id == first_main.exercise_id
