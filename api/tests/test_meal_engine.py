"""Unit tests for nutrition clamps and deterministic meal assembler."""

from app.core.exceptions import BadRequestError
from app.services.workout_generation.meal_engine import (
    FoodView,
    USER_POOL_HELP,
    USER_POOL_MAX,
    _ai_safe_pool,
    _is_ai_safe,
    _is_lean_ingredient,
    _load_foods_by_ids,
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


def test_pool_ready_requires_two_protein_carb_produce():
    chicken = _food(id=1, roles=frozenset({"protein"}))
    beef = _food(id=4, roles=frozenset({"protein"}))
    rice = _food(id=2, roles=frozenset({"carb"}), calories=195, protein_g=4, carbs_g=42)
    bun = _food(id=5, roles=frozenset({"carb"}), calories=110, protein_g=2, carbs_g=25)
    veg = _food(id=3, roles=frozenset({"produce"}), calories=20, protein_g=2, carbs_g=3)
    veg2 = _food(id=6, roles=frozenset({"produce"}), calories=25, protein_g=2, carbs_g=5)
    assert not pool_is_ready([chicken, rice])
    assert not pool_is_ready([chicken, beef, rice, bun])
    assert pool_is_ready([chicken, beef, rice, bun, veg, veg2])
    pho = _food(id=10, is_complete_meal=True, roles=frozenset({"complete"}), calories=450, protein_g=25, carbs_g=55)
    assert not pool_is_ready([pho, pho, pho])
    assert not pool_is_ready([pho, chicken, rice, veg])


class _DummyFood:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", 1)
        self.name_vi = kwargs.get("name_vi", "Món")
        self.food_kind = kwargs.get("food_kind", "ingredient")
        self.prep_state = kwargs.get("prep_state", "cooked")
        self.is_complete_meal = kwargs.get("is_complete_meal", False)
        self.macro_roles = kwargs.get("macro_roles", ["protein"])
        self.meal_slots = kwargs.get("meal_slots", ["breakfast", "lunch", "dinner", "snack"])
        self.tags = kwargs.get("tags", [])
        self.calories = kwargs.get("calories", 165)
        self.protein_g = kwargs.get("protein_g", 31)
        self.carbs_g = kwargs.get("carbs_g", 0)
        self.fat_g = kwargs.get("fat_g", 3.6)
        self.serving_size = kwargs.get("serving_size", "100g")
        self.is_common = kwargs.get("is_common", True)
        self.ai_priority = kwargs.get("ai_priority", 1)
        self.default_for_ai = kwargs.get("default_for_ai", True)
        self.region_slug = kwargs.get("region_slug", None)
        self.image_url = kwargs.get("image_url", None)


class _FoodQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self._rows


class _FoodDb:
    def __init__(self, rows):
        self._rows = rows

    def query(self, _model):
        return _FoodQuery(self._rows)


def test_ai_pool_drops_foods_without_image_url():
    with_photo = _DummyFood(id=1, image_url="foods/uc-ga-khong-da.jpg")
    without_photo = _DummyFood(id=2, image_url=None, name_vi="Không ảnh")
    pool = _ai_safe_pool(_FoodDb([with_photo, without_photo]))
    assert [f.id for f in pool] == [1]
    assert pool[0].image_url == "foods/uc-ga-khong-da.jpg"


def test_ai_pool_keeps_foods_with_image_url():
    chicken = _DummyFood(
        id=1,
        image_url="foods/uc-ga.jpg",
        macro_roles=["protein"],
        calories=165,
        protein_g=31,
    )
    fish = _DummyFood(
        id=2,
        image_url="foods/ca-hoi.jpg",
        macro_roles=["protein"],
        calories=200,
        protein_g=22,
    )
    rice = _DummyFood(
        id=3,
        image_url="foods/com-trang.jpg",
        macro_roles=["carb"],
        calories=195,
        protein_g=4,
        carbs_g=42,
    )
    potato = _DummyFood(
        id=4,
        image_url="foods/khoai-lang.jpg",
        macro_roles=["carb"],
        calories=129,
        protein_g=2,
        carbs_g=30,
    )
    greens = _DummyFood(
        id=5,
        image_url="foods/rau-muong.jpg",
        macro_roles=["produce"],
        calories=19,
        protein_g=2,
        carbs_g=3,
    )
    broccoli = _DummyFood(
        id=6,
        image_url="foods/bong-cai.jpg",
        macro_roles=["produce"],
        calories=25,
        protein_g=2,
        carbs_g=5,
    )
    pool = _ai_safe_pool(_FoodDb([chicken, fish, rice, potato, greens, broccoli]))
    assert {f.id for f in pool} == {1, 2, 3, 4, 5, 6}
    assert pool_is_ready(pool)


def test_user_pool_keeps_foods_without_image_url():
    rows = [
        _DummyFood(id=1, image_url="foods/uc-ga.jpg", macro_roles=["protein"]),
        _DummyFood(id=2, image_url=None, macro_roles=["protein"], name_vi="Trứng"),
        _DummyFood(
            id=3,
            image_url="foods/com-trang.jpg",
            macro_roles=["carb"],
            calories=195,
            protein_g=4,
            carbs_g=42,
        ),
        _DummyFood(
            id=4,
            image_url="foods/khoai-lang.jpg",
            macro_roles=["carb"],
            calories=129,
            protein_g=2,
            carbs_g=30,
        ),
        _DummyFood(
            id=5,
            image_url="foods/rau-muong.jpg",
            macro_roles=["produce"],
            calories=19,
            protein_g=2,
            carbs_g=3,
        ),
        _DummyFood(id=6, image_url=None, macro_roles=["produce"], name_vi="Cải thìa", calories=19, protein_g=2, carbs_g=3),
    ]
    pool = _load_foods_by_ids(_FoodDb(rows), [1, 2, 3, 4, 5, 6])
    assert [f.id for f in pool] == [1, 2, 3, 4, 5, 6]
    assert pool_is_ready(pool)


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
    bun = _food(
        id=9,
        name_vi="Bún bò",
        food_kind="ingredient",
        is_complete_meal=False,
        region_slug="viet-nam",
        roles=frozenset({"protein", "carb"}),
    )
    tagged = _food(
        id=10,
        name_vi="Cơm tấm",
        tags=frozenset({"complete_meal"}),
        roles=frozenset({"protein", "carb"}),
    )
    assert _is_ai_safe(bun)
    assert _is_ai_safe(tagged)
    assert not _is_lean_ingredient(bun)
    assert not _is_lean_ingredient(tagged)
    assert _is_lean_ingredient(raw_chicken)
    assert _is_lean_ingredient(cooked_rice)
    assert pool_is_ready(
        [
            raw_chicken,
            _food(id=5, prep_state="raw", raw=True, roles=frozenset({"protein"})),
            cooked_rice,
            _food(id=6, roles=frozenset({"carb"}), calories=129, protein_g=2, carbs_g=30),
            _food(id=7, roles=frozenset({"produce"}), calories=19, protein_g=2, carbs_g=3),
            _food(id=8, roles=frozenset({"produce"}), calories=25, protein_g=2, carbs_g=5),
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


def test_user_pool_rejected_when_over_max():
    ids = list(range(1, USER_POOL_MAX + 2))
    try:
        load_meal_pool(None, {"ai_suggest_foods": False, "food_ids": ids})
        assert False, "expected BadRequestError"
    except BadRequestError as exc:
        assert USER_POOL_HELP[:12] in exc.message


def test_infer_roles_from_macros():
    class Dummy:
        macro_roles = []
        tags = ["protein"]
        protein_g = 20
        carbs_g = 2
        is_complete_meal = False

    assert "protein" in infer_roles(Dummy())


def test_potato_and_corn_are_carb_not_produce():
    class Food:
        def __init__(self, **kwargs):
            self.macro_roles = kwargs.get("macro_roles", [])
            self.tags = kwargs.get("tags", ["rau", "carb"])
            self.protein_g = 2
            self.carbs_g = 20
            self.is_complete_meal = False
            self.slug = kwargs.get("slug")
            self.name_vi = kwargs.get("name_vi")
            self.name_en = kwargs.get("name_en")

    sweet = infer_roles(Food(slug="khoai-lang", name_vi="Khoai lang luộc", name_en="Sweet potato boiled"))
    corn = infer_roles(Food(slug="bap-ngot", name_vi="Bắp ngọt", name_en="Sweet corn, raw kernels"))
    cabbage = infer_roles(
        Food(slug="cai-bap", name_vi="Cải bắp", name_en="Cabbage", tags=["rau"], carbs_g=6)
    )
    assert sweet == {"carb"}
    assert corn == {"carb"}
    assert "produce" in cabbage
    assert "carb" not in cabbage


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


def _dish(**kwargs) -> FoodView:
    base = dict(
        food_kind="dish",
        is_complete_meal=True,
        roles=frozenset({"complete"}),
        calories=520,
        protein_g=28,
        carbs_g=68,
        fat_g=12,
        serving_size="1 suất",
    )
    base.update(kwargs)
    return _food(**base)


def test_pool_ready_with_dish_and_two_protein_two_carb_two_produce():
    pho = _dish(id=20, name_vi="Phở bò")
    chicken = _food(id=1, roles=frozenset({"protein"}))
    beef = _food(id=2, roles=frozenset({"protein"}))
    rice = _food(id=3, roles=frozenset({"carb"}), calories=195, protein_g=4, carbs_g=42)
    bun = _food(id=4, roles=frozenset({"carb"}), calories=110, protein_g=2, carbs_g=25)
    veg = _food(id=5, roles=frozenset({"produce"}), calories=19, protein_g=2, carbs_g=3)
    veg2 = _food(id=6, roles=frozenset({"produce"}), calories=25, protein_g=2, carbs_g=5)
    assert not pool_is_ready([pho, chicken, beef, rice, bun])
    assert pool_is_ready([pho, chicken, beef, rice, bun, veg, veg2])


def test_complete_meal_stays_one_serving_and_ingredients_hit_target():
    from app.services.workout_generation.meal_engine import _serving_bounds, _item

    pho = _dish(id=20, name_vi="Phở bò")
    chicken = _food(id=1, roles=frozenset({"protein"}))
    rice = _food(id=3, roles=frozenset({"carb"}), calories=195, protein_g=4, carbs_g=42, fat_g=0.5)
    veg = _food(id=5, roles=frozenset({"produce"}), calories=19, protein_g=2, carbs_g=3, fat_g=0.1)
    fruit = _food(
        id=12,
        name_vi="Chuối",
        roles=frozenset({"fruit", "produce"}),
        calories=89,
        protein_g=1,
        carbs_g=23,
        fat_g=0.3,
        tags=frozenset({"trai-cay"}),
    )
    item = _item(pho, "lunch", "complete")
    assert _serving_bounds(item) == (1.0, 1.0)

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
    picked = [
        _item(chicken, "breakfast", "protein"),
        _item(rice, "breakfast", "carb"),
        _item(veg, "breakfast", "produce"),
        _item(pho, "lunch", "complete"),
        _item(chicken, "dinner", "protein"),
        _item(rice, "dinner", "carb"),
        _item(fruit, "dinner", "produce"),
    ]
    fitted, _warn = fit_meals_to_target(picked, targets, pool=_realistic_pool() + [pho, fruit])
    dish = [row for row in fitted if row.food.id == 20]
    assert dish and dish[0].servings == 1.0
    total = sum(row.food.calories * row.servings for row in fitted)
    assert abs(total - targets.target_calories) / targets.target_calories <= 0.12


def test_build_day_templates_rotates_dish_not_every_meal():
    pool = _realistic_pool() + [
        _dish(id=20, name_vi="Phở bò"),
        _dish(id=21, name_vi="Bún chả", calories=480, protein_g=26, carbs_g=55, fat_g=14),
    ]
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
    templates = build_day_templates(pool, targets, count=2)
    assert len(templates) == 2
    dish_ids = {20, 21}
    slots_by_day: list[list[str]] = []
    for tmpl in templates:
        dish_meals = [m for m in tmpl.meals if m.food_id in dish_ids]
        assert len(dish_meals) == 1, [m.meal_type for m in dish_meals]
        assert dish_meals[0].meal_type in {"breakfast", "lunch", "dinner"}
        assert float(dish_meals[0].servings) == 1.0
        slots_by_day.append([m.meal_type for m in dish_meals])
        _assert_within_10pct(tmpl.totals["calories"], targets.target_calories)
    assert slots_by_day[0] != slots_by_day[1]


def _maintain_targets():
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
    return targets


def _meals_by_slot(tmpl) -> dict[str, list[int]]:
    grouped: dict[str, list[int]] = {}
    for meal in tmpl.meals:
        grouped.setdefault(meal.meal_type, []).append(meal.food_id)
    return grouped


def test_main_meals_include_protein_carb_and_produce_regardless_of_saved_slot():
    chicken = _food(
        id=1,
        name_vi="Ức gà",
        roles=frozenset({"protein"}),
        slots=frozenset({"lunch"}),
    )
    rice = _food(
        id=2,
        name_vi="Cơm",
        roles=frozenset({"carb"}),
        slots=frozenset({"lunch"}),
        calories=195,
        protein_g=4,
        carbs_g=42,
    )
    veg = _food(
        id=3,
        name_vi="Rau muống",
        roles=frozenset({"produce"}),
        slots=frozenset({"dinner"}),
        calories=19,
        protein_g=2,
        carbs_g=3,
    )
    fruit = _food(
        id=4,
        name_vi="Chuối",
        roles=frozenset({"fruit"}),
        slots=frozenset({"snack"}),
        calories=89,
        protein_g=1,
        carbs_g=23,
    )
    templates = build_day_templates([chicken, rice, veg, fruit], _maintain_targets(), count=1)
    assert templates
    notes = templates[0].meal_notes["breakfast"]
    assert "một món chế biến" in notes
    assert "tinh bột kèm thịt và rau" in notes
    by_slot = _meals_by_slot(templates[0])
    for slot in ("breakfast", "lunch", "dinner"):
        ids = set(by_slot[slot])
        assert {1, 2, 3} <= ids, slot
    assert by_slot["snack"] == [4]


def test_rice_plus_dish_without_breakfast_slot_is_only_the_dish():
    rice = _food(
        id=2,
        name_vi="Cơm",
        roles=frozenset({"carb"}),
        slots=frozenset({"breakfast"}),
        calories=195,
        protein_g=4,
        carbs_g=42,
    )
    pho = _dish(id=20, name_vi="Phở bò", slots=frozenset({"lunch", "dinner"}))
    templates = build_day_templates([rice, pho], _maintain_targets(), count=1)
    assert templates
    by_slot = _meals_by_slot(templates[0])
    for slot in ("breakfast", "lunch", "dinner"):
        assert by_slot[slot] == [20], slot


def test_pool_with_dish_and_full_plate_has_no_carb_only_main_meal():
    pool = _realistic_pool() + [_dish(id=20, name_vi="Phở bò", slots=frozenset({"lunch"}))]
    carb_ids = {3, 4, 10}
    templates = build_day_templates(pool, _maintain_targets(), count=2)
    assert len(templates) == 2
    for tmpl in templates:
        by_slot = _meals_by_slot(tmpl)
        for slot in ("breakfast", "lunch", "dinner"):
            ids = by_slot[slot]
            assert ids != [] and not set(ids) <= carb_ids, slot
            if 20 in ids:
                assert ids == [20], slot


def test_main_meal_caps_each_group_at_two_foods():
    foods: list[FoodView] = []
    for index in range(6):
        foods.append(
            _food(
                id=index + 1,
                name_vi=f"Gà {index}",
                roles=frozenset({"protein"}),
                calories=80,
                protein_g=4,
                carbs_g=0,
                fat_g=1,
            )
        )
        foods.append(
            _food(
                id=index + 11,
                name_vi=f"Cơm {index}",
                roles=frozenset({"carb"}),
                calories=80,
                protein_g=1,
                carbs_g=4,
                fat_g=0,
            )
        )
        foods.append(
            _food(
                id=index + 21,
                name_vi=f"Rau {index}",
                roles=frozenset({"produce"}),
                calories=30,
                protein_g=1,
                carbs_g=4,
                fat_g=0,
            )
        )
    templates = build_day_templates(foods, _maintain_targets(), count=1)
    assert templates
    by_slot = _meals_by_slot(templates[0])
    saw_two_proteins = False
    for slot in ("breakfast", "lunch", "dinner"):
        ids = by_slot[slot]
        proteins = [fid for fid in ids if fid <= 6]
        carbs = [fid for fid in ids if 11 <= fid <= 16]
        produce = [fid for fid in ids if 21 <= fid <= 26]
        assert 1 <= len(proteins) <= 2, slot
        assert 1 <= len(carbs) <= 2, slot
        assert 1 <= len(produce) <= 2, slot
        saw_two_proteins = saw_two_proteins or len(proteins) == 2
    assert saw_two_proteins


def _line_grams(servings: float, serving_grams: float = 100) -> float:
    return servings * serving_grams


def _olive_oil() -> FoodView:
    return _food(
        id=99,
        name_vi="Dầu oliu",
        slug="dau-oliu",
        roles=frozenset({"fat"}),
        serving_grams=14,
        serving_size="1 muỗng canh (14g)",
        calories=123.8,
        protein_g=0,
        carbs_g=0,
        fat_g=14,
    )


def _lean_plate() -> list[FoodView]:
    return [
        _food(
            id=1,
            name_vi="Ức gà",
            roles=frozenset({"protein"}),
            calories=165,
            protein_g=31,
            fat_g=3.6,
            serving_grams=100,
        ),
        _food(
            id=2,
            name_vi="Cơm",
            roles=frozenset({"carb"}),
            calories=195,
            protein_g=4,
            carbs_g=42,
            fat_g=0.5,
            serving_grams=100,
        ),
        _food(
            id=3,
            name_vi="Rau muống",
            roles=frozenset({"produce"}),
            calories=19,
            protein_g=2,
            carbs_g=3,
            fat_g=0.2,
            serving_grams=100,
        ),
    ]


def test_main_meals_keep_meat_and_vegetables_in_gram_bands():
    templates = build_day_templates(_lean_plate(), _maintain_targets(), count=1)
    assert templates
    by_slot = _meals_by_slot(templates[0])
    for slot in ("breakfast", "lunch", "dinner"):
        ids = by_slot[slot]
        meals = [m for m in templates[0].meals if m.meal_type == slot]
        meat = sum(_line_grams(m.servings) for m in meals if m.food_id == 1)
        veg = sum(_line_grams(m.servings) for m in meals if m.food_id == 3)
        assert meat >= 80, slot
        assert 100 <= veg <= 200, (slot, veg, ids)


def test_missing_fat_adds_one_olive_oil_line_and_keeps_calories():
    oil = _olive_oil()
    templates = build_day_templates(_lean_plate(), _maintain_targets(), count=1, fallback_fat=oil)
    assert templates
    meals = templates[0].meals
    oil_lines = [m for m in meals if m.food_id == oil.id]
    assert len(oil_lines) == 1
    assert oil_lines[0].meal_type in {"breakfast", "lunch", "dinner"}
    assert _line_grams(oil_lines[0].servings, 14) <= 28.01
    _assert_within_10pct(templates[0].totals["calories"], _maintain_targets().target_calories)
    for slot in ("breakfast", "lunch", "dinner"):
        veg = sum(_line_grams(m.servings) for m in meals if m.meal_type == slot and m.food_id == 3)
        if veg:
            assert veg <= 200, slot


def test_existing_fat_food_blocks_olive_oil_fallback():
    oil = _olive_oil()
    peanut = _food(
        id=7,
        name_vi="Bơ đậu phộng",
        roles=frozenset({"fat"}),
        calories=588,
        protein_g=25,
        carbs_g=20,
        fat_g=50,
        serving_grams=100,
    )
    templates = build_day_templates(_lean_plate() + [peanut], _maintain_targets(), count=1, fallback_fat=oil)
    assert templates
    ids = {m.food_id for m in templates[0].meals}
    assert oil.id not in ids
    assert peanut.id in ids


def test_olive_oil_is_not_attached_to_a_complete_dish_meal():
    oil = _olive_oil()
    pho = _dish(id=20, name_vi="Phở bò")
    templates = build_day_templates(_lean_plate() + [pho], _maintain_targets(), count=1, fallback_fat=oil)
    assert templates
    meals = templates[0].meals
    dish_slots = {m.meal_type for m in meals if m.food_id == pho.id}
    assert dish_slots
    oil_lines = [m for m in meals if m.food_id == oil.id]
    assert oil_lines
    assert all(m.meal_type not in dish_slots for m in oil_lines)
    for slot in dish_slots:
        assert [m.food_id for m in meals if m.meal_type == slot] == [pho.id]