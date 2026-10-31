"""Deterministic meal assembler: pool → slot recipe → portion scale → day templates."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError
from app.models.entities import Food
from app.schemas.plans import PlanDayIn, PlanMealIn
from app.services.food_picker_roles import food_has_fruit_tag, is_starchy_vegetable
from app.services.workout_generation.nutrition_targets import (
    NutritionBlock,
    NutritionTargets,
    WeeklyCalorieSchedule,
    build_weekly_calorie_schedule,
    deload_week_avg_target,
    split_role_category,
    targets_for_calories,
)

logger = logging.getLogger(__name__)

MealSlot = Literal["breakfast", "lunch", "dinner", "snack"]

USER_POOL_MAX = 30
USER_POOL_HELP = "Chọn ít nhất 2 món đạm, 2 món tinh bột và 2 món rau (tối đa 30 món)."

_SLOT_NOTES = {
    "breakfast": "Bữa sáng — một món chế biến, hoặc tinh bột kèm thịt và rau.",
    "lunch": "Bữa trưa — một món chế biến, hoặc tinh bột kèm thịt và rau.",
    "dinner": "Bữa tối — một món chế biến, hoặc tinh bột kèm thịt và rau.",
    "snack": "Bữa phụ — hoa quả, không thay bữa chính.",
}

_WHY = {
    "protein": "Đạm chính cho bữa này.",
    "carb": "Tinh bột no lâu, hỗ trợ tập.",
    "produce": "Rau/củ/quả lấy chất xơ.",
    "fat": "Béo lành để đủ calo và no.",
    "dairy": "Đạm dễ ăn, tiện bữa phụ.",
    "fruit": "Hoa quả cho bữa phụ.",
    "snack": "Bữa phụ hoa quả.",
    "complete": "Một suất chế biến cho cả bữa.",
}

_MAIN_SLOTS: tuple[MealSlot, ...] = ("breakfast", "lunch", "dinner")
_ROLE_CAP = 2


@dataclass
class FoodView:
    id: int
    name_vi: str
    food_kind: str
    prep_state: str | None
    is_complete_meal: bool
    roles: frozenset[str]
    slots: frozenset[str]
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    serving_size: str | None
    is_common: bool
    ai_priority: int
    default_for_ai: bool
    raw: bool
    region_slug: str | None = None
    tags: frozenset[str] = field(default_factory=frozenset)
    image_url: str | None = None
    serving_grams: float | None = None
    slug: str | None = None


@dataclass
class PickedItem:
    food: FoodView
    meal_type: MealSlot
    servings: float
    role: str
    notes_vi: str


@dataclass
class DayTemplate:
    meals: list[PlanMealIn]
    meal_notes: dict[str, str]
    totals: dict[str, float]


@dataclass
class MealPlanResult:
    templates: list[DayTemplate] = field(default_factory=list)
    warning_vi: str | None = None
    used_ai_pool: bool = False
    schedule: WeeklyCalorieSchedule | None = None
    rest_day_template: DayTemplate | None = None
    templates_by_kind: dict[str, DayTemplate] = field(default_factory=dict)
    nutrition_blocks: list[dict[str, Any]] = field(default_factory=list)
    foods_by_id: dict[int, FoodView] = field(default_factory=dict)


_WEEK_TITLE_RE = re.compile(r"Tuần\s+(\d+)", re.IGNORECASE)


def _as_list(val: Any) -> list[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str):
        text = val.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return [p.strip() for p in text.split(",") if p.strip()]
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    return []


def infer_roles(food: Food | FoodView, *, protein_g: float | None = None, carbs_g: float | None = None) -> set[str]:
    if isinstance(food, FoodView):
        return set(food.roles)
    kind = str(getattr(food, "food_kind", None) or "ingredient").lower()
    complete = bool(getattr(food, "is_complete_meal", False)) or kind == "dish"
    if complete:
        return {"complete"}
    roles = {r.lower() for r in _as_list(getattr(food, "macro_roles", None))}
    tags = {t.lower() for t in _as_list(getattr(food, "tags", None))}
    roles.update(t for t in tags if t in {"protein", "carb", "produce", "fat", "dairy", "beverage"})
    if "rau" in tags:
        roles.add("produce")
    if food_has_fruit_tag(tags):
        roles.add("fruit")
        roles.add("produce")
        roles.discard("carb")
        return roles
    p = protein_g if protein_g is not None else float(getattr(food, "protein_g", 0) or 0)
    c = carbs_g if carbs_g is not None else float(getattr(food, "carbs_g", 0) or 0)
    if p >= 15:
        roles.add("protein")
    if c >= 15 and "produce" not in roles:
        roles.add("carb")
    if is_starchy_vegetable(
        slug=getattr(food, "slug", None),
        name_vi=getattr(food, "name_vi", None),
        name_en=getattr(food, "name_en", None),
    ):
        roles.discard("produce")
        roles.discard("fruit")
        roles.add("carb")
    return roles


def _food_image_url(food: object) -> str | None:
    text = str(getattr(food, "image_url", None) or "").strip()
    return text or None


def _to_view(food: Food) -> FoodView:
    prep = (getattr(food, "prep_state", None) or "") or None
    prep_l = (prep or "").lower() or None
    kind = str(getattr(food, "food_kind", None) or "ingredient")
    is_complete = bool(getattr(food, "is_complete_meal", False)) or kind == "dish"
    roles = infer_roles(food)
    if is_complete:
        roles.add("complete")
    slots = {s.lower() for s in _as_list(getattr(food, "meal_slots", None))}
    if not slots:
        slots = {"breakfast", "lunch", "dinner", "snack"}
    return FoodView(
        id=int(food.id),
        name_vi=str(food.name_vi),
        food_kind=kind,
        prep_state=prep_l,
        is_complete_meal=is_complete,
        roles=frozenset(roles),
        slots=frozenset(slots),
        calories=float(food.calories or 0),
        protein_g=float(food.protein_g or 0),
        carbs_g=float(food.carbs_g or 0),
        fat_g=float(food.fat_g or 0),
        serving_size=getattr(food, "serving_size", None),
        is_common=bool(getattr(food, "is_common", False)),
        ai_priority=int(getattr(food, "ai_priority", 0) or 0),
        default_for_ai=bool(getattr(food, "default_for_ai", False)),
        raw=(prep_l == "raw"),
        region_slug=(str(getattr(food, "region_slug", None) or "").strip() or None),
        tags=frozenset(t.lower() for t in _as_list(getattr(food, "tags", None))),
        image_url=_food_image_url(food),
        serving_grams=float(food.serving_grams) if getattr(food, "serving_grams", None) else None,
        slug=(str(getattr(food, "slug", None) or "").strip() or None),
    )


def pool_is_ready(foods: Iterable[FoodView]) -> bool:
    items = list(foods)
    protein = [f for f in items if "protein" in f.roles]
    carb = [f for f in items if "carb" in f.roles]
    produce = [f for f in items if "produce" in f.roles]
    return len(protein) >= 2 and len(carb) >= 2 and len(produce) >= 2


def _active_catalog(query):
    return query.filter(Food.owner_user_id.is_(None), Food.status == "active")


def _normalized_food_ids(food_ids: list[int]) -> list[int]:
    ids: list[int] = []
    seen: set[int] = set()
    for raw in food_ids:
        try:
            fid = int(raw)
        except (TypeError, ValueError):
            continue
        if fid <= 0 or fid in seen:
            continue
        seen.add(fid)
        ids.append(fid)
    return ids


def _load_foods_by_ids(db: Session, food_ids: list[int]) -> list[FoodView]:
    ids = _normalized_food_ids(food_ids)
    if not ids:
        return []
    rows = _active_catalog(db.query(Food)).filter(Food.id.in_(ids)).all()
    order = {fid: i for i, fid in enumerate(ids)}
    views = [_to_view(f) for f in rows]
    return sorted(views, key=lambda f: order.get(f.id, 9999))


def _is_ai_safe(food: FoodView) -> bool:
    return (
        food.food_kind == "ingredient"
        and "beverage" not in food.roles
        and not food.is_complete_meal
    )


_TRADITIONAL_TAG_NEEDLES = frozenset(
    {
        "complete-meal",
        "complete_meal",
        "viet-nam",
        "vietnam",
        "vietnamese",
        "mon-viet",
        "mon_viet",
        "traditional",
        "gia-dinh",
        "family-dish",
    }
)


def _is_lean_ingredient(food: FoodView) -> bool:
    """TAPTOT AI pool: fresh ingredients only — no regional/family dishes."""
    if not _is_ai_safe(food):
        return False
    if str(food.region_slug or "").strip():
        return False
    tags = {t.lower().replace("_", "-") for t in (food.tags or ())}
    tags.update(t.lower() for t in (food.tags or ()))
    if tags & _TRADITIONAL_TAG_NEEDLES:
        return False
    blob = " ".join(tags)
    if any(n in blob for n in ("viet nam", "mon viet", "complete meal")):
        return False
    return True


def _ai_safe_pool(db: Session) -> list[FoodView]:
    query = _active_catalog(db.query(Food)).filter(Food.ai_eligible.is_(True))
    rows = query.all()
    views = [_to_view(f) for f in rows if _food_image_url(f)]
    safe = [f for f in views if _is_lean_ingredient(f)]
    defaults = [f for f in safe if f.default_for_ai]
    pool = defaults if len(defaults) >= 12 and pool_is_ready(defaults) else safe
    pool.sort(key=lambda f: (-f.ai_priority, -int(f.default_for_ai), -int(f.is_common), f.id))
    return pool[:80]


def load_meal_pool(db: Session, payload: dict[str, Any]) -> tuple[list[FoodView], bool]:
    """Return (pool, used_ai_pool). Raises if user opted to pick but pool is unusable."""
    flag = payload.get("ai_suggest_foods")
    raw_ids = list(payload.get("food_ids") or [])
    if flag is False and not raw_ids:
        raise BadRequestError("Chọn món hay ăn.")
    if flag is False:
        if len(_normalized_food_ids(raw_ids)) > USER_POOL_MAX:
            raise BadRequestError(USER_POOL_HELP)
        pool = _load_foods_by_ids(db, raw_ids)
        if not pool:
            raise BadRequestError("Không tìm thấy món đã chọn trong kho thức ăn.")
        if not pool_is_ready(pool):
            raise BadRequestError(USER_POOL_HELP)
        return pool, False

    pool = _ai_safe_pool(db)
    if not pool_is_ready(pool):
        return [], True
    return pool, True


def _active_complete_meals(db: Session) -> list[FoodView]:
    rows = (
        _active_catalog(db.query(Food))
        .filter(or_(Food.is_complete_meal.is_(True), Food.food_kind == "dish"))
        .all()
    )
    dishes: list[FoodView] = []
    for row in rows:
        view = _to_view(row)
        if _is_complete_food(view):
            dishes.append(view)
    return dishes


def _merge_complete_meals(pool: list[FoodView], dishes: list[FoodView]) -> list[FoodView]:
    seen = {food.id for food in pool}
    merged = list(pool)
    for dish in dishes:
        if dish.id in seen:
            continue
        merged.append(dish)
        seen.add(dish.id)
    return merged


def _pool_with_dishes(db: Session, pool: list[FoodView]) -> list[FoodView]:
    """Active prepared dishes stay available as the one-serving option for every main meal."""
    try:
        return _merge_complete_meals(pool, _active_complete_meals(db))
    except SQLAlchemyError:
        logger.exception("complete meal query failed")
        return pool


def _load_olive_oil(db: Session) -> FoodView | None:
    try:
        row = _active_catalog(db.query(Food)).filter(Food.slug == _OLIVE_OIL_SLUG).first()
    except SQLAlchemyError:
        logger.exception("olive oil lookup failed")
        return None
    if row is None:
        return None
    view = _to_view(row)
    return view if _is_olive_oil(view) else None


def _in_slot(food: FoodView, slot: MealSlot) -> bool:
    return slot in food.slots or (slot == "snack" and "dairy" in food.roles)


def _is_complete_food(food: FoodView) -> bool:
    return food.is_complete_meal or food.food_kind == "dish" or "complete" in food.roles


def _filter(
    pool: list[FoodView],
    *,
    role: str | None,
    slot: MealSlot,
    complete: bool | None = None,
    require_slot: bool = True,
) -> list[FoodView]:
    out = []
    for food in pool:
        if require_slot and not _in_slot(food, slot):
            continue
        if slot in _MAIN_SLOTS and food.slots <= {"snack"} and not _is_complete_food(food):
            continue
        is_complete = _is_complete_food(food)
        if complete is True and not is_complete:
            continue
        if complete is False and is_complete:
            continue
        if role and role not in food.roles and not (role == "complete" and is_complete):
            continue
        if role == "protein" and "beverage" in food.roles:
            continue
        if slot != "snack" and "fruit" in food.roles:
            continue
        out.append(food)
    return out


def _pick_preferred(
    cands: list[FoodView],
    preferred_ids: list[int] | None,
    used: set[int],
) -> FoodView | None:
    if not preferred_ids or not cands:
        return None
    by_id = {f.id: f for f in cands}
    for pid in preferred_ids:
        food = by_id.get(int(pid))
        if food and food.id not in used:
            return food
    return None


def _pick(cands: list[FoodView], used: set[int], offset: int) -> FoodView | None:
    if not cands:
        return None
    ranked = sorted(
        cands,
        key=lambda f: (-f.ai_priority, -int(f.default_for_ai), -int(f.is_common), f.id),
    )
    n = len(ranked)
    rotated = ranked[offset % n :] + ranked[: offset % n]
    for food in rotated:
        if food.id not in used:
            return food
    return rotated[0]


def _round_servings(value: float, *, lo: float, hi: float) -> float:
    clamped = max(lo, min(hi, value))
    stepped = round(clamped * 4) / 4
    if stepped < lo:
        stepped = lo
    if stepped > hi:
        stepped = hi
    return stepped


def _prefer_complete_slot(
    slot: MealSlot,
    *,
    template_index: int,
    rotation_index: int,
    has_complete: bool,
) -> bool:
    """One main meal per day is a prepared dish, rotating so the others stay a full plate."""
    if not has_complete or slot not in _MAIN_SLOTS:
        return False
    tick = int(template_index) + max(0, int(rotation_index))
    return _MAIN_SLOTS[tick % len(_MAIN_SLOTS)] == slot


def _item(food: FoodView, slot: MealSlot, role: str, servings: float = 1.0) -> PickedItem:
    why = _WHY.get(role) or _WHY.get("snack") or "Phù hợp bữa này."
    return PickedItem(food=food, meal_type=slot, servings=servings, role=role, notes_vi=why)


def _macro_share(targets: NutritionTargets | None, macro: str) -> float | None:
    if targets is None:
        return None
    value = float(getattr(targets, macro, 0) or 0)
    if value <= 0:
        return None
    return value / 3.0


def _role_count(items: list[PickedItem], role: str) -> int:
    return sum(1 for item in items if item.role == role)


def _append_second_role(
    pool: list[FoodView],
    slot: MealSlot,
    role: str,
    first: FoodView,
    items: list[PickedItem],
    used: set[int],
    offset: int,
    preferred_ids: list[int] | None,
    targets: NutritionTargets | None,
    *,
    require_slot: bool,
    reserve: int = 0,
) -> None:
    """A second item of this group only when one serving-cap misses the meal share. Never a third."""
    if _role_count(items, role) >= _ROLE_CAP:
        return
    macro = "protein_g" if role == "protein" else "carbs_g"
    share = _macro_share(targets, macro)
    if share is None:
        return
    _lo, hi = _serving_bounds(_item(first, slot, role))
    if float(getattr(first, macro) or 0) * hi >= share:
        return
    cands = [
        food
        for food in _filter(pool, role=role, slot=slot, complete=False, require_slot=require_slot)
        if food.id != first.id and food.id not in used
    ]
    if len(cands) <= reserve:
        return
    second = _pick_preferred(cands, preferred_ids, used) or _pick(cands, used, offset)
    if second is None or second.id == first.id:
        return
    used.add(second.id)
    items.append(_item(second, slot, role))


def _pick_complete_dish(
    pool: list[FoodView],
    slot: MealSlot,
    *,
    used: set[int],
    offset: int,
    preferred_ids: list[int] | None,
    require_slot: bool,
) -> PickedItem | None:
    complete_cands = _filter(pool, role=None, slot=slot, complete=True, require_slot=require_slot)
    complete = _pick_preferred(complete_cands, preferred_ids, used) or _pick(complete_cands, used, offset)
    if complete is None:
        return None
    used.add(complete.id)
    return _item(complete, slot, "complete")


def _plate_has_trio(items: list[PickedItem]) -> bool:
    roles = {item.role for item in items}
    return {"protein", "carb", "produce"} <= roles


def _assemble_slot(
    pool: list[FoodView],
    slot: MealSlot,
    *,
    template_index: int,
    used: set[int],
    prefer_complete: bool,
    preferred_ids: list[int] | None = None,
    rotation_index: int = 0,
    targets: NutritionTargets | None = None,
    reserve: int = 0,
) -> list[PickedItem]:
    offset = (template_index + max(0, int(rotation_index))) * 3 + {
        "breakfast": 0,
        "lunch": 1,
        "dinner": 2,
        "snack": 3,
    }[slot]
    main = slot in _MAIN_SLOTS
    require_slot = not main
    items: list[PickedItem] = []
    if main and prefer_complete:
        dish = _pick_complete_dish(
            pool, slot, used=used, offset=offset, preferred_ids=preferred_ids, require_slot=False
        )
        if dish:
            return [dish]

    if slot == "snack":
        snack_pool = [f for f in pool if "fruit" in f.roles]
        picked = _pick_preferred(snack_pool, preferred_ids, used) or _pick(
            snack_pool, used, offset
        )
        if picked:
            used.add(picked.id)
            items.append(_item(picked, "snack", "fruit"))
        return items

    for role, role_offset in (("protein", 0), ("carb", 1), ("produce", 2)):
        cands = _filter(pool, role=role, slot=slot, complete=False, require_slot=require_slot)
        first = _pick_preferred(cands, preferred_ids, used) or _pick(cands, used, offset + role_offset)
        if first is None:
            continue
        used.add(first.id)
        items.append(_item(first, slot, role))
        _append_second_role(
            pool,
            slot,
            role,
            first,
            items,
            used,
            offset + 3 + role_offset,
            preferred_ids,
            targets,
            require_slot=require_slot,
            reserve=reserve,
        )

    if main and not _plate_has_trio(items):
        dish = _pick_complete_dish(
            pool, slot, used=used, offset=offset, preferred_ids=preferred_ids, require_slot=False
        )
        if dish:
            return [dish]

    if not items:
        fallback_cands = _filter(pool, role=None, slot=slot, require_slot=require_slot)
        fallback = _pick_preferred(fallback_cands, preferred_ids, used) or _pick(
            fallback_cands, used, offset
        )
        if fallback:
            used.add(fallback.id)
            role = "complete" if _is_complete_food(fallback) else "protein" if "protein" in fallback.roles else "carb"
            items.append(_item(fallback, slot, role))
    return items


def _totals(items: list[PickedItem]) -> dict[str, float]:
    kcal = sum(i.food.calories * i.servings for i in items)
    protein = sum(i.food.protein_g * i.servings for i in items)
    carbs = sum(i.food.carbs_g * i.servings for i in items)
    fat = sum(i.food.fat_g * i.servings for i in items)
    return {"calories": kcal, "protein_g": protein, "carbs_g": carbs, "fat_g": fat}


_MEAL_CALORIE_TOLERANCE = 0.10
_MACRO_TOLERANCE = 0.12
_MAX_FIT_ROUNDS = 6
_CALORIE_FIT_WARNING_VI = (
    "Tổng calo món còn lệch ~{pct}% so với mục tiêu — có thể bổ sung snack hoặc điều chỉnh khẩu phần."
)
_MACRO_FIT_WARNING_VI = (
    "Macro món còn lệch mục tiêu (đạm/béo/tinh bột) — có thể điều chỉnh khẩu phần tay."
)


def _serving_bounds(item: PickedItem) -> tuple[float, float]:
    if item.food.is_complete_meal or item.role == "complete":
        return 1.0, 1.0
    per = _grams_per_serving(item.food)
    if _is_olive_oil(item.food):
        return 5.0 / per, _OLIVE_OIL_HI_G / per
    if _is_protein_portion(item):
        return _PROTEIN_LO_G / per, _PROTEIN_HI_G / per
    if _is_produce_portion(item):
        return _PRODUCE_MEAL_LO_G / per, _PRODUCE_MEAL_HI_G / per
    if item.role == "carb" or "carb" in item.food.roles:
        return 0.5, 12.0
    if item.role in {"snack", "dairy", "fruit"} or "dairy" in item.food.roles or "fruit" in item.food.roles:
        return 0.5, 2.5
    if item.role == "fat" or "fat" in item.food.roles:
        return 0.25, 3.0
    return 0.5, 2.5


_PROTEIN_LO_G = 80.0
_PROTEIN_HI_G = 200.0
_PRODUCE_MEAL_LO_G = 100.0
_PRODUCE_MEAL_HI_G = 200.0
_OLIVE_OIL_HI_G = 28.0
_OLIVE_OIL_SLUG = "dau-oliu"


def _grams_per_serving(food: FoodView) -> float:
    grams = getattr(food, "serving_grams", None)
    if grams is not None and float(grams) > 0:
        return float(grams)
    return 100.0


def _is_olive_oil(food: FoodView) -> bool:
    slug = (getattr(food, "slug", None) or "").lower()
    if slug == _OLIVE_OIL_SLUG:
        return True
    name = (food.name_vi or "").lower()
    return "oliu" in name or "olive" in name


def _is_produce_portion(item: PickedItem) -> bool:
    if item.meal_type == "snack" or item.role in {"snack", "fruit", "carb", "protein", "fat", "complete"}:
        return False
    return item.role == "produce" or "produce" in item.food.roles


def _is_protein_portion(item: PickedItem) -> bool:
    if _is_fixed_serving(item):
        return False
    if item.role in {"carb", "produce", "snack", "fruit", "fat", "complete"}:
        return False
    return item.role == "protein" or "protein" in item.food.roles


def _is_starch_item(item: PickedItem) -> bool:
    if _is_fixed_serving(item) or _is_produce_portion(item) or _is_protein_portion(item):
        return False
    if item.role in {"fat", "snack", "fruit"}:
        return False
    return item.role == "carb" or "carb" in item.food.roles


def _is_carb_flexible(item: PickedItem) -> bool:
    """Calorie and carb lever: starch, plus fruit snacks. Vegetables stay in their gram band."""
    if item.role == "protein" or item.food.is_complete_meal or _is_produce_portion(item):
        return False
    if item.role in {"carb", "snack", "fruit"} or "carb" in item.food.roles:
        return True
    return item.role == "fruit" or "fruit" in item.food.roles


def _is_fat_flexible(item: PickedItem) -> bool:
    if item.food.is_complete_meal:
        return False
    if item.role == "fat" or "fat" in item.food.roles:
        return True
    cal = max(item.food.calories, 1.0)
    if item.food.fat_g >= 10.0 and item.food.fat_g * 9 / cal >= 0.35:
        return item.role in {"protein", "dairy", "snack"}
    return item.food.fat_g >= 8.0 and item.role in {"dairy", "snack"}


def _rank_fat_foods(pool: list[FoodView]) -> list[FoodView]:
    """Fat-dense foods suitable for injection when the day total is under fat target."""
    out: list[FoodView] = []
    for food in pool:
        if food.is_complete_meal or food.fat_g <= 0:
            continue
        if "fat" in food.roles:
            out.append(food)
            continue
        cal = max(food.calories, 1.0)
        if food.fat_g >= 6.0 and food.fat_g * 9 / cal >= 0.30:
            out.append(food)
    out.sort(
        key=lambda f: (
            -f.fat_g / max(f.protein_g + 1.0, 1.0),
            -f.fat_g / max(f.calories, 1.0),
            -f.ai_priority,
            -int(f.default_for_ai),
            f.id,
        )
    )
    return out


def _max_fat_achievable(items: list[PickedItem], fat_idx: list[int]) -> float:
    total = _totals(items)["fat_g"]
    for i in fat_idx:
        item = items[i]
        lo, hi = _serving_bounds(item)
        total += max(0.0, item.food.fat_g * (hi - item.servings))
    return total


def _inject_fat_from_pool(
    items: list[PickedItem],
    pool: list[FoodView],
    targets: NutritionTargets,
    *,
    tolerance: float = _MACRO_TOLERANCE,
) -> list[PickedItem]:
    """Add one fat-source food from pool when scaling existing items cannot reach fat floor."""
    if not pool:
        return items
    totals = _totals(items)
    gap = targets.fat_g - totals["fat_g"]
    if gap <= 0:
        return items
    if any(item.role == "fat" or "fat" in item.food.roles for item in items):
        return items

    complete_slots = {
        item.meal_type
        for item in items
        if item.role == "complete" or item.food.is_complete_meal
    }
    slot_order: tuple[MealSlot, ...] = ("breakfast", "dinner", "lunch", "snack")
    slots_present = {i.meal_type for i in items if i.meal_type not in complete_slots}
    if not slots_present:
        return items
    slot: MealSlot = next(s for s in slot_order if s in slots_present)

    for food in _rank_fat_foods(pool):
        if not _in_slot(food, slot):
            alt = next((s for s in slot_order if s in food.slots), None)
            if alt is None:
                continue
            slot = alt
        probe = _item(food, slot, "fat", 1.0)
        lo, hi = _serving_bounds(probe)
        servings = gap / max(food.fat_g, 0.5)
        servings = min(servings, targets.fat_g * 1.08 / max(food.fat_g, 0.5))
        servings = _round_servings(servings, lo=lo, hi=hi)
        gained = servings * food.fat_g
        if _is_olive_oil(food):
            if gained < 5:
                continue
        elif gained < gap * 0.35:
            continue
        return items + [_item(food, slot, "fat", servings)]
    return items


def _within_macro_targets(
    totals: dict[str, float],
    targets: NutritionTargets,
    *,
    tolerance: float = _MACRO_TOLERANCE,
) -> bool:
    prot_ok = totals["protein_g"] >= targets.protein_g * (1 - tolerance)
    fat_ok = totals["fat_g"] >= targets.fat_g * (1 - tolerance)
    carb_den = max(targets.carbs_g, 1.0)
    carb_ok = abs(totals["carbs_g"] - targets.carbs_g) / carb_den <= tolerance
    return prot_ok and fat_ok and carb_ok


def _within_calorie_tolerance(total: float, target: int, *, tolerance: float) -> bool:
    if target <= 0:
        return True
    return abs(total - target) / target <= tolerance


def _clone_item(item: PickedItem, servings: float) -> PickedItem:
    return PickedItem(
        food=item.food,
        meal_type=item.meal_type,
        servings=servings,
        role=item.role,
        notes_vi=item.notes_vi,
    )


def _is_fixed_serving(item: PickedItem) -> bool:
    return item.food.is_complete_meal or item.role == "complete" or item.food.food_kind == "dish"


def _uniform_scale(items: list[PickedItem], targets: NutritionTargets) -> list[PickedItem]:
    totals = _totals(items)
    kcal = totals["calories"] or 1.0
    factor = targets.target_calories / kcal
    scaled: list[PickedItem] = []
    for item in items:
        if _is_fixed_serving(item):
            scaled.append(_clone_item(item, 1.0))
            continue
        lo, hi = _serving_bounds(item)
        servings = _round_servings(item.servings * factor, lo=lo, hi=hi)
        scaled.append(_clone_item(item, servings))
    return scaled


def _bump_protein(items: list[PickedItem], targets: NutritionTargets) -> list[PickedItem]:
    totals = _totals(items)
    if totals["protein_g"] >= targets.protein_g * 0.98:
        return items
    deficit = max(0.0, targets.protein_g - totals["protein_g"])
    protein_idx = [
        i
        for i, item in enumerate(items)
        if not _is_fixed_serving(item)
        and ("protein" in item.food.roles or item.role == "protein")
    ]
    if not protein_idx:
        return items
    weight = sum(max(items[i].food.protein_g, 1.0) for i in protein_idx) or 1.0
    protein_set = set(protein_idx)
    bumped: list[PickedItem] = []
    for i, item in enumerate(items):
        if i not in protein_set:
            bumped.append(item)
            continue
        share = max(item.food.protein_g, 1.0) / weight
        extra = deficit * share / max(item.food.protein_g, 1.0)
        lo, hi = _serving_bounds(item)
        if item.role == "protein":
            hi = max(hi, 3.0)
        servings = _round_servings(item.servings + extra, lo=lo, hi=hi)
        bumped.append(_clone_item(item, servings))
    return bumped


def _trim_carb_over(items: list[PickedItem], targets: NutritionTargets) -> list[PickedItem]:
    totals = _totals(items)
    if totals["calories"] <= targets.target_calories * (1 + _MEAL_CALORIE_TOLERANCE):
        return items
    over = totals["calories"] - targets.target_calories
    carb_idx = [i for i, item in enumerate(items) if _is_carb_flexible(item)]
    if not carb_idx:
        return items
    carb_kcal = sum(items[i].food.calories * items[i].servings for i in carb_idx) or 1.0
    carb_set = set(carb_idx)
    trimmed: list[PickedItem] = []
    for i, item in enumerate(items):
        if i not in carb_set:
            trimmed.append(item)
            continue
        share = (item.food.calories * item.servings) / carb_kcal
        lo, hi = _serving_bounds(item)
        new_kcal = max(item.food.calories * lo, item.food.calories * item.servings - over * share)
        servings = _round_servings(new_kcal / max(item.food.calories, 1.0), lo=lo, hi=hi)
        trimmed.append(_clone_item(item, servings))
    return trimmed


def _boost_carb_under(items: list[PickedItem], need_kcal: float) -> list[PickedItem]:
    if need_kcal <= 0:
        return items
    carb_idx = [i for i, item in enumerate(items) if _is_carb_flexible(item)]
    if not carb_idx:
        return items
    carb_kcal = sum(items[i].food.calories * items[i].servings for i in carb_idx) or 1.0
    carb_set = set(carb_idx)
    boosted: list[PickedItem] = []
    for i, item in enumerate(items):
        if i not in carb_set:
            boosted.append(item)
            continue
        share = (item.food.calories * item.servings) / carb_kcal
        lo, hi = _serving_bounds(item)
        add = need_kcal * share / max(item.food.calories, 1.0)
        servings = _round_servings(item.servings + add, lo=lo, hi=hi)
        boosted.append(_clone_item(item, servings))
    return boosted


def _boost_protein_under(
    items: list[PickedItem],
    need_kcal: float,
    *,
    max_servings: float = 5.0,
) -> list[PickedItem]:
    if need_kcal <= 0:
        return items
    protein_idx = [
        i
        for i, item in enumerate(items)
        if not item.food.is_complete_meal
        and (item.role == "protein" or "protein" in item.food.roles)
    ]
    if not protein_idx:
        return items
    protein_kcal = sum(items[i].food.calories * items[i].servings for i in protein_idx) or 1.0
    protein_set = set(protein_idx)
    boosted: list[PickedItem] = []
    for i, item in enumerate(items):
        if i not in protein_set:
            boosted.append(item)
            continue
        share = (item.food.calories * item.servings) / protein_kcal
        lo, hi = _serving_bounds(item)
        add = need_kcal * share / max(item.food.calories, 1.0)
        servings = _round_servings(item.servings + add, lo=lo, hi=min(hi, max_servings))
        boosted.append(_clone_item(item, servings))
    return boosted


def _boost_macro_on_indices(
    items: list[PickedItem],
    indices: list[int],
    need_g: float,
    *,
    macro: Literal["protein_g", "fat_g", "carbs_g"],
    max_servings: float = 5.0,
) -> list[PickedItem]:
    if need_g <= 0 or not indices:
        return items
    macro_set = set(indices)
    weight = sum(max(getattr(items[i].food, macro), 0.5) for i in indices) or 1.0
    out: list[PickedItem] = []
    for i, item in enumerate(items):
        if i not in macro_set:
            out.append(item)
            continue
        share = max(getattr(item.food, macro), 0.5) / weight
        lo, hi = _serving_bounds(item)
        add = need_g * share / max(getattr(item.food, macro), 0.5)
        servings = _round_servings(item.servings + add, lo=lo, hi=hi)
        out.append(_clone_item(item, servings))
    return out


def _trim_macro_on_indices(
    items: list[PickedItem],
    indices: list[int],
    excess_g: float,
    *,
    macro: Literal["protein_g", "fat_g", "carbs_g"],
) -> list[PickedItem]:
    if excess_g <= 0 or not indices:
        return items
    macro_set = set(indices)
    total = sum(getattr(items[i].food, macro) * items[i].servings for i in indices) or 1.0
    out: list[PickedItem] = []
    for i, item in enumerate(items):
        if i not in macro_set:
            out.append(item)
            continue
        share = (getattr(item.food, macro) * item.servings) / total
        lo, hi = _serving_bounds(item)
        cut = excess_g * share
        new_g = max(getattr(item.food, macro) * lo, getattr(item.food, macro) * item.servings - cut)
        servings = _round_servings(new_g / max(getattr(item.food, macro), 0.5), lo=lo, hi=hi)
        out.append(_clone_item(item, servings))
    return out


def _extended_uniform_scale(items: list[PickedItem], targets: NutritionTargets) -> list[PickedItem]:
    """Last-resort scale with wider caps when a sparse meal set hit normal limits."""
    totals = _totals(items)
    kcal = totals["calories"] or 1.0
    factor = targets.target_calories / kcal
    scaled: list[PickedItem] = []
    for item in items:
        if _is_fixed_serving(item):
            scaled.append(_clone_item(item, 1.0))
            continue
        lo, hi = _serving_bounds(item)
        if _is_starch_item(item):
            hi = max(hi, 12.0)
        servings = _round_servings(item.servings * factor, lo=lo, hi=hi)
        scaled.append(_clone_item(item, servings))
    return scaled


def _fat_trim_indices(items: list[PickedItem]) -> list[int]:
    """Items we can reduce to lower total fat (dedicated fat sources first, then incidental)."""
    dedicated = [i for i, item in enumerate(items) if _is_fat_flexible(item)]
    if dedicated:
        return dedicated
    return [
        i
        for i, item in enumerate(items)
        if not item.food.is_complete_meal and item.food.fat_g > 0 and item.role != "protein"
    ]


def _trim_protein_over(items: list[PickedItem], targets: NutritionTargets) -> list[PickedItem]:
    """Cap protein when calorie-fit overshoots lean protein portions."""
    totals = _totals(items)
    cap = targets.protein_g * (1 + _MACRO_TOLERANCE)
    if totals["protein_g"] <= cap:
        return items
    protein_idx = [
        i
        for i, item in enumerate(items)
        if not item.food.is_complete_meal
        and ("protein" in item.food.roles or item.role == "protein")
    ]
    if not protein_idx:
        return items
    excess = totals["protein_g"] - targets.protein_g
    return _trim_macro_on_indices(items, protein_idx, excess, macro="protein_g")


def _inject_missing_fat(
    items: list[PickedItem],
    pool: list[FoodView] | None,
    targets: NutritionTargets,
    fallback: FoodView | None,
    *,
    tolerance: float,
) -> list[PickedItem]:
    """Use a fat food already in the pool. Olive oil is only the fallback when that pool cannot cover the gap."""
    if any(item.role == "fat" or "fat" in item.food.roles for item in items):
        return items
    if _totals(items)["fat_g"] >= targets.fat_g * (1 - tolerance):
        return items
    injected = _inject_fat_from_pool(items, pool or [], targets, tolerance=tolerance)
    if len(injected) > len(items):
        return injected
    if fallback is None or any(item.food.id == fallback.id for item in items):
        return items
    return _inject_fat_from_pool(items, [fallback], targets, tolerance=tolerance)


def _clamp_plate_grams(items: list[PickedItem]) -> list[PickedItem]:
    """Meat stays 80–200g per line. Vegetables in one main meal stay 100–200g together."""
    out = list(items)
    for i, item in enumerate(out):
        if not _is_protein_portion(item):
            continue
        per = _grams_per_serving(item.food)
        grams = min(_PROTEIN_HI_G, max(_PROTEIN_LO_G, item.servings * per))
        out[i] = _clone_item(item, grams / per)
    groups: dict[str, list[int]] = {}
    for i, item in enumerate(out):
        if _is_produce_portion(item):
            groups.setdefault(item.meal_type, []).append(i)
    for indices in groups.values():
        total = sum(out[i].servings * _grams_per_serving(out[i].food) for i in indices)
        if total <= 0:
            share = _PRODUCE_MEAL_LO_G / len(indices)
            for i in indices:
                per = _grams_per_serving(out[i].food)
                out[i] = _clone_item(out[i], share / per)
            continue
        if _PRODUCE_MEAL_LO_G <= total <= _PRODUCE_MEAL_HI_G:
            continue
        target = _PRODUCE_MEAL_LO_G if total < _PRODUCE_MEAL_LO_G else _PRODUCE_MEAL_HI_G
        factor = target / total
        for i in indices:
            per = _grams_per_serving(out[i].food)
            out[i] = _clone_item(out[i], out[i].servings * factor)
    return out


def _trim_indexed_calories(
    items: list[PickedItem],
    indices: list[int],
    targets: NutritionTargets,
) -> list[PickedItem]:
    totals = _totals(items)
    if totals["calories"] <= targets.target_calories * (1 + _MEAL_CALORIE_TOLERANCE):
        return items
    over = totals["calories"] - targets.target_calories
    kcal = sum(items[i].food.calories * items[i].servings for i in indices) or 1.0
    chosen = set(indices)
    out: list[PickedItem] = []
    for i, item in enumerate(items):
        if i not in chosen:
            out.append(item)
            continue
        share = (item.food.calories * item.servings) / kcal
        lo, hi = _serving_bounds(item)
        new_kcal = max(item.food.calories * lo, item.food.calories * item.servings - over * share)
        servings = _round_servings(new_kcal / max(item.food.calories, 1.0), lo=lo, hi=hi)
        out.append(_clone_item(item, servings))
    return out


def _boost_indexed_calories(items: list[PickedItem], indices: list[int], need_kcal: float) -> list[PickedItem]:
    if need_kcal <= 0 or not indices:
        return items
    kcal = sum(items[i].food.calories * items[i].servings for i in indices) or 1.0
    chosen = set(indices)
    out: list[PickedItem] = []
    for i, item in enumerate(items):
        if i not in chosen:
            out.append(item)
            continue
        share = (item.food.calories * item.servings) / kcal
        lo, hi = _serving_bounds(item)
        add = need_kcal * share / max(item.food.calories, 1.0)
        servings = _round_servings(item.servings + add, lo=lo, hi=hi)
        out.append(_clone_item(item, servings))
    return out


def _reduce_added_fat(items: list[PickedItem], targets: NutritionTargets) -> list[PickedItem]:
    """Drop the added fat line once starch is already at its floor, so rice stays on the plate."""
    out = list(items)
    for _ in range(len(out)):
        over = _totals(out)["calories"] - targets.target_calories
        if over <= targets.target_calories * _MEAL_CALORIE_TOLERANCE:
            return out
        fat_indexes = [i for i, item in enumerate(out) if item.role == "fat" or _is_olive_oil(item.food)]
        if not fat_indexes:
            return out
        i = fat_indexes[-1]
        item = out[i]
        lo, hi = _serving_bounds(item)
        drop = over / max(item.food.calories, 1.0)
        servings = _round_servings(item.servings - drop, lo=lo, hi=hi)
        if servings >= item.servings - 1e-6:
            return out
        out[i] = _clone_item(item, servings)
    return out


def _balance_starch_and_oil(items: list[PickedItem], targets: NutritionTargets) -> list[PickedItem]:
    scaled = list(items)
    for _ in range(4):
        kcal = _totals(scaled)["calories"]
        target = targets.target_calories
        if _within_calorie_tolerance(kcal, target, tolerance=_MEAL_CALORIE_TOLERANCE):
            return scaled
        starch = [i for i, item in enumerate(scaled) if _is_starch_item(item)]
        if kcal > target * (1 + _MEAL_CALORIE_TOLERANCE):
            before = [scaled[i].servings for i in starch]
            if starch:
                scaled = _trim_indexed_calories(scaled, starch, targets)
            moved = any(scaled[i].servings < before[n] - 1e-6 for n, i in enumerate(starch))
            if moved:
                continue
            scaled = _reduce_added_fat(scaled, targets)
            continue
        if not starch:
            return scaled
        scaled = _boost_indexed_calories(scaled, starch, target - kcal)
    return scaled


def _fit_macros_to_target(
    items: list[PickedItem],
    targets: NutritionTargets,
    *,
    pool: list[FoodView] | None = None,
    fallback_fat: FoodView | None = None,
    tolerance: float = _MACRO_TOLERANCE,
) -> list[PickedItem]:
    """Priority: protein floor → fat floor (hormones) → carbs fill → re-balance kcal via carbs."""
    scaled = list(items)
    protein_idx = [
        i
        for i, item in enumerate(scaled)
        if not _is_fixed_serving(item)
        and ("protein" in item.food.roles or item.role == "protein")
    ]
    fat_idx = [i for i, item in enumerate(scaled) if _is_fat_flexible(item)]
    carb_idx = [i for i, item in enumerate(scaled) if _is_carb_flexible(item)]

    for _ in range(_MAX_FIT_ROUNDS):
        totals = _totals(scaled)
        changed = False

        if totals["protein_g"] > targets.protein_g * (1 + tolerance) and protein_idx:
            excess = totals["protein_g"] - targets.protein_g
            trimmed = _trim_macro_on_indices(scaled, protein_idx, excess, macro="protein_g")
            if _totals(trimmed)["protein_g"] <= targets.protein_g * (1 + tolerance):
                scaled = trimmed
                changed = True
                protein_idx = [
                    i
                    for i, item in enumerate(scaled)
                    if not _is_fixed_serving(item)
                    and ("protein" in item.food.roles or item.role == "protein")
                ]

        totals = _totals(scaled)
        if totals["protein_g"] < targets.protein_g * (1 - tolerance) and protein_idx:
            need = targets.protein_g * (1 - tolerance) - totals["protein_g"]
            scaled = _boost_macro_on_indices(scaled, protein_idx, need, macro="protein_g")
            changed = True

        totals = _totals(scaled)
        if totals["fat_g"] < targets.fat_g * (1 - tolerance):
            if not any(item.role == "fat" or "fat" in item.food.roles for item in scaled):
                injected = _inject_missing_fat(scaled, pool, targets, fallback_fat, tolerance=tolerance)
                if len(injected) > len(scaled):
                    scaled = injected
                    changed = True
            fat_idx = [i for i, item in enumerate(scaled) if _is_fat_flexible(item)]
            if fat_idx:
                need = targets.fat_g * (1 - tolerance) - _totals(scaled)["fat_g"]
                if need > 0:
                    scaled = _boost_macro_on_indices(scaled, fat_idx, need, macro="fat_g")
                    changed = True
            totals = _totals(scaled)
            if (
                totals["fat_g"] < targets.fat_g * (1 - tolerance)
                and _max_fat_achievable(scaled, fat_idx) < targets.fat_g * (1 - tolerance)
            ):
                injected = _inject_missing_fat(scaled, pool, targets, fallback_fat, tolerance=tolerance)
                if len(injected) > len(scaled):
                    scaled = injected
                    changed = True
        elif totals["fat_g"] > targets.fat_g * (1 + tolerance):
            trim_idx = _fat_trim_indices(scaled)
            if trim_idx:
                excess = totals["fat_g"] - targets.fat_g
                scaled = _trim_macro_on_indices(scaled, trim_idx, excess, macro="fat_g")
                changed = True

        totals = _totals(scaled)
        carb_target = targets.carbs_g
        if carb_idx and carb_target > 0:
            if totals["carbs_g"] < carb_target * (1 - tolerance):
                need = carb_target - totals["carbs_g"]
                scaled = _boost_macro_on_indices(scaled, carb_idx, need, macro="carbs_g")
                changed = True
            elif totals["carbs_g"] > carb_target * (1 + tolerance):
                excess = totals["carbs_g"] - carb_target
                scaled = _trim_macro_on_indices(scaled, carb_idx, excess, macro="carbs_g")
                changed = True

        totals = _totals(scaled)
        kcal = totals["calories"]
        target_kcal = targets.target_calories
        if kcal > target_kcal * (1 + _MEAL_CALORIE_TOLERANCE) and carb_idx:
            scaled = _trim_carb_over(scaled, targets)
            changed = True
        elif kcal < target_kcal * (1 - _MEAL_CALORIE_TOLERANCE) and carb_idx:
            scaled = _boost_carb_under(scaled, target_kcal - kcal)
            changed = True

        if _within_macro_targets(_totals(scaled), targets, tolerance=tolerance) and _within_calorie_tolerance(
            _totals(scaled)["calories"], targets.target_calories, tolerance=_MEAL_CALORIE_TOLERANCE
        ):
            break
        if not changed:
            break

    totals = _totals(scaled)
    trim_idx = _fat_trim_indices(scaled)
    carb_idx = [i for i, item in enumerate(scaled) if _is_carb_flexible(item)]
    if totals["fat_g"] > targets.fat_g * (1 + tolerance) and trim_idx:
        excess = totals["fat_g"] - targets.fat_g
        scaled = _trim_macro_on_indices(scaled, trim_idx, excess, macro="fat_g")
    totals = _totals(scaled)
    if carb_idx and totals["carbs_g"] > targets.carbs_g * (1 + tolerance):
        excess = totals["carbs_g"] - targets.carbs_g
        scaled = _trim_macro_on_indices(scaled, carb_idx, excess, macro="carbs_g")

    for _ in range(3):
        totals = _totals(scaled)
        kcal = totals["calories"]
        target_kcal = targets.target_calories
        if _within_calorie_tolerance(kcal, target_kcal, tolerance=_MEAL_CALORIE_TOLERANCE):
            break
        if kcal < target_kcal * (1 - _MEAL_CALORIE_TOLERANCE) and carb_idx:
            scaled = _boost_carb_under(scaled, target_kcal - kcal)
        elif kcal > target_kcal * (1 + _MEAL_CALORIE_TOLERANCE):
            scaled = _trim_carb_over(scaled, targets)

    scaled = _trim_protein_over(scaled, targets)
    totals = _totals(scaled)
    if totals["protein_g"] > targets.protein_g * (1 + tolerance):
        protein_idx = [
            i
            for i, item in enumerate(scaled)
            if not _is_fixed_serving(item)
            and ("protein" in item.food.roles or item.role == "protein")
        ]
        if protein_idx:
            excess = totals["protein_g"] - targets.protein_g
            scaled = _trim_macro_on_indices(scaled, protein_idx, excess, macro="protein_g")

    return scaled


def _payload_weight_kg(payload: dict[str, Any]) -> float | None:
    raw = payload.get("weight_kg")
    if raw in (None, ""):
        return None
    try:
        weight = float(raw)
    except (TypeError, ValueError):
        return None
    return weight if weight > 0 else None


def _extreme_protein_floor_g(weight_kg: float) -> float:
    """Light people cannot clear a ±5% day total if every protein line stays at 80 g."""
    if weight_kg < 50:
        return 30.0
    return _PROTEIN_LO_G


def _repair_calories_with_starch(items: list[PickedItem], targets: NutritionTargets) -> list[PickedItem]:
    out = items
    for _ in range(6):
        totals = _totals(out)
        kcal = totals["calories"]
        target = targets.target_calories
        if _within_calorie_tolerance(kcal, target, tolerance=_MEAL_CALORIE_TOLERANCE):
            return out
        if kcal > target * (1 + _MEAL_CALORIE_TOLERANCE):
            nxt = _trim_carb_over(out, targets)
        else:
            nxt = _boost_carb_under(out, target - kcal)
        if abs(_totals(nxt)["calories"] - kcal) < 1:
            return nxt
        out = nxt
    return out


def _nudge_extreme_protein(
    items: list[PickedItem],
    targets: NutritionTargets,
    weight_kg: float | None,
) -> list[PickedItem]:
    """15 g steps for people under 50 kg or over 90 kg, then starch pulls calories back."""
    if weight_kg is None or not (weight_kg < 50 or weight_kg > 90):
        return items
    lo = _extreme_protein_floor_g(weight_kg)
    hi = _PROTEIN_HI_G
    out = list(items)
    for _ in range(48):
        prot = _totals(out)["protein_g"]
        target_p = float(targets.protein_g or 0)
        if target_p <= 0 or abs(prot - target_p) / target_p <= 0.05:
            break
        direction = 15.0 if prot < target_p else -15.0
        best: tuple[float, int, float] | None = None
        for i, item in enumerate(out):
            if not _is_protein_portion(item):
                continue
            per = _grams_per_serving(item.food)
            grams = item.servings * per
            nxt = grams + direction
            if nxt < lo - 1e-6 or nxt > hi + 1e-6:
                continue
            delta_p = item.food.protein_g * ((nxt - grams) / per)
            new_err = abs(prot + delta_p - target_p)
            if best is None or new_err < best[0]:
                best = (new_err, i, nxt)
        if best is None or best[0] >= abs(prot - target_p) - 0.05:
            break
        _, index, nxt = best
        per = _grams_per_serving(out[index].food)
        out[index] = _clone_item(out[index], nxt / per)
        out = _repair_calories_with_starch(out, targets)
    return _repair_calories_with_starch(out, targets)


def fit_meals_to_target(
    items: list[PickedItem],
    targets: NutritionTargets,
    *,
    pool: list[FoodView] | None = None,
    fallback_fat: FoodView | None = None,
    tolerance: float = _MEAL_CALORIE_TOLERANCE,
    weight_kg: float | None = None,
) -> tuple[list[PickedItem], str | None]:
    """Scale portions so meal totals land within tolerance of target_calories."""
    if not items:
        return items, None

    scaled = _uniform_scale(items, targets)
    scaled = _bump_protein(scaled, targets)

    for _ in range(_MAX_FIT_ROUNDS):
        totals = _totals(scaled)
        total_kcal = totals["calories"]
        target = targets.target_calories
        if _within_calorie_tolerance(total_kcal, target, tolerance=tolerance):
            break
        if total_kcal > target * (1 + tolerance):
            scaled = _trim_carb_over(scaled, targets)
        elif total_kcal < target * (1 - tolerance):
            before = total_kcal
            scaled = _boost_carb_under(scaled, target - total_kcal)
            after = _totals(scaled)["calories"]
            if after <= before + 1:
                prot = _totals(scaled)["protein_g"]
                if prot < targets.protein_g * 0.98:
                    scaled = _boost_protein_under(scaled, target - after)
        else:
            break

    totals = _totals(scaled)
    if not _within_calorie_tolerance(totals["calories"], targets.target_calories, tolerance=tolerance):
        scaled = _extended_uniform_scale(scaled, targets)
        for _ in range(3):
            totals = _totals(scaled)
            total_kcal = totals["calories"]
            target = targets.target_calories
            if _within_calorie_tolerance(total_kcal, target, tolerance=tolerance):
                break
            if total_kcal < target * (1 - tolerance):
                scaled = _boost_carb_under(scaled, target - total_kcal)
                scaled = _boost_protein_under(scaled, target - _totals(scaled)["calories"], max_servings=6.0)
            elif total_kcal > target * (1 + tolerance):
                scaled = _trim_carb_over(scaled, targets)
            else:
                break

    scaled = _trim_protein_over(scaled, targets)
    totals = _totals(scaled)
    if not _within_calorie_tolerance(totals["calories"], targets.target_calories, tolerance=tolerance):
        carb_idx = [i for i, item in enumerate(scaled) if _is_carb_flexible(item)]
        if carb_idx and totals["calories"] < targets.target_calories * (1 - tolerance):
            scaled = _boost_carb_under(scaled, targets.target_calories - totals["calories"])

    scaled = _fit_macros_to_target(scaled, targets, pool=pool, fallback_fat=fallback_fat)

    if not _within_calorie_tolerance(
        _totals(scaled)["calories"], targets.target_calories, tolerance=tolerance
    ):
        scaled = _extended_uniform_scale(scaled, targets)
        for _ in range(3):
            totals = _totals(scaled)
            total_kcal = totals["calories"]
            target = targets.target_calories
            if _within_calorie_tolerance(total_kcal, target, tolerance=tolerance):
                break
            if total_kcal < target * (1 - tolerance):
                scaled = _boost_carb_under(scaled, target - total_kcal)
                prot = _totals(scaled)["protein_g"]
                if prot < targets.protein_g * 0.98:
                    scaled = _boost_protein_under(
                        scaled, target - _totals(scaled)["calories"], max_servings=6.0
                    )
            elif total_kcal > target * (1 + tolerance):
                scaled = _trim_carb_over(scaled, targets)

    scaled = _clamp_plate_grams(scaled)
    scaled = _balance_starch_and_oil(scaled, targets)
    scaled = _clamp_plate_grams(scaled)
    scaled = _nudge_extreme_protein(scaled, targets, weight_kg)

    totals = _totals(scaled)
    warning = None
    if not _within_calorie_tolerance(totals["calories"], targets.target_calories, tolerance=tolerance):
        target = max(targets.target_calories, 1)
        pct = int(round(abs(totals["calories"] - target) / target * 100))
        warning = _CALORIE_FIT_WARNING_VI.format(pct=pct)
        logger.warning(
            "meal calorie fit off target: got %.0f vs %d (%.0f%%)",
            totals["calories"],
            targets.target_calories,
            abs(totals["calories"] - target) / target * 100,
        )
    if not _within_macro_targets(totals, targets):
        if warning:
            warning = f"{warning} {_MACRO_FIT_WARNING_VI}"
        else:
            warning = _MACRO_FIT_WARNING_VI
        logger.warning(
            "meal macro fit off target: P %.0f/%.0f F %.0f/%.0f C %.0f/%.0f",
            totals["protein_g"],
            targets.protein_g,
            totals["fat_g"],
            targets.fat_g,
            totals["carbs_g"],
            targets.carbs_g,
        )
    return scaled, warning


def scale_items(items: list[PickedItem], targets: NutritionTargets) -> list[PickedItem]:
    fitted, _ = fit_meals_to_target(items, targets)
    return fitted


def _infer_meal_role(food: FoodView, meal: PlanMealIn) -> str:
    notes = (meal.notes_vi or "").lower()
    if "đạm" in notes or "protein" in notes:
        return "protein"
    if "tinh bột" in notes or "carb" in notes:
        return "carb"
    if "rau" in notes or "chất xơ" in notes or "produce" in notes:
        return "produce"
    if "béo" in notes or "fat" in notes:
        return "fat"
    if food.is_complete_meal or "complete" in food.roles:
        return "complete"
    if "protein" in food.roles:
        return "protein"
    if "carb" in food.roles:
        return "carb"
    if "produce" in food.roles:
        return "produce"
    if "fat" in food.roles:
        return "fat"
    if "dairy" in food.roles:
        return "dairy"
    return "snack"


def _meals_to_items(
    meals: list[PlanMealIn],
    foods_by_id: dict[int, FoodView],
) -> list[PickedItem]:
    items: list[PickedItem] = []
    for m in meals:
        food = foods_by_id.get(int(m.food_id))
        if food is None:
            continue
        role = _infer_meal_role(food, m)
        items.append(
            PickedItem(
                food=food,
                meal_type=m.meal_type,
                servings=float(m.servings or 1),
                role=role,
                notes_vi=m.notes_vi or _WHY.get(role, "Phù hợp bữa này."),
            )
        )
    return items


def _append_fit_warning(meal_notes: dict[str, str], warning: str) -> dict[str, str]:
    notes = dict(meal_notes)
    key = "breakfast" if "breakfast" in notes else next(iter(notes), "breakfast")
    prev = notes.get(key, _SLOT_NOTES.get(key, ""))
    notes[key] = f"{prev} {warning}".strip()
    return notes


def meal_total_calories(items: list[PickedItem]) -> float:
    return _totals(items)["calories"]


def _to_plan_meals(items: list[PickedItem]) -> list[PlanMealIn]:
    meals: list[PlanMealIn] = []
    for idx, item in enumerate(items):
        meals.append(
            PlanMealIn(
                food_id=item.food.id,
                meal_type=item.meal_type,
                servings=item.servings,
                notes_vi=item.notes_vi,
                sort_order=idx,
            )
        )
    return meals


def _relocate_fruit_picks(
    preferred: dict[str, list[int]] | None,
    pool: list[FoodView],
) -> dict[str, list[int]] | None:
    """Fruit ids the model put on a main meal move to the snack slot."""
    if not preferred:
        return preferred
    fruit_ids = {int(food.id) for food in pool if "fruit" in food.roles}
    if not fruit_ids:
        return preferred
    out = {key: [int(fid) for fid in (ids or [])] for key, ids in preferred.items()}
    moved: list[int] = []
    for slot in ("breakfast", "lunch", "dinner", "rest"):
        kept: list[int] = []
        for fid in out.get(slot) or []:
            if fid in fruit_ids:
                moved.append(fid)
            else:
                kept.append(fid)
        if slot in out or moved:
            out[slot] = kept
    if moved:
        snack = list(out.get("snack") or [])
        for fid in moved:
            if fid not in snack:
                snack.append(fid)
        out["snack"] = snack
    return out


def build_day_templates(
    pool: list[FoodView],
    targets: NutritionTargets,
    *,
    count: int = 2,
    preferred_by_slot: dict[str, list[int]] | None = None,
    rotation_index: int = 0,
    fallback_fat: FoodView | None = None,
    weight_kg: float | None = None,
) -> list[DayTemplate]:
    slots: list[MealSlot] = ["breakfast", "lunch", "dinner"]
    if any("fruit" in (food.roles or frozenset()) for food in pool):
        slots.append("snack")
    templates: list[DayTemplate] = []
    n = max(1, min(3, count))
    pref = _relocate_fruit_picks(preferred_by_slot, pool) or {}
    has_complete = any(_is_complete_food(f) for f in pool)
    for idx in range(n):
        used: set[int] = set()
        picked: list[PickedItem] = []
        for slot_i, slot in enumerate(slots):
            prefer_complete = _prefer_complete_slot(
                slot,
                template_index=idx,
                rotation_index=rotation_index,
                has_complete=has_complete,
            )
            later_plates = 0
            if slot in _MAIN_SLOTS and not prefer_complete:
                for later in slots[slot_i + 1 :]:
                    if later not in _MAIN_SLOTS:
                        continue
                    if _prefer_complete_slot(
                        later,
                        template_index=idx,
                        rotation_index=rotation_index,
                        has_complete=has_complete,
                    ):
                        continue
                    later_plates += 1
            picked.extend(
                _assemble_slot(
                    pool,
                    slot,
                    template_index=idx,
                    used=used,
                    prefer_complete=prefer_complete,
                    preferred_ids=pref.get(slot) or None,
                    rotation_index=rotation_index,
                    targets=targets,
                    reserve=later_plates,
                )
            )
        picked, fit_warn = fit_meals_to_target(
            picked, targets, pool=pool, fallback_fat=fallback_fat, weight_kg=weight_kg
        )
        notes = {slot: _SLOT_NOTES[slot] for slot in slots if slot != "snack"}
        if "snack" in slots:
            notes["snack"] = _SLOT_NOTES["snack"]
        if fit_warn:
            notes = _append_fit_warning(notes, fit_warn)
        templates.append(
            DayTemplate(
                meals=_to_plan_meals(picked),
                meal_notes=notes,
                totals=_totals(picked),
            )
        )
    return templates


def apply_meals_with_schedule(
    days: list[PlanDayIn],
    schedule: WeeklyCalorieSchedule,
    templates_by_kind: dict[str, DayTemplate],
    *,
    foods_by_id: dict[int, FoodView] | None = None,
    weight_kg: float | None = None,
) -> list[PlanDayIn]:
    if not days or not templates_by_kind:
        return days
    out: list[PlanDayIn] = []
    for i, day in enumerate(days):
        slot = schedule.training[i] if i < len(schedule.training) else None
        kind = slot.session_kind if slot else split_role_category(day.split_role)
        tmpl = templates_by_kind.get(kind) or next(iter(templates_by_kind.values()))
        day_targets = slot.targets if slot else None
        meals = [m.model_copy() for m in tmpl.meals]
        meal_notes = dict(tmpl.meal_notes)
        if day_targets and foods_by_id:
            items = _meals_to_items(meals, foods_by_id)
            if items:
                fitted, fit_warn = fit_meals_to_target(
                    items, day_targets, pool=list(foods_by_id.values()), weight_kg=weight_kg
                )
                meals = _to_plan_meals(fitted)
                if fit_warn:
                    meal_notes = _append_fit_warning(meal_notes, fit_warn)
        updates: dict[str, Any] = {
            "meals": meals,
            "meal_notes": meal_notes,
        }
        if day_targets:
            updates.update(
                {
                    "target_calories": day_targets.target_calories,
                    "target_protein_g": day_targets.protein_g,
                    "target_carbs_g": day_targets.carbs_g,
                    "target_fat_g": day_targets.fat_g,
                }
            )
        out.append(day.model_copy(update=updates))
    return out


def parse_week_from_title(title_vi: str | None) -> int:
    if not title_vi:
        return 1
    m = _WEEK_TITLE_RE.search(title_vi)
    return int(m.group(1)) if m else 1


def _preferred_for_rest(preferred: dict[str, list[int]] | None) -> dict[str, list[int]] | None:
    if not preferred:
        return preferred
    rest_ids = list(preferred.get("rest") or [])
    if not rest_ids:
        return preferred
    out = {
        "breakfast": rest_ids,
        "lunch": rest_ids,
        "dinner": rest_ids,
        "rest": rest_ids,
    }
    snack_ids = list(preferred.get("snack") or [])
    if snack_ids:
        out["snack"] = snack_ids
    return out


def _templates_for_schedule(
    pool: list[FoodView],
    schedule: WeeklyCalorieSchedule,
    preferred: dict[str, list[int]] | None = None,
    rotation_index: int = 0,
    fallback_fat: FoodView | None = None,
    weight_kg: float | None = None,
) -> tuple[dict[str, DayTemplate], DayTemplate | None]:
    templates_by_kind: dict[str, DayTemplate] = {}
    seen_kcal: dict[int, str] = {}
    for slot in schedule.training:
        kcal = slot.targets.target_calories
        if kcal in seen_kcal:
            templates_by_kind[slot.session_kind] = templates_by_kind[seen_kcal[kcal]]
            continue
        built = build_day_templates(
            pool,
            slot.targets,
            count=1,
            preferred_by_slot=preferred,
            rotation_index=rotation_index,
            fallback_fat=fallback_fat,
            weight_kg=weight_kg,
        )
        if built:
            templates_by_kind[slot.session_kind] = built[0]
            seen_kcal[kcal] = slot.session_kind
    rest_day_template: DayTemplate | None = None
    rest_built = build_day_templates(
        pool,
        schedule.rest,
        count=1,
        preferred_by_slot=_preferred_for_rest(preferred),
        rotation_index=rotation_index,
        fallback_fat=fallback_fat,
        weight_kg=weight_kg,
    )
    if rest_built:
        rest_day_template = rest_built[0]
        rest_notes = dict(rest_day_template.meal_notes)
        rest_notes["breakfast"] = (
            rest_notes.get("breakfast", _SLOT_NOTES["breakfast"])
            + " Thực đơn mẫu cho ngày nghỉ."
        )
        rest_day_template = DayTemplate(
            meals=rest_day_template.meals,
            meal_notes=rest_notes,
            totals=rest_day_template.totals,
        )
    return templates_by_kind, rest_day_template


def _session_to_dict(day: PlanDayIn) -> dict[str, Any]:
    return {
        "split_role": day.split_role,
        "target_calories": day.target_calories,
        "target_protein_g": day.target_protein_g,
        "target_carbs_g": day.target_carbs_g,
        "target_fat_g": day.target_fat_g,
        "meals": [m.model_dump() for m in day.meals],
        "meal_notes": dict(day.meal_notes or {}),
    }


def _rest_insight_from_template(
    schedule: WeeklyCalorieSchedule,
    rest_tpl: DayTemplate | None,
    foods_map: dict[int, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rest = schedule.rest
    nutrition = {
        "target_calories": rest.target_calories,
        "protein_g": rest.protein_g,
        "carbs_g": rest.carbs_g,
        "fat_g": rest.fat_g,
    }
    meals_out: list[dict[str, Any]] = []
    if rest_tpl:
        for m in rest_tpl.meals:
            food = (foods_map or {}).get(int(m.food_id))
            servings = float(m.servings or 1)
            meals_out.append(
                {
                    "food_id": m.food_id,
                    "name_vi": getattr(food, "name_vi", None) if food else None,
                    "meal_type": m.meal_type,
                    "servings": servings,
                    "calories": int(round((food.calories or 0) * servings)) if food else None,
                    "protein_g": (food.protein_g * servings) if food and food.protein_g else None,
                    "carbs_g": (food.carbs_g * servings) if food and food.carbs_g else None,
                    "fat_g": (food.fat_g * servings) if food and food.fat_g else None,
                    "notes_vi": m.notes_vi,
                    "image_url": getattr(food, "image_url", None) if food else None,
                    "serving_size": getattr(food, "serving_size", None) if food else None,
                    "serving_grams": getattr(food, "serving_grams", None) if food else None,
                }
            )
    return nutrition, meals_out


def generate_meals_with_blocks(
    db: Session,
    payload: dict[str, Any],
    blocks: list[NutritionBlock],
    template_days: list[PlanDayIn],
    *,
    goal: str = "maintain",
    block_size: int = 2,
    include_deload_meals: bool = False,
    preferred_foods_by_block: dict[int, dict[str, list[int]]] | None = None,
) -> MealPlanResult:
    """Build meal templates per nutrition block; week-1 days use block 0."""
    if not blocks or not template_days:
        return generate_meals(db, payload, blocks[0].targets if blocks else None, plan_days=template_days, goal=goal)
    try:
        pool, used_ai = load_meal_pool(db, payload)
    except BadRequestError:
        raise
    except SQLAlchemyError:
        logger.exception("meal pool query failed")
        return MealPlanResult(warning_vi="Chưa tạo được thực đơn từ kho thức ăn.")
    if not pool:
        return MealPlanResult(
            warning_vi="Kho thức ăn chưa đủ món an toàn để ráp thực đơn.",
            used_ai_pool=used_ai,
        )
    pool = _pool_with_dishes(db, pool)
    olive = _load_olive_oil(db)

    from app.models.entities import Food

    all_food_ids: set[int] = set()
    block_insights: list[dict[str, Any]] = []
    first_block_days: list[PlanDayIn] | None = None
    first_schedule: WeeklyCalorieSchedule | None = None
    first_rest: DayTemplate | None = None
    first_templates: dict[str, DayTemplate] = {}

    foods_map = {f.id: f for f in pool}
    if olive is not None:
        foods_map.setdefault(olive.id, olive)
    goal_n = (goal or "maintain").lower()
    gender = (payload.get("gender") or "male").lower()
    if gender not in {"male", "female"}:
        gender = "male"

    for block in blocks:
        pref = None
        if preferred_foods_by_block:
            pref = preferred_foods_by_block.get(int(block.block_index))
        rotation = int(block.block_index)
        templates_by_kind, rest_tpl = _templates_for_schedule(
            pool,
            block.schedule,
            preferred=pref,
            rotation_index=rotation,
            fallback_fat=olive,
            weight_kg=_payload_weight_kg(payload),
        )
        days_copy = [d.model_copy(deep=True) for d in template_days]
        applied = apply_meals_with_schedule(
            days_copy,
            block.schedule,
            templates_by_kind,
            foods_by_id=foods_map,
            weight_kg=_payload_weight_kg(payload),
        )
        for m in rest_tpl.meals if rest_tpl else []:
            all_food_ids.add(int(m.food_id))
        for d in applied:
            for m in d.meals:
                all_food_ids.add(int(m.food_id))

        avg = block.schedule.avg_target
        display = targets_for_calories(
            block.targets,
            goal=goal_n,
            weight_kg=block.projected_weight_kg,
            target_calories=avg,
        )
        insight: dict[str, Any] = {
            "block_index": block.block_index,
            "weeks": list(range(block.week_from, block.week_to + 1)),
            "projected_weight_kg": block.projected_weight_kg,
            "avg_target_calories": avg,
            "tdee": block.targets.tdee,
            "protein_g": display.protein_g,
            "carbs_g": display.carbs_g,
            "fat_g": display.fat_g,
            "sessions": [_session_to_dict(d) for d in applied],
        }

        # Cut: soft maintenance meals on deload weeks within the block.
        if goal_n == "lose_weight" and (include_deload_meals or block_size >= 4):
            deload_avg = deload_week_avg_target(
                goal=goal_n, block_avg=avg, tdee=block.targets.tdee
            )
            if deload_avg > avg:
                split_roles = [d.split_role for d in template_days]
                deload_schedule = build_weekly_calorie_schedule(
                    goal=goal_n,
                    avg_target=deload_avg,
                    split_roles=split_roles,
                    gender=gender,
                    weight_kg=block.projected_weight_kg,
                    bmr=float(block.targets.bmr),
                    base=block.targets,
                )
                d_templates, _ = _templates_for_schedule(
                    pool,
                    deload_schedule,
                    preferred=pref,
                    rotation_index=rotation,
                    fallback_fat=olive,
                )
                d_days = apply_meals_with_schedule(
                    [d.model_copy(deep=True) for d in template_days],
                    deload_schedule,
                    d_templates,
                    foods_by_id=foods_map,
                )
                for d in d_days:
                    for m in d.meals:
                        all_food_ids.add(int(m.food_id))
                insight["deload_sessions"] = [_session_to_dict(d) for d in d_days]
                insight["deload_avg_target_calories"] = deload_avg

        block_insights.append(insight)
        if block.block_index == 0:
            first_block_days = applied
            first_schedule = block.schedule
            first_rest = rest_tpl
            first_templates = templates_by_kind

    foods_map = {}
    if all_food_ids:
        foods_map = {
            int(f.id): f for f in db.query(Food).filter(Food.id.in_(all_food_ids)).all()
        }
    for insight in block_insights:
        block = blocks[int(insight["block_index"])]
        rest_pref = None
        if preferred_foods_by_block:
            rest_pref = preferred_foods_by_block.get(int(insight["block_index"]))
        _, rest_tpl = _templates_for_schedule(
            pool,
            block.schedule,
            preferred=rest_pref,
            rotation_index=int(insight["block_index"]),
            fallback_fat=olive,
        )
        rest_nut, rest_meals = _rest_insight_from_template(block.schedule, rest_tpl, foods_map)
        insight["rest_day_nutrition"] = rest_nut
        insight["rest_day_meals"] = rest_meals

    cadence = "theo pha (≈ mỗi tháng)" if (include_deload_meals or block_size >= 4) else "mỗi 2 tuần"
    warning = (
        f"Calo và khẩu phần điều chỉnh {cadence} theo cân dự kiến; "
        "trong tuần vẫn cao hơn ngày tập strength, thấp hơn ngày nghỉ."
    )
    if (include_deload_meals or block_size >= 4) and goal_n == "lose_weight":
        warning += " Tuần deload gần maintenance để phục hồi."
    if used_ai:
        warning = "Thực đơn mẫu từ nguyên liệu tươi — " + warning
    else:
        warning = "Thực đơn ráp từ món bạn chọn — " + warning

    return MealPlanResult(
        templates=list(first_templates.values()),
        warning_vi=warning,
        used_ai_pool=used_ai,
        schedule=first_schedule,
        rest_day_template=first_rest,
        templates_by_kind=first_templates,
        nutrition_blocks=block_insights,
        foods_by_id=foods_map,
    )


def apply_nutrition_blocks_to_expanded_days(
    days: list[PlanDayIn],
    block_insights: list[dict[str, Any]],
    *,
    sessions_per_week: int,
    block_size: int = 2,
    deload_every_n_weeks: int | None = None,
    deload_weeks: list[int] | tuple[int, ...] | set[int] | None = None,
) -> list[PlanDayIn]:
    """Assign per-block meals and targets onto expanded multi-week plan days."""
    if not days or not block_insights or sessions_per_week <= 0:
        return days
    blocks_by_index = {int(b["block_index"]): b for b in block_insights}
    deload_set = {int(w) for w in (deload_weeks or [])}
    out: list[PlanDayIn] = []
    for day in days:
        week = parse_week_from_title(day.title_vi)
        block = None
        for b in block_insights:
            weeks_list = b.get("weeks") or []
            if week in weeks_list:
                block = b
                break
        if block is None:
            bi = min((week - 1) // block_size, max(blocks_by_index.keys()))
            block = blocks_by_index.get(bi) or block_insights[0]
        use_deload = bool(
            block.get("deload_sessions")
            and (
                (week in deload_set)
                or (
                    deload_every_n_weeks
                    and week > 0
                    and week % deload_every_n_weeks == 0
                )
            )
        )
        sessions = (
            block.get("deload_sessions") if use_deload else block.get("sessions")
        ) or []
        if not sessions:
            out.append(day)
            continue
        idx = (int(day.day_number) - 1) % sessions_per_week
        if idx >= len(sessions):
            idx = idx % len(sessions)
        sess = sessions[idx]
        meals = [PlanMealIn(**m) for m in sess.get("meals") or []]
        out.append(
            day.model_copy(
                update={
                    "meals": meals,
                    "meal_notes": dict(sess.get("meal_notes") or {}),
                    "target_calories": sess.get("target_calories"),
                    "target_protein_g": sess.get("target_protein_g"),
                    "target_carbs_g": sess.get("target_carbs_g"),
                    "target_fat_g": sess.get("target_fat_g"),
                }
            )
        )
    return out

def apply_meals_to_days(days: list[PlanDayIn], templates: list[DayTemplate]) -> list[PlanDayIn]:
    if not days or not templates:
        return days
    out: list[PlanDayIn] = []
    for i, day in enumerate(days):
        tmpl = templates[i % len(templates)]
        out.append(
            day.model_copy(
                update={
                    "meals": [m.model_copy() for m in tmpl.meals],
                    "meal_notes": dict(tmpl.meal_notes),
                }
            )
        )
    return out


def generate_meals(
    db: Session,
    payload: dict[str, Any],
    targets: NutritionTargets | None,
    *,
    plan_days: list[PlanDayIn] | None = None,
    goal: str = "maintain",
) -> MealPlanResult:
    if targets is None:
        return MealPlanResult(warning_vi="Thiếu chiều cao/cân nặng nên chưa tạo thực đơn.")
    try:
        pool, used_ai = load_meal_pool(db, payload)
    except BadRequestError:
        raise
    except SQLAlchemyError:
        logger.exception("meal pool query failed")
        return MealPlanResult(warning_vi="Chưa tạo được thực đơn từ kho thức ăn.")
    if not pool:
        return MealPlanResult(
            warning_vi="Kho thức ăn chưa đủ món an toàn để ráp thực đơn.",
            used_ai_pool=used_ai,
        )
    pool = _pool_with_dishes(db, pool)
    olive = _load_olive_oil(db)

    foods_map = {f.id: f for f in pool}
    if olive is not None:
        foods_map.setdefault(olive.id, olive)
    schedule: WeeklyCalorieSchedule | None = None
    templates_by_kind: dict[str, DayTemplate] = {}
    rest_day_template: DayTemplate | None = None

    if plan_days:
        gender = (payload.get("gender") or "male").lower()
        weight = float(payload.get("weight_kg") or 65)
        split_roles = [d.split_role for d in plan_days]
        schedule = build_weekly_calorie_schedule(
            goal=goal,
            avg_target=targets.target_calories,
            split_roles=split_roles,
            gender=gender if gender in {"male", "female"} else "male",
            weight_kg=weight,
            bmr=float(targets.bmr),
            base=targets,
        )
        seen_kcal: dict[int, str] = {}
        for slot in schedule.training:
            kcal = slot.targets.target_calories
            if kcal in seen_kcal:
                templates_by_kind[slot.session_kind] = templates_by_kind[seen_kcal[kcal]]
                continue
            built = build_day_templates(
                pool,
                slot.targets,
                count=1,
                fallback_fat=olive,
                weight_kg=_payload_weight_kg(payload),
            )
            if built:
                templates_by_kind[slot.session_kind] = built[0]
                seen_kcal[kcal] = slot.session_kind
        rest_built = build_day_templates(
            pool, schedule.rest, count=1, fallback_fat=olive, weight_kg=_payload_weight_kg(payload)
        )
        if rest_built:
            rest_day_template = rest_built[0]
            rest_notes = dict(rest_day_template.meal_notes)
            rest_notes["breakfast"] = (
                rest_notes.get("breakfast", _SLOT_NOTES["breakfast"])
                + " Thực đơn mẫu cho ngày nghỉ."
            )
            rest_day_template = DayTemplate(
                meals=rest_day_template.meals,
                meal_notes=rest_notes,
                totals=rest_day_template.totals,
            )
        warning = (
            "Thực đơn theo loại buổi (strength/cardio/full body) + mẫu riêng ngày nghỉ; "
            "calo thay đổi nhưng trung bình tuần giữ mục tiêu."
        )
        if used_ai:
            warning = "Thực đơn mẫu từ nguyên liệu tươi — " + warning
        else:
            warning = "Thực đơn ráp từ món bạn chọn — " + warning
        return MealPlanResult(
            templates=list(templates_by_kind.values()),
            warning_vi=warning,
            used_ai_pool=used_ai,
            schedule=schedule,
            rest_day_template=rest_day_template,
            templates_by_kind=templates_by_kind,
            foods_by_id=foods_map,
        )

    templates = build_day_templates(
        pool, targets, count=2, fallback_fat=olive, weight_kg=_payload_weight_kg(payload)
    )
    warning = None
    if used_ai:
        warning = "Thực đơn mẫu từ nguyên liệu tươi — lặp 2 mẫu trong tuần."
    else:
        warning = "Thực đơn ráp từ món bạn chọn — lặp 2 mẫu trong tuần."
    return MealPlanResult(
        templates=templates,
        warning_vi=warning,
        used_ai_pool=used_ai,
        foods_by_id=foods_map,
    )
