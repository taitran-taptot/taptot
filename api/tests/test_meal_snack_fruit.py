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
    mains = [m for m in templates[0].meals if m.meal_type in {"breakfast", "lunch", "dinner"}]
    assert all(m.food_id != 30 for m in mains)
    assert isinstance(fruit, FoodView)


def test_main_meal_is_veg_and_one_or_two_protein_carb_or_one_dish():
    from dataclasses import replace

    from tests.test_meal_engine import _dish

    fruit = _food(
        id=30,
        name_vi="Chuối",
        roles=frozenset({"fruit", "produce"}),
        carbs_g=23,
        calories=89,
        protein_g=1,
        fat_g=0.3,
    )
    pho = _dish(id=20, name_vi="Phở bò")
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
    pool = _realistic_pool() + [fruit, pho]
    templates = build_day_templates(
        pool,
        targets,
        count=1,
        preferred_by_slot={"breakfast": [30], "lunch": [30, 20]},
        rotation_index=1,
    )
    meals = templates[0].meals
    assert all(m.food_id != 30 or m.meal_type == "snack" for m in meals)
    lunch = [m for m in meals if m.meal_type == "lunch"]
    assert [m.food_id for m in lunch] == [20]
    breakfast = [m for m in meals if m.meal_type == "breakfast"]
    roles = {m.food_id: next(f for f in pool if f.id == m.food_id).roles for m in breakfast}
    assert sum("produce" in roles[fid] and "fruit" not in roles[fid] for fid in roles) == 1
    assert 1 <= sum("protein" in roles[fid] for fid in roles) <= 2
    assert 1 <= sum("carb" in roles[fid] and "protein" not in roles[fid] for fid in roles) <= 2

    wide = replace(targets, protein_g=400, carbs_g=700)
    tiny = [
        _food(id=101, name_vi="Đạm nhỏ", roles=frozenset({"protein"}), protein_g=8, calories=80),
        _food(id=102, name_vi="Đạm nhỏ 2", roles=frozenset({"protein"}), protein_g=8, calories=80),
        _food(id=103, name_vi="Cơm nhỏ", roles=frozenset({"carb"}), carbs_g=15, calories=70, protein_g=1),
        _food(id=104, name_vi="Khoai nhỏ", roles=frozenset({"carb"}), carbs_g=15, calories=70, protein_g=1),
        _food(id=105, name_vi="Rau", roles=frozenset({"produce"}), calories=20, protein_g=1, carbs_g=3),
        _food(id=106, name_vi="Đạm nhỏ 3", roles=frozenset({"protein"}), protein_g=8, calories=80),
        _food(id=107, name_vi="Đạm nhỏ 4", roles=frozenset({"protein"}), protein_g=8, calories=80),
        _food(id=108, name_vi="Cơm nhỏ 3", roles=frozenset({"carb"}), carbs_g=15, calories=70, protein_g=1),
        _food(id=109, name_vi="Khoai nhỏ 4", roles=frozenset({"carb"}), carbs_g=15, calories=70, protein_g=1),
    ]
    built = build_day_templates(tiny, wide, count=1)
    breakfast = [m.food_id for m in built[0].meals if m.meal_type == "breakfast"]
    assert sum(breakfast.count(fid) for fid in (101, 102, 106, 107)) == 2
    assert sum(breakfast.count(fid) for fid in (103, 104, 108, 109)) == 2
    assert 105 in breakfast
