"""Tests for biweekly nutrition block projection and apply-after-expand."""

from copy import deepcopy

from app.schemas.plans import PlanDayIn, PlanExerciseIn
from app.services.periodization import expand_plan_days_for_weeks
from app.services.workout_generation.meal_engine import apply_nutrition_blocks_to_expanded_days
from app.services.workout_generation.nutrition_targets import (
    BLOCK_SIZE_WEEKS,
    MAX_BLOCK_CALORIE_DELTA,
    build_nutrition_blocks,
    build_weekly_calorie_schedule,
    clamp_block_avg_target,
    estimate_targets,
    projected_weight_kg,
)


def _lose_payload(**overrides):
    base = {
        "gender": "male",
        "weight_kg": 80,
        "height_cm": 175,
        "age": 30,
        "activity": "moderate",
        "goal": "lose_weight",
        "kg_per_week": 0.5,
    }
    base.update(overrides)
    return base


def _template_days(count: int = 3) -> list[PlanDayIn]:
    roles = ["upper", "lower", "cardio"]
    days: list[PlanDayIn] = []
    for i in range(count):
        days.append(
            PlanDayIn(
                day_number=i + 1,
                title_vi=f"Ngày {i + 1}",
                split_role=roles[i % len(roles)],
                exercises=[
                    PlanExerciseIn(exercise_id=1, sets=3, reps="10", section="main"),
                ],
                meals=[],
            )
        )
    return days


def test_projected_weight_decreases_on_cut():
    w0 = projected_weight_kg(80, goal="lose_weight", kg_per_week=0.5, block_index=0)
    w1 = projected_weight_kg(80, goal="lose_weight", kg_per_week=0.5, block_index=1)
    assert w0 == 80.0
    assert w1 == 79.0


def test_four_week_cut_block1_lower_calories():
    payload = _lose_payload()
    roles = [d.split_role for d in _template_days()]
    blocks = build_nutrition_blocks(
        payload, goal="lose_weight", duration_weeks=4, split_roles=roles
    )
    assert len(blocks) == 2
    assert blocks[1].schedule.avg_target < blocks[0].schedule.avg_target
    delta = blocks[0].schedule.avg_target - blocks[1].schedule.avg_target
    assert delta <= MAX_BLOCK_CALORIE_DELTA


def test_block_calorie_delta_clamped():
    assert clamp_block_avg_target(1800, 2000, "lose_weight") == 2000 - MAX_BLOCK_CALORIE_DELTA
    assert clamp_block_avg_target(2200, 2000, "gain_weight") == 2000 + MAX_BLOCK_CALORIE_DELTA


def test_each_block_weekly_schedule_balances():
    payload = _lose_payload()
    roles = [d.split_role for d in _template_days()]
    blocks = build_nutrition_blocks(
        payload, goal="lose_weight", duration_weeks=4, split_roles=roles
    )
    nut = estimate_targets(payload)
    assert nut is not None
    for block in blocks:
        sched = block.schedule
        total = sum(d.targets.target_calories for d in sched.training)
        total += sched.rest_days_per_week * sched.rest.target_calories
        assert abs(total - 7 * sched.avg_target) <= 10


def test_expand_weeks_three_four_differ_from_one_two():
    payload = _lose_payload()
    template = _template_days()
    roles = [d.split_role for d in template]
    blocks = build_nutrition_blocks(
        payload, goal="lose_weight", duration_weeks=4, split_roles=roles
    )
    block_insights = [
        {
            "block_index": b.block_index,
            "weeks": list(range(b.week_from, b.week_to + 1)),
            "projected_weight_kg": b.projected_weight_kg,
            "avg_target_calories": b.schedule.avg_target,
            "sessions": [
                {
                    "split_role": template[i].split_role,
                    "target_calories": b.schedule.training[i].targets.target_calories,
                    "target_protein_g": b.schedule.training[i].targets.protein_g,
                    "target_carbs_g": b.schedule.training[i].targets.carbs_g,
                    "target_fat_g": b.schedule.training[i].targets.fat_g,
                    "meals": [],
                    "meal_notes": {},
                }
                for i in range(len(template))
            ],
        }
        for b in blocks
    ]
    expanded = expand_plan_days_for_weeks(template, 4, is_dict=False, experience_level=1)
    applied = apply_nutrition_blocks_to_expanded_days(
        expanded,
        block_insights,
        sessions_per_week=len(template),
        block_size=BLOCK_SIZE_WEEKS,
    )
    w12 = [d for d in applied if "Tuần 1" in (d.title_vi or "") or "Tuần 2" in (d.title_vi or "")]
    w34 = [d for d in applied if "Tuần 3" in (d.title_vi or "") or "Tuần 4" in (d.title_vi or "")]
    avg12 = sum(d.target_calories or 0 for d in w12) / max(len(w12), 1)
    avg34 = sum(d.target_calories or 0 for d in w34) / max(len(w34), 1)
    assert avg34 < avg12


def test_curriculum_monthly_blocks():
    payload = _lose_payload()
    roles = [d.split_role for d in _template_days()]
    blocks = build_nutrition_blocks(
        payload,
        goal="lose_weight",
        duration_weeks=14,
        split_roles=roles,
        week_ranges=((1, 4), (5, 8), (9, 14)),
    )
    assert len(blocks) == 3
    assert blocks[0].week_from == 1 and blocks[0].week_to == 4
    assert blocks[1].week_from == 5 and blocks[1].week_to == 8
    assert blocks[2].week_from == 9 and blocks[2].week_to == 14
    assert blocks[2].schedule.avg_target <= blocks[0].schedule.avg_target
    assert blocks[0].schedule.avg_target - blocks[1].schedule.avg_target <= 250


def test_deload_week_avg_toward_tdee_on_cut():
    from app.services.workout_generation.nutrition_targets import deload_week_avg_target

    assert deload_week_avg_target(goal="lose_weight", block_avg=1800, tdee=2200) > 1800
    assert deload_week_avg_target(goal="lose_weight", block_avg=1800, tdee=2200) <= 2200
    assert deload_week_avg_target(goal="gain_weight", block_avg=2800, tdee=2500) == 2800


def _session(kcal: int, role: str = "upper") -> dict:
    return {
        "split_role": role,
        "target_calories": kcal,
        "target_protein_g": 150,
        "target_carbs_g": 180,
        "target_fat_g": 55,
        "meals": [],
        "meal_notes": {},
    }


def test_challenge_deload_weeks_use_deload_sessions():
    """Tuần 4/8/14 dùng deload_sessions; tuần khác dùng sessions thường; tuần 14 thuộc block 9–14."""
    template = _template_days(1)
    expanded = expand_plan_days_for_weeks(
        template, 14, is_dict=False, experience_level=1, curriculum=True
    )
    assert len(expanded) == 14

    block_insights = []
    for bi, (lo, hi) in enumerate(((1, 4), (5, 8), (9, 14))):
        normal = 2000 - bi * 50
        deload = normal + 200
        block_insights.append(
            {
                "block_index": bi,
                "weeks": list(range(lo, hi + 1)),
                "avg_target_calories": normal,
                "sessions": [_session(normal)],
                "deload_sessions": [_session(deload)],
            }
        )

    applied = apply_nutrition_blocks_to_expanded_days(
        expanded,
        block_insights,
        sessions_per_week=1,
        block_size=4,
        deload_weeks=[4, 8, 14],
    )

    by_week = {i + 1: applied[i] for i in range(14)}
    assert by_week[1].target_calories == 2000
    assert by_week[4].target_calories == 2200
    assert by_week[5].target_calories == 1950
    assert by_week[8].target_calories == 2150
    # Week 14 must match phase-3 block (index 2), not //4 wrong bucket
    assert by_week[14].target_calories == 2100
    assert by_week[13].target_calories == 1900


def test_challenge_without_deload_sessions_keeps_normal():
    template = _template_days(1)
    expanded = expand_plan_days_for_weeks(
        template, 14, is_dict=False, experience_level=1, curriculum=True
    )
    insights = [
        {
            "block_index": 0,
            "weeks": list(range(1, 15)),
            "sessions": [_session(1800)],
        }
    ]
    applied = apply_nutrition_blocks_to_expanded_days(
        expanded,
        insights,
        sessions_per_week=1,
        deload_weeks=[4, 8, 14],
    )
    assert all(d.target_calories == 1800 for d in applied)
