"""Tests for weekly calorie cycling (training vs rest, split types)."""

from app.services.workout_generation.nutrition_targets import (
    NutritionTargets,
    build_weekly_calorie_schedule,
    estimate_targets,
    split_role_category,
)


def _base_nutrition(**overrides) -> NutritionTargets:
    payload = {
        "gender": "male",
        "weight_kg": 75,
        "height_cm": 175,
        "age": 28,
        "activity": "moderate",
        "goal": "lose_weight",
        "kg_per_week": 0.5,
        **overrides,
    }
    nut = estimate_targets(payload)
    assert nut is not None
    return nut


def test_split_role_category():
    assert split_role_category("upper") == "strength"
    assert split_role_category("cardio") == "cardio"
    assert split_role_category("fb_a") == "fullbody"
    assert split_role_category("recovery") == "cardio"


def test_weekly_schedule_balances_seven_days():
    base = _base_nutrition()
    roles = ["upper", "lower", "cardio"]
    sched = build_weekly_calorie_schedule(
        goal="lose_weight",
        avg_target=base.target_calories,
        split_roles=roles,
        gender="male",
        weight_kg=75,
        bmr=float(base.bmr),
        base=base,
    )
    train_sum = sum(d.targets.target_calories for d in sched.training)
    total = train_sum + sched.rest_days_per_week * sched.rest.target_calories
    assert abs(total - 7 * sched.avg_target) <= 10


def test_strength_higher_than_cardio_on_cut():
    base = _base_nutrition()
    roles = ["upper", "cardio"]
    sched = build_weekly_calorie_schedule(
        goal="lose_weight",
        avg_target=base.target_calories,
        split_roles=roles,
        gender="male",
        weight_kg=75,
        bmr=float(base.bmr),
        base=base,
    )
    strength = next(d for d in sched.training if d.session_kind == "strength")
    cardio = next(d for d in sched.training if d.session_kind == "cardio")
    assert strength.targets.target_calories > cardio.targets.target_calories


def test_rest_lower_than_training():
    base = _base_nutrition()
    roles = ["upper", "lower", "push"]
    sched = build_weekly_calorie_schedule(
        goal="lose_weight",
        avg_target=base.target_calories,
        split_roles=roles,
        gender="male",
        weight_kg=75,
        bmr=float(base.bmr),
        base=base,
    )
    max_train = max(d.targets.target_calories for d in sched.training)
    assert sched.rest.target_calories < max_train
