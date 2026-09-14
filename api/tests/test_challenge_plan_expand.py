"""Expand challenge week_templates the same way plan_service.create_plan does."""

from app.schemas.plans import PlanDayIn, PlanExerciseIn
from app.services.periodization import expand_plan_days_for_weeks
from app.services.workout_generation.meal_engine import apply_nutrition_blocks_to_expanded_days
from app.services.workout_generation.phase_templates import curriculum_insight_payload


def _day(title: str, exercise_id: int, sets: int = 3) -> PlanDayIn:
    return PlanDayIn(
        day_number=1,
        title_vi=title,
        split_role="push",
        exercises=[
            PlanExerciseIn(
                exercise_id=exercise_id,
                sets=sets,
                reps="8-12",
                rest_seconds=90,
                section="main",
            )
        ],
        meals=[],
    )


def test_plan_service_style_expand_from_insights():
    """Mirrors plan_service: reconstruct templates from dumps → expand 14 weeks."""
    phase1 = [_day("Push A", 10)]
    phase2 = [_day("Push B", 20)]
    phase3 = [_day("Push C", 30, sets=4)]
    week_templates_dump = [
        [d.model_dump() for d in phase1],
        [d.model_dump() for d in phase2],
        [d.model_dump() for d in phase3],
    ]
    templates = [
        [PlanDayIn(**d) for d in phase] for phase in week_templates_dump
    ]
    curriculum = curriculum_insight_payload()
    assert curriculum["deload_weeks"] == [4, 8, 14]

    days = expand_plan_days_for_weeks(
        templates[0],
        14,
        is_dict=False,
        experience_level=2,
        week_templates=templates,
        curriculum=True,
    )
    assert len(days) == 14
    assert "Push A" in (days[0].title_vi or "")
    assert "Push B" in (days[4].title_vi or "")
    assert "Push C" in (days[8].title_vi or "")
    assert "Push C" in (days[13].title_vi or "")
    for idx in (3, 7, 13):  # weeks 4, 8, 14
        assert "Deload" in (days[idx].title_vi or "")

    # Stamp nutrition like create_plan
    sessions = [
        {
            "split_role": "push",
            "target_calories": 2000,
            "target_protein_g": 140,
            "target_carbs_g": 200,
            "target_fat_g": 60,
            "meals": [],
            "meal_notes": {},
        }
    ]
    deload_sessions = [
        {
            **sessions[0],
            "target_calories": 2300,
        }
    ]
    nb = [
        {
            "block_index": i,
            "weeks": m["weeks"],
            "sessions": sessions,
            "deload_sessions": deload_sessions,
        }
        for i, m in enumerate(curriculum["mesocycles"])
    ]
    applied = apply_nutrition_blocks_to_expanded_days(
        days,
        nb,
        sessions_per_week=1,
        block_size=4,
        deload_weeks=curriculum["deload_weeks"],
    )
    assert applied[0].target_calories == 2000
    assert applied[3].target_calories == 2300
    assert applied[13].target_calories == 2300


def test_plan_service_style_expand_week_a_b_dict():
    """insights.week_templates as {a,b} per phase — even local weeks use B."""
    phase = {
        "a": [_day("Push A", 10, sets=3).model_dump()],
        "b": [_day("Push B", 20, sets=3).model_dump()],
    }
    week_templates_dump = [phase, phase, phase]
    templates = []
    for raw in week_templates_dump:
        a = [PlanDayIn(**d) for d in raw["a"]]
        b = [PlanDayIn(**d) for d in raw["b"]]
        templates.append({"a": a, "b": b})
    days = expand_plan_days_for_weeks(
        templates[0]["a"],
        14,
        is_dict=False,
        experience_level=2,
        week_templates=templates,
        curriculum=True,
    )
    assert len(days) == 14
    assert days[0].exercises[0].exercise_id == 10
    assert days[1].exercises[0].exercise_id == 20
    assert days[3].exercises[0].exercise_id == 10  # deload week 4 = A
    assert (days[3].exercises[0].sets or 0) < 3
    assert "Deload" in (days[3].title_vi or "")
