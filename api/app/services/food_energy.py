"""Atwater 4-4-9 energy checks and produce net-carb alignment."""

from __future__ import annotations

from typing import Any

ATWATER_TOLERANCE = 0.10
PRODUCE_CATEGORY_SLUGS = frozenset({"rau-cu-qua", "trai-cay-rau-cu"})
SKIP_ENERGY_SLUGS = frozenset({"nuoc-loc", "muoi"})


def _f(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def classic_atwater_kcal(protein_g: float, carbs_g: float, fat_g: float) -> float:
    return 4.0 * protein_g + 4.0 * carbs_g + 9.0 * fat_g


def modified_atwater_kcal(
    protein_g: float,
    carbs_g: float,
    fat_g: float,
    fiber_g: float = 0.0,
    *,
    carbs_include_fiber: bool = True,
) -> float:
    """FAO-style: net carb 4 kcal/g, fiber 2 kcal/g, fat 9, protein 4.

    If carbs_include_fiber is False, `carbs_g` is already net carb.
    """
    fiber = max(_f(fiber_g), 0.0)
    carbs = max(_f(carbs_g), 0.0)
    if carbs_include_fiber:
        net = max(carbs - fiber, 0.0)
    else:
        net = carbs
    return 4.0 * _f(protein_g) + 4.0 * net + 2.0 * fiber + 9.0 * _f(fat_g)


def relative_error(actual: float, expected: float) -> float:
    denom = max(abs(actual), abs(expected), 1.0)
    return abs(actual - expected) / denom


def is_produce_category(category_slug: str | None, tags: Any = None, macro_roles: Any = None) -> bool:
    slug = (category_slug or "").strip().lower()
    if slug in PRODUCE_CATEGORY_SLUGS:
        return True
    for raw in list(tags or []):
        if str(raw).strip().lower() in {"produce", "rau", "rau-cu"}:
            return True
        if str(raw).startswith("nhom:") and "rau" in str(raw).lower():
            return True
    return False


def already_net_carb(
    *,
    kcal_100g: float,
    protein_100g: float,
    carbs_100g: float,
    fat_100g: float,
    fiber_100g: float,
) -> bool:
    """True when stored C behaves as net carb (modified Atwater already matches)."""
    fiber = max(fiber_100g, 0.0)
    if fiber <= 0.05:
        return False
    as_net = modified_atwater_kcal(
        protein_100g, carbs_100g, fat_100g, fiber, carbs_include_fiber=False
    )
    as_total = modified_atwater_kcal(
        protein_100g, carbs_100g, fat_100g, fiber, carbs_include_fiber=True
    )
    err_net = relative_error(kcal_100g, as_net)
    err_total = relative_error(kcal_100g, as_total)
    return err_net <= ATWATER_TOLERANCE and err_net + 0.02 < err_total


def align_per_100g(
    *,
    kcal_100g: float,
    protein_100g: float,
    carbs_100g: float,
    fat_100g: float,
    fiber_100g: float | None,
    is_produce: bool,
) -> tuple[float, float, float, bool]:
    """Return (kcal_100g, carbs_100g, fiber_100g, changed)."""
    protein = max(_f(protein_100g), 0.0)
    carbs = max(_f(carbs_100g), 0.0)
    fat = max(_f(fat_100g), 0.0)
    fiber = max(_f(fiber_100g), 0.0)
    kcal = _f(kcal_100g)
    changed = False

    if is_produce and fiber > 0.05:
        net_already = already_net_carb(
            kcal_100g=kcal,
            protein_100g=protein,
            carbs_100g=carbs,
            fat_100g=fat,
            fiber_100g=fiber,
        )
        if carbs + 1e-9 >= fiber and not net_already:
            carbs = round(max(carbs - fiber, 0.0), 2)
            kcal = round(
                modified_atwater_kcal(protein, carbs, fat, fiber, carbs_include_fiber=False),
                2,
            )
            changed = True
        else:
            expected = modified_atwater_kcal(
                protein, carbs, fat, fiber, carbs_include_fiber=False
            )
            if relative_error(kcal, expected) > ATWATER_TOLERANCE:
                kcal = round(expected, 2)
                changed = True
    else:
        expected = classic_atwater_kcal(protein, carbs, fat)
        if relative_error(kcal, expected) > ATWATER_TOLERANCE:
            kcal = round(expected, 2)
            changed = True

    return kcal, carbs, fiber, changed


def apply_energy_alignment_dict(row: dict[str, Any], *, is_produce: bool | None = None) -> bool:
    """Mutate a seed-style food dict. Returns True if fields changed."""
    slug = str(row.get("slug") or "").strip()
    if slug in SKIP_ENERGY_SLUGS:
        return False
    if str(row.get("source_ref") or "").startswith("vn-fct"):
        return False
    kind = str(row.get("food_kind") or "ingredient").strip().lower()
    if kind == "dish":
        return False

    produce = is_produce
    if produce is None:
        produce = is_produce_category(
            str(row.get("category_slug") or ""),
            row.get("tags"),
            row.get("macro_roles"),
        ) and kind == "ingredient"

    serving_grams = _f(row.get("serving_grams"), 100.0) or 100.0
    kcal_100 = row.get("kcal_100g")
    protein_100 = row.get("protein_100g")
    carbs_100 = row.get("carbs_100g")
    fat_100 = row.get("fat_100g")
    fiber_100 = row.get("fiber_100g")
    if kcal_100 is None or protein_100 is None:
        scale = 100.0 / serving_grams if serving_grams else 0.0
        kcal_100 = _f(row.get("calories")) * scale
        protein_100 = _f(row.get("protein_g")) * scale
        carbs_100 = _f(row.get("carbs_g")) * scale
        fat_100 = _f(row.get("fat_g")) * scale
        fiber_100 = None if row.get("fiber_g") is None else _f(row.get("fiber_g")) * scale

    new_kcal, new_carbs, new_fiber, changed = align_per_100g(
        kcal_100g=_f(kcal_100),
        protein_100g=_f(protein_100),
        carbs_100g=_f(carbs_100),
        fat_100g=_f(fat_100),
        fiber_100g=None if fiber_100 is None else _f(fiber_100),
        is_produce=bool(produce),
    )
    if not changed:
        return False

    scale = serving_grams / 100.0
    row["kcal_100g"] = new_kcal
    row["protein_100g"] = _f(protein_100)
    row["carbs_100g"] = new_carbs
    row["fat_100g"] = _f(fat_100)
    row["fiber_100g"] = new_fiber
    row["calories"] = round(new_kcal * scale, 2)
    row["protein_g"] = round(_f(protein_100) * scale, 2)
    row["carbs_g"] = round(new_carbs * scale, 2)
    row["fat_g"] = round(_f(fat_100) * scale, 2)
    row["fiber_g"] = round(new_fiber * scale, 2)
    return True


def apply_energy_alignment_food(food: Any, *, category_slug: str | None = None) -> bool:
    """Mutate a Food ORM row. Returns True if fields changed."""
    row = {
        "slug": getattr(food, "slug", None),
        "source_ref": getattr(food, "source_ref", None),
        "food_kind": getattr(food, "food_kind", None) or "ingredient",
        "category_slug": category_slug or "",
        "tags": getattr(food, "tags", None) or [],
        "macro_roles": getattr(food, "macro_roles", None) or [],
        "kcal_100g": getattr(food, "kcal_100g", None),
        "protein_100g": getattr(food, "protein_100g", None),
        "carbs_100g": getattr(food, "carbs_100g", None),
        "fat_100g": getattr(food, "fat_100g", None),
        "fiber_100g": getattr(food, "fiber_100g", None),
        "serving_grams": getattr(food, "serving_grams", None) or 100,
        "calories": getattr(food, "calories", None),
        "protein_g": getattr(food, "protein_g", None),
        "carbs_g": getattr(food, "carbs_g", None),
        "fat_g": getattr(food, "fat_g", None),
        "fiber_g": getattr(food, "fiber_g", None),
    }
    if not apply_energy_alignment_dict(row):
        return False
    food.kcal_100g = row["kcal_100g"]
    food.protein_100g = row["protein_100g"]
    food.carbs_100g = row["carbs_100g"]
    food.fat_100g = row["fat_100g"]
    food.fiber_100g = row["fiber_100g"]
    food.calories = row["calories"]
    food.protein_g = row["protein_g"]
    food.carbs_g = row["carbs_g"]
    food.fat_g = row["fat_g"]
    food.fiber_g = row["fiber_g"]
    return True
