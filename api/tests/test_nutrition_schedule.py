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


def test_carb_cycle_shifts_train_vs_rest_carbs():
    base = _base_nutrition()
    roles = ["upper", "lower"]
    kwargs = dict(
        goal="lose_weight",
        avg_target=base.target_calories,
        split_roles=roles,
        gender="male",
        weight_kg=75,
        bmr=float(base.bmr),
        base=base,
    )
    plain = build_weekly_calorie_schedule(**kwargs)
    cycled = build_weekly_calorie_schedule(**kwargs, carb_cycle=True)
    assert cycled.training[0].targets.carbs_g > plain.training[0].targets.carbs_g
    assert cycled.rest.carbs_g < plain.rest.carbs_g
    assert abs(cycled.training[0].targets.protein_g - plain.training[0].targets.protein_g) < 1.0


def test_refeed_raises_first_training_day_toward_tdee():
    base = _base_nutrition()
    roles = ["upper", "lower"]
    plain = build_weekly_calorie_schedule(
        goal="lose_weight",
        avg_target=base.target_calories,
        split_roles=roles,
        gender="male",
        weight_kg=75,
        bmr=float(base.bmr),
        base=base,
    )
    refeed = build_weekly_calorie_schedule(
        goal="lose_weight",
        avg_target=base.target_calories,
        split_roles=roles,
        gender="male",
        weight_kg=75,
        bmr=float(base.bmr),
        base=base,
        refeed=True,
    )
    assert refeed.training[0].targets.target_calories >= plain.training[0].targets.target_calories
    assert refeed.training[0].targets.carbs_g > plain.training[0].targets.carbs_g


def test_challenge_blocks_carb_cycle_only_l2_p3():
    from app.services.workout_generation.nutrition_targets import build_nutrition_blocks
    from app.services.workout_generation.session_policy import CHALLENGE_PHASE_RANGES

    payload = {
        "gender": "male",
        "weight_kg": 75,
        "height_cm": 175,
        "age": 28,
        "activity": "moderate",
        "goal": "lose_weight",
        "kg_per_week": 0.4,
    }
    roles = ["upper", "lower"]
    l1 = build_nutrition_blocks(
        payload,
        goal="lose_weight",
        duration_weeks=14,
        split_roles=roles,
        week_ranges=CHALLENGE_PHASE_RANGES,
        experience_level=1,
    )
    l2 = build_nutrition_blocks(
        payload,
        goal="lose_weight",
        duration_weeks=14,
        split_roles=roles,
        week_ranges=CHALLENGE_PHASE_RANGES,
        experience_level=2,
    )
    assert len(l1) == 3 and len(l2) == 3

    def _carb_ratio(block):
        train = block.schedule.training[0].targets.carbs_g
        rest = max(1.0, block.schedule.rest.carbs_g)
        return train / rest

    assert abs(_carb_ratio(l1[2]) - _carb_ratio(l1[0])) < 0.25
    assert _carb_ratio(l2[2]) > _carb_ratio(l2[0]) * 1.15
