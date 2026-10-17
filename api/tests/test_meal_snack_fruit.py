from app.services.workout_generation.meal_engine import FoodView, build_day_templates
from app.services.workout_generation.nutrition_targets import estimate_targets
from tests.test_meal_engine import _food, _realistic_pool


def test_no_snack_without_fruit_in_pool():
    targets = estimate_targets(
        {
            "gender": "male",
            "weight_kg": 75,
            "height_cm": 175,
            "age": 28,
            "activity": "moderate",
            "goal": "maintain",
        }
    )
    assert targets is not None
    assert targets.meals_per_day >= 4
    templates = build_day_templates(_realistic_pool(), targets, count=1)
    types = {m.meal_type for m in templates[0].meals}
    assert "snack" not in types
    assert {"breakfast", "lunch", "dinner"} <= types


def test_snack_only_when_pool_has_fruit():
    fruit = _food(
        id=30,
        name_vi="Chuối",
        roles=frozenset({"fruit", "produce"}),
        carbs_g=23,
        calories=89,
        protein_g=1,
        fat_g=0.3,
    )
    targets = estimate_targets(
        {
            "gender": "male",
            "weight_kg": 75,
            "height_cm": 175,
            "age": 28,
            "activity": "moderate",
            "goal": "maintain",
        }
    )
    assert targets is not None
    templates = build_day_templates(_realistic_pool() + [fruit], targets, count=1)
    snacks = [m for m in templates[0].meals if m.meal_type == "snack"]
    assert snacks
    assert all(m.food_id == 30 for m in snacks)
    assert isinstance(fruit, FoodView)
