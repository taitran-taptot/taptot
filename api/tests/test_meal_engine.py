"""Unit tests for nutrition clamps and deterministic meal assembler."""

from app.core.exceptions import BadRequestError
from app.services.workout_generation.meal_engine import (
    FoodView,
    USER_POOL_HELP,
    _is_ai_safe,
    apply_meals_with_schedule,
    build_day_templates,
    fit_meals_to_target,
    infer_roles,
    load_meal_pool,
    meal_total_calories,
    pool_is_ready,
    scale_items,
    PickedItem,
)
from app.services.workout_generation.nutrition_targets import (
    build_weekly_calorie_schedule,
    desired_calorie_adjustment,
    estimate_targets,
    targets_for_calories,
)


def _food(**kwargs) -> FoodView:
    base = dict(
        id=1,
        name_vi="Món",
        food_kind="ingredient",
        prep_state="cooked",
        is_complete_meal=False,
        roles=frozenset({"protein"}),
        slots=frozenset({"breakfast", "lunch", "dinner", "snack"}),
        calories=165,
        protein_g=31,
        carbs_g=0,
        fat_g=3.6,
        serving_size="100g",
        is_common=True,
        ai_priority=1,
        default_for_ai=True,
        raw=False,
    )
    base.update(kwargs)
    return FoodView(**base)


def test_calorie_adjustment_still_reports_desired_rate():
    assert desired_calorie_adjustment("lose_weight", {"kg_per_week": 0.5}) == -550
    assert desired_calorie_adjustment("lose_weight", {"kg_per_week": 1}) == -1100
    assert desired_calorie_adjustment("gain_weight", {"kg_per_week": 0.25}) == 275
    assert desired_calorie_adjustment("maintain", {"kg_per_week": 1}) == 0


def test_estimate_targets_uses_weekly_loss_rate():
    base = {
        "gender": "male",
        "weight_kg": 80,
        "height_cm": 175,
        "age": 30,
        "activity": "moderate",
        "goal": "lose_weight",
    }
    slow = estimate_targets({**base, "kg_per_week": 0.5})
    fast = estimate_targets({**base, "kg_per_week": 1})
    assert slow is not None and fast is not None
    assert fast.target_calories < slow.target_calories


def test_cut_follows_percent_bodyweight_without_calorie_caps():
    targets = estimate_targets(
        {
            "gender": "male",
            "weight_kg": 80,
            "height_cm": 175,
            "age": 30,
            "activity": "moderate",
            "goal": "lose_weight",
            "kg_per_week": 1,
        }
    )
    assert targets is not None
    # 80 kg × 1% = 0,8 kg/tuần → 880 kcal/ngày, không kẹp 25% TDEE / sàn calo.
    assert targets.tdee - targets.target_calories == 880
    assert not targets.clamped
    assert targets.protein_g == round(80 * 1.8, 1)


def test_maintain_protein_is_1_8():
    targets = estimate_targets(
        {
            "gender": "female",
            "weight_kg": 55,
            "height_cm": 160,
            "age": 28,
            "activity": "light",
            "goal": "maintain",
        }
    )
    assert targets is not None
    assert targets.target_calories == targets.tdee
    assert targets.protein_g == round(55 * 1.8, 1)
    assert targets.meals_per_day in {3, 4}


def test_pool_ready_requires_protein_and_carb_or_complete():
    chicken = _food(id=1, roles=frozenset({"protein"}))
    rice = _food(id=2, roles=frozenset({"carb"}), calories=195, protein_g=4, carbs_g=42)
    veg = _food(id=3, roles=frozenset({"produce"}), calories=20, protein_g=2, carbs_g=3)
    assert not pool_is_ready([chicken, rice])
    assert pool_is_ready([chicken, _food(id=4, roles=frozenset({"protein"})), rice, _food(id=5, roles=frozenset({"carb"}))])
    pho = _food(id=10, is_complete_meal=True, roles=frozenset({"complete"}), calories=450, protein_g=25, carbs_g=55)
    assert pool_is_ready([pho, pho, pho])
    assert pool_is_ready([pho, chicken, rice, veg])


def _realistic_pool() -> list[FoodView]:
    return [
        _food(id=1, name_vi="Ức gà", roles=frozenset({"protein"}), calories=165, protein_g=31),
        _food(id=2, name_vi="Cá hồi", roles=frozenset({"protein"}), calories=227, protein_g=25, fat_g=15),
        _food(id=8, name_vi="Thịt bò", roles=frozenset({"protein"}), calories=250, protein_g=26, fat_g=15),
        _food(id=9, name_vi="Trứng", roles=frozenset({"protein"}), calories=155, protein_g=13, fat_g=11),
        _food(id=3, name_vi="Cơm", roles=frozenset({"carb"}), calories=195, protein_g=4, carbs_g=42, fat_g=0.5),
        _food(id=4, name_vi="Khoai lang", roles=frozenset({"carb"}), calories=129, protein_g=2, carbs_g=30, fat_g=0.2),
        _food(id=10, name_vi="Bún", roles=frozenset({"carb"}), calories=110, protein_g=2, carbs_g=25, fat_g=0.2),
        _food(id=5, name_vi="Rau muống", roles=frozenset({"produce"}), calories=19, protein_g=2, carbs_g=3, fat_g=0.1),
        _food(id=11, name_vi="Bông cải", roles=frozenset({"produce"}), calories=25, protein_g=2, carbs_g=5, fat_g=0.3),
        _food(
            id=6,
            name_vi="Sữa chua",
            roles=frozenset({"dairy", "protein"}),
            slots=frozenset({"snack"}),
            calories=90,
            protein_g=8,
            carbs_g=12,
        ),
        _food(
            id=7,
            name_vi="Dầu olive",
            roles=frozenset({"fat"}),
            calories=884,
            protein_g=0,
            carbs_g=0,
            fat_g=100,
        ),
    ]


def _assert_within_10pct(actual: float, target: int) -> None:
    assert target > 0
    assert abs(actual - target) / target <= 0.10, f"{actual} vs {target}"


def test_fit_meals_within_10pct_maintain():
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
    pool = _realistic_pool()
    templates = build_day_templates(pool, targets, count=1)
    _assert_within_10pct(templates[0].totals["calories"], targets.target_calories)


def test_fit_meals_within_10pct_cut():
    targets = estimate_targets(
        {
            "gender": "male",
            "weight_kg": 80,
            "height_cm": 175,
            "age": 30,
            "activity": "moderate",
            "goal": "lose_weight",
            "kg_per_week": 0.5,
        }
    )
    assert targets is not None
    templates = build_day_templates(_realistic_pool(), targets, count=1)
    _assert_within_10pct(templates[0].totals["calories"], targets.target_calories)


def test_fit_meals_under_old_factor_would_fail():
    """Regression: old scale clamp 1.6 could not reach ~2000 kcal from ~400 kcal base."""
    base = estimate_targets(
        {
            "gender": "male",
            "weight_kg": 70,
            "height_cm": 170,
            "age": 25,
            "activity": "moderate",
            "goal": "maintain",
        }
    )
    assert base is not None
    targets = targets_for_calories(
        base, goal="maintain", weight_kg=70, target_calories=2000
    )
    items = [
        PickedItem(food=_food(id=1), meal_type="lunch", servings=1, role="protein", notes_vi=""),
        PickedItem(
            food=_food(id=2, roles=frozenset({"carb"}), calories=195, protein_g=4, carbs_g=42),
            meal_type="lunch",
            servings=1,
            role="carb",
            notes_vi="",
        ),
        PickedItem(
            food=_food(id=3, roles=frozenset({"produce"}), calories=25, protein_g=2, carbs_g=4),
            meal_type="lunch",
            servings=1,
            role="produce",
            notes_vi="",
        ),
    ]
    base_kcal = meal_total_calories(items)
    assert base_kcal < 500
    fitted, _ = fit_meals_to_target(items, targets)
    _assert_within_10pct(meal_total_calories(fitted), targets.target_calories)


def test_build_day_templates_totals_match_target():
    targets = estimate_targets(
        {
            "gender": "female",
            "weight_kg": 58,
            "height_cm": 162,
            "age": 27,
            "activity": "light",
            "goal": "lose_weight",
            "kg_per_week": 0.5,
        }
    )
    assert targets is not None
    for tmpl in build_day_templates(_realistic_pool(), targets, count=2):
        _assert_within_10pct(tmpl.totals["calories"], targets.target_calories)


def test_build_day_templates_prefers_slot_ids_and_still_fits_kcal():
    targets = estimate_targets(
        {
            "gender": "female",
            "weight_kg": 58,
            "height_cm": 162,
            "age": 27,
            "activity": "light",
            "goal": "lose_weight",
            "kg_per_week": 0.5,
        }
    )
    assert targets is not None
    tmpl = build_day_templates(
        _realistic_pool(),
        targets,
        count=1,
        preferred_by_slot={"breakfast": [2], "lunch": [2], "dinner": [2]},
    )[0]
    protein_ids = [
        m.food_id
        for m in tmpl.meals
        if m.meal_type in {"breakfast", "lunch", "dinner"}
    ]
    assert 2 in protein_ids
    _assert_within_10pct(tmpl.totals["calories"], targets.target_calories)


def test_apply_meals_with_schedule_matches_day_target():
    from app.schemas.plans import PlanDayIn

    targets = estimate_targets(
        {
            "gender": "male",
            "weight_kg": 78,
            "height_cm": 178,
            "age": 32,
            "activity": "moderate",
            "goal": "lose_weight",
            "kg_per_week": 0.5,
        }
    )
    assert targets is not None
    pool = _realistic_pool()
    roles = ["upper", "lower", "cardio"]
    schedule = build_weekly_calorie_schedule(
        goal="lose_weight",
        avg_target=targets.target_calories,
        split_roles=roles,
        gender="male",
        weight_kg=78,
        bmr=float(targets.bmr),
        base=targets,
    )
    templates_by_kind = {}
    foods_map = {f.id: f for f in pool}
    for slot in schedule.training:
        built = build_day_templates(pool, slot.targets, count=1)
        if built:
            templates_by_kind[slot.session_kind] = built[0]
    days = [
        PlanDayIn(day_number=i + 1, title_vi=f"Ngày {i + 1}", split_role=roles[i])
        for i in range(3)
    ]
    applied = apply_meals_with_schedule(
        days, schedule, templates_by_kind, foods_by_id=foods_map
    )
    for day, slot in zip(applied, schedule.training):
        assert day.target_calories == slot.targets.target_calories
        total = sum(
            foods_map[m.food_id].calories * float(m.servings or 1) for m in day.meals
        )
        _assert_within_10pct(total, slot.targets.target_calories)


def test_build_day_templates_macros_near_target():
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
    templates = build_day_templates(_realistic_pool(), targets, count=1)
    t = templates[0].totals
    assert t["protein_g"] >= targets.protein_g * 0.88
    assert t["protein_g"] <= targets.protein_g * 1.15
    assert t["fat_g"] >= targets.fat_g * 0.88
    assert abs(t["carbs_g"] - targets.carbs_g) / max(targets.carbs_g, 1) <= 0.15


def test_injects_fat_from_pool_for_lean_chicken_menu():
    """When menu is all lean protein, inject a fat-source food instead of overshooting protein."""
    peanut = _food(
        id=99,
        name_vi="Đậu phộng",
        roles=frozenset({"fat"}),
        calories=588,
        protein_g=25,
        carbs_g=16,
        fat_g=50,
    )
    pool = [
        _food(id=1, name_vi="Ức gà", roles=frozenset({"protein"}), calories=165, protein_g=31, fat_g=3.6),
        _food(id=2, roles=frozenset({"carb"}), calories=195, protein_g=4, carbs_g=42, fat_g=1),
        _food(id=3, roles=frozenset({"produce"}), calories=25, protein_g=2, carbs_g=4, fat_g=0),
        peanut,
    ]
    targets = estimate_targets(
        {
            "gender": "male",
            "weight_kg": 72,
            "height_cm": 172,
            "age": 30,
            "activity": "moderate",
            "goal": "maintain",
        }
    )
    assert targets is not None
    templates = build_day_templates(pool, targets, count=1)
    meal_ids = {m.food_id for m in templates[0].meals}
    assert 99 in meal_ids
    t = templates[0].totals
    assert t["fat_g"] >= targets.fat_g * 0.88
    assert t["protein_g"] <= targets.protein_g * 1.15


def test_scale_items_moves_toward_calorie_target():
    base = estimate_targets(
        {
            "gender": "male",
            "weight_kg": 70,
            "height_cm": 170,
            "age": 25,
            "activity": "moderate",
            "goal": "maintain",
        }
    )
    assert base is not None
    targets = targets_for_calories(
        base, goal="maintain", weight_kg=70, target_calories=2000
    )
    items = [
        PickedItem(food=_food(id=1, roles=frozenset({"protein"})), meal_type="lunch", servings=1, role="protein", notes_vi=""),
        PickedItem(
            food=_food(id=2, roles=frozenset({"carb"}), calories=195, protein_g=4, carbs_g=42),
            meal_type="lunch",
            servings=1,
            role="carb",
            notes_vi="",
        ),
        PickedItem(
            food=_food(id=3, roles=frozenset({"produce"}), calories=25, protein_g=2, carbs_g=4),
            meal_type="lunch",
            servings=1,
            role="produce",
            notes_vi="",
        ),
    ]
    scaled = scale_items(items, targets)
    kcal = meal_total_calories(scaled)
    _assert_within_10pct(kcal, targets.target_calories)


def test_build_templates_has_main_meals_and_no_duplicate_slot_stack():
    pool = [
        _food(id=1, name_vi="Ức gà sống", prep_state="raw", raw=True, roles=frozenset({"protein"})),
        _food(id=2, name_vi="Cá hồi", roles=frozenset({"protein"}), calories=227, protein_g=25),
        _food(id=3, name_vi="Cơm", roles=frozenset({"carb"}), calories=195, protein_g=4, carbs_g=42),
        _food(id=4, name_vi="Khoai lang", roles=frozenset({"carb"}), calories=129, protein_g=2, carbs_g=30),
        _food(id=5, name_vi="Rau muống", roles=frozenset({"produce"}), calories=19, protein_g=2, carbs_g=3),
        _food(
            id=6,
            name_vi="Phở bò",
            food_kind="dish",
            is_complete_meal=True,
            roles=frozenset({"complete"}),
            slots=frozenset({"lunch", "dinner"}),
            calories=450,
            protein_g=25,
            carbs_g=55,
            fat_g=12,
        ),
    ]
    targets = estimate_targets(
        {
            "gender": "male",
            "weight_kg": 70,
            "height_cm": 170,
            "age": 25,
            "activity": "moderate",
            "goal": "lose_weight",
            "kg_per_week": 0.5,
        }
    )
    assert targets is not None
    templates = build_day_templates(pool, targets, count=2)
    assert len(templates) == 2
    for tmpl in templates:
        types = [m.meal_type for m in tmpl.meals]
        assert "breakfast" in types
        assert "lunch" in types
        assert "dinner" in types
        _assert_within_10pct(tmpl.totals["calories"], targets.target_calories)
        # complete meal stays a single line in its slot
        by_slot: dict[str, list[int]] = {}
        for meal in tmpl.meals:
            by_slot.setdefault(meal.meal_type, []).append(meal.food_id)
        for slot, ids in by_slot.items():
            if 6 in ids:
                assert ids == [6], slot


def test_ai_safe_includes_raw_ingredients():
    raw_chicken = _food(id=1, prep_state="raw", raw=True, roles=frozenset({"protein"}))
    cooked_rice = _food(id=2, roles=frozenset({"carb"}), calories=195, protein_g=4, carbs_g=42)
    pho = _food(
        id=3,
        food_kind="dish",
        is_complete_meal=True,
        roles=frozenset({"complete"}),
        calories=450,
        protein_g=25,
        carbs_g=55,
    )
    drink = _food(id=4, roles=frozenset({"beverage"}), calories=40, protein_g=0, carbs_g=10)
    assert _is_ai_safe(raw_chicken)
    assert _is_ai_safe(cooked_rice)
    assert not _is_ai_safe(pho)
    assert not _is_ai_safe(drink)
    assert pool_is_ready(
        [
            raw_chicken,
            _food(id=5, prep_state="raw", raw=True, roles=frozenset({"protein"})),
            cooked_rice,
            _food(id=6, roles=frozenset({"carb"}), calories=129, protein_g=2, carbs_g=30),
        ]
    )


def test_user_pool_rejected_when_only_snacks(monkeypatch):
    class _Q:
        def filter(self, *args, **kwargs):
            return self

        def all(self):
            return []

    class _Db:
        def query(self, _model):
            return _Q()

    try:
        load_meal_pool(_Db(), {"ai_suggest_foods": False, "food_ids": [1, 2]})
        assert False, "expected BadRequestError"
    except BadRequestError as exc:
        assert "kho thức ăn" in exc.message or USER_POOL_HELP[:12] in exc.message


def test_infer_roles_from_macros():
    class Dummy:
        macro_roles = []
        tags = ["protein"]
        protein_g = 20
        carbs_g = 2
        is_complete_meal = False

    assert "protein" in infer_roles(Dummy())


def test_apply_meals_rotates_templates():
    from app.schemas.plans import PlanDayIn, PlanMealIn
    from app.services.workout_generation.meal_engine import DayTemplate, apply_meals_to_days

    days = [PlanDayIn(day_number=i, title_vi=f"D{i}") for i in range(1, 4)]
    t0 = DayTemplate(meals=[PlanMealIn(food_id=1, meal_type="lunch")], meal_notes={"lunch": "A"}, totals={})
    t1 = DayTemplate(meals=[PlanMealIn(food_id=2, meal_type="lunch")], meal_notes={"lunch": "B"}, totals={})
    out = apply_meals_to_days(days, [t0, t1])
    assert [d.meals[0].food_id for d in out] == [1, 2, 1]
    assert out[0].meal_notes["lunch"] == "A"


def test_rotation_index_changes_food_ids():
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
    pool = _realistic_pool()
    ids_by_rotation = []
    for rot in (0, 1, 2):
        tmpl = build_day_templates(pool, targets, count=1, rotation_index=rot)[0]
        ids_by_rotation.append(tuple(sorted(m.food_id for m in tmpl.meals)))
        _assert_within_10pct(tmpl.totals["calories"], targets.target_calories)
    assert len(set(ids_by_rotation)) >= 2


def test_generate_meals_with_blocks_rotates_without_preferred(monkeypatch):
    from unittest.mock import MagicMock

    from app.schemas.plans import PlanDayIn
    from app.services.workout_generation.meal_engine import generate_meals_with_blocks
    from app.services.workout_generation.nutrition_targets import (
        build_nutrition_blocks,
    )

    payload = {
        "gender": "male",
        "weight_kg": 75,
        "height_cm": 175,
        "age": 28,
        "activity": "moderate",
        "goal": "lose_weight",
        "kg_per_week": 0.5,
        "ai_suggest_foods": True,
    }
    pool = _realistic_pool()
    monkeypatch.setattr(
        "app.services.workout_generation.meal_engine.load_meal_pool",
        lambda db, payload: (pool, True),
    )
    blocks = build_nutrition_blocks(
        payload,
        goal="lose_weight",
        duration_weeks=14,
        split_roles=["push", "pull", "legs"],
        week_ranges=((1, 4), (5, 8), (9, 14)),
    )
    assert len(blocks) == 3
    days = [
        PlanDayIn(day_number=i + 1, title_vi=f"Ngày {i + 1}", split_role=role)
        for i, role in enumerate(["push", "pull", "legs"])
    ]
    db = MagicMock()
    query = db.query.return_value
    query.filter.return_value.all.return_value = pool
    result = generate_meals_with_blocks(
        db, payload, blocks, days, goal="lose_weight", block_size=4
    )
    assert result.nutrition_blocks
    assert len(result.nutrition_blocks) == 3
    menus = []
    for block in result.nutrition_blocks:
        ids = tuple(
            sorted(
                m["food_id"]
                for sess in (block.get("sessions") or [])
                for m in (sess.get("meals") or [])
            )
        )
        assert ids
        menus.append(ids)
    assert len(set(menus)) >= 2