"""Unit tests for the free-home 8-week beginner curriculum."""

from app.schemas.plans import PlanDayIn, PlanExerciseIn
from app.services.workout_generation.free_home_curriculum import (
    FREE_HOME_WEEKS,
    expand_free_home_weeks,
    normalize_foundation_motive,
    pick_nutrition_copy,
    plan_title_vi,
    scale_exercise_for_week,
)


def test_normalize_motive_defaults():
    assert normalize_foundation_motive(None) == "build_habit"
    assert normalize_foundation_motive("daily_energy") == "daily_energy"
    assert normalize_foundation_motive("nope") == "build_habit"


def test_plan_title_is_fitness_not_maintain():
    assert plan_title_vi("13/09/2026 12:00").startswith("Lịch tập cải thiện thể lực")


def test_nutrition_templates_differ_by_motive_and_seed():
    a, tips_a = pick_nutrition_copy("daily_energy", seed="u1")
    b, tips_b = pick_nutrition_copy("body_confidence", seed="u1")
    assert a
    assert b
    assert a != b
    assert "kiêng gắt" not in a
    assert tips_a and tips_b
    same_a, _ = pick_nutrition_copy("daily_energy", seed="u1")
    assert same_a == a
    assert "4 tuần" not in a
    assert "4 tuần" not in b


def test_free_home_session_dose_scales_with_minutes():
    from app.services.workout_generation.free_home_curriculum import (
        apply_free_home_session_timing,
        free_home_session_dose,
    )

    short = free_home_session_dose(30)
    long = free_home_session_dose(75)
    assert short["primer_sets"] == 1
    assert short["stretch_sets"] == 1
    assert short["main_sets"] == 2
    assert short["main_rest"] == 45
    assert long["primer_sets"] == 2
    assert long["stretch_sets"] == 2
    assert long["main_sets"] == 3
    assert long["main_rest"] == 60

    day = PlanDayIn(
        day_number=1,
        title_vi="Toàn thân",
        exercises=[
            PlanExerciseIn(
                exercise_id=1, sets=2, reps="30 giây", rest_seconds=30, section="warmup"
            ),
            PlanExerciseIn(exercise_id=10, sets=2, reps="4", rest_seconds=45, section="warmup"),
            PlanExerciseIn(exercise_id=10, sets=3, reps="10", rest_seconds=90, section="main"),
            PlanExerciseIn(
                exercise_id=2, sets=1, reps="8 phút", rest_seconds=0, section="cardio"
            ),
            PlanExerciseIn(
                exercise_id=3, sets=2, reps="30 giây", rest_seconds=20, section="cooldown"
            ),
        ],
    )
    apply_free_home_session_timing([day], session_minutes=30, experience_level=1)
    wu = [ex for ex in day.exercises if ex.section == "warmup"]
    assert wu[0].sets == 1
    assert wu[-1].sets == 1
    cardio = next(ex for ex in day.exercises if ex.section == "cardio")
    assert "phút" not in str(cardio.reps).lower()
    assert "giây" in str(cardio.reps).lower()
    assert cardio.sets >= 4
    assert cardio.rest_seconds > 0
    cool = next(ex for ex in day.exercises if ex.section == "cooldown")
    assert cool.sets == 1


def test_week_progression_sets():
    base = PlanExerciseIn(exercise_id=1, sets=3, reps="10", rest_seconds=90, section="main")
    w1 = scale_exercise_for_week(base, 1)
    w2 = scale_exercise_for_week(base, 2)
    w3 = scale_exercise_for_week(base, 3)
    w4 = scale_exercise_for_week(base, 4)
    w5 = scale_exercise_for_week(base, 5)
    w7 = scale_exercise_for_week(base, 7)
    w8 = scale_exercise_for_week(base, 8)
    assert w1.sets == 2
    assert w2.sets == 3
    assert w3.sets == 4
    assert w4.sets < w3.sets
    assert w4.rest_seconds >= w2.rest_seconds
    assert "chủ đích" in (w4.notes_vi or "")
    assert w5.sets >= w2.sets
    assert w7.sets >= w5.sets
    assert w7.sets >= w1.sets
    assert w8.sets < w7.sets
    assert "chủ đích" in (w8.notes_vi or "")


def test_expand_tags_weeks_and_volume():
    day = PlanDayIn(
        day_number=1,
        title_vi="Toàn thân",
        exercises=[
            PlanExerciseIn(exercise_id=1, sets=3, reps="10", rest_seconds=90, section="main"),
            PlanExerciseIn(exercise_id=2, sets=1, reps="5 phút", rest_seconds=60, section="cardio"),
        ],
    )
    expanded = expand_free_home_weeks([day], FREE_HOME_WEEKS)
    assert FREE_HOME_WEEKS == 8
    assert len(expanded) == 8
    assert "Giai đoạn 1" in (expanded[0].title_vi or "")
    assert "Giai đoạn 2" in (expanded[4].title_vi or "")
    assert "Nhẹ hơn" in (expanded[3].title_vi or "")
    assert "Nhẹ hơn" in (expanded[7].title_vi or "")
    assert "Nhẹ hơn" not in (expanded[5].title_vi or "")
    main_sets = [
        sum(e.sets for e in d.exercises if e.section == "main") for d in expanded
    ]
    assert main_sets[2] >= main_sets[0]
    assert main_sets[3] < main_sets[2]
    assert main_sets[6] >= main_sets[0]
    assert main_sets[7] < main_sets[6]


def test_expand_three_sessions_yields_twenty_four_days():
    days = [
        PlanDayIn(
            day_number=i,
            title_vi=f"Buổi {i}",
            exercises=[
                PlanExerciseIn(
                    exercise_id=i, sets=3, reps="10", rest_seconds=90, section="main"
                ),
            ],
        )
        for i in (1, 2, 3)
    ]
    expanded = expand_free_home_weeks(days, 8)
    assert len(expanded) == 24
