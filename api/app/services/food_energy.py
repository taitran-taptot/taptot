"""Classic Atwater 4-4-9 energy checks. Carbs are total carbohydrate; no fiber."""

from __future__ import annotations

from typing import Any

ATWATER_TOLERANCE = 0.05
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


def _is_raw_ingredient(row: dict[str, Any]) -> bool:
    kind = str(row.get("food_kind") or "ingredient").strip().lower()
    if kind == "dish":
        return False
    prep = str(row.get("prep_state") or "raw").strip().lower()
    return prep == "raw"


def align_per_100g(
    *,
    kcal_100g: float,
    protein_100g: float,
    carbs_100g: float,
    fat_100g: float,
) -> tuple[float, bool]:
    """Return (kcal_100g, changed). Never rewrites protein/carbs/fat."""
    protein = max(_f(protein_100g), 0.0)
    carbs = max(_f(carbs_100g), 0.0)
    fat = max(_f(fat_100g), 0.0)
    kcal = _f(kcal_100g)
    expected = classic_atwater_kcal(protein, carbs, fat)
    if relative_error(kcal, expected) > ATWATER_TOLERANCE:
        return round(expected, 2), True
    return kcal, False


def apply_energy_alignment_dict(row: dict[str, Any], *, is_produce: bool | None = None) -> bool:
    """Mutate a seed-style food dict. Returns True if kcal fields changed."""
    del is_produce  # produce no longer uses a separate energy path
    slug = str(row.get("slug") or "").strip()
    if slug in SKIP_ENERGY_SLUGS:
        return False
    if not _is_raw_ingredient(row):
        return False

    serving_grams = _f(row.get("serving_grams"), 100.0) or 100.0
    kcal_100 = row.get("kcal_100g")
    protein_100 = row.get("protein_100g")
    carbs_100 = row.get("carbs_100g")
    fat_100 = row.get("fat_100g")
    if kcal_100 is None or protein_100 is None:
        scale = 100.0 / serving_grams if serving_grams else 0.0
        kcal_100 = _f(row.get("calories")) * scale
        protein_100 = _f(row.get("protein_g")) * scale
        carbs_100 = _f(row.get("carbs_g")) * scale
        fat_100 = _f(row.get("fat_g")) * scale

    new_kcal, changed = align_per_100g(
        kcal_100g=_f(kcal_100),
        protein_100g=_f(protein_100),
        carbs_100g=_f(carbs_100),
        fat_100g=_f(fat_100),
    )
    if not changed:
        return False

    scale = serving_grams / 100.0
    row["kcal_100g"] = new_kcal
    row["protein_100g"] = _f(protein_100)
    row["carbs_100g"] = _f(carbs_100)
    row["fat_100g"] = _f(fat_100)
    row["calories"] = round(new_kcal * scale, 2)
    row["protein_g"] = round(_f(protein_100) * scale, 2)
    row["carbs_g"] = round(_f(carbs_100) * scale, 2)
    row["fat_g"] = round(_f(fat_100) * scale, 2)
    return True


def apply_energy_alignment_food(food: Any, *, category_slug: str | None = None) -> bool:
    """Mutate a Food ORM row. Returns True if fields changed."""
    del category_slug
    row = {
        "slug": getattr(food, "slug", None),
        "food_kind": getattr(food, "food_kind", None) or "ingredient",
        "prep_state": getattr(food, "prep_state", None) or "raw",
        "kcal_100g": getattr(food, "kcal_100g", None),
        "protein_100g": getattr(food, "protein_100g", None),
        "carbs_100g": getattr(food, "carbs_100g", None),
        "fat_100g": getattr(food, "fat_100g", None),
        "serving_grams": getattr(food, "serving_grams", None) or 100,
        "calories": getattr(food, "calories", None),
        "protein_g": getattr(food, "protein_g", None),
        "carbs_g": getattr(food, "carbs_g", None),
        "fat_g": getattr(food, "fat_g", None),
    }
    if not apply_energy_alignment_dict(row):
        return False
    food.kcal_100g = row["kcal_100g"]
    food.protein_100g = row["protein_100g"]
    food.carbs_100g = row["carbs_100g"]
    food.fat_100g = row["fat_100g"]
    food.calories = row["calories"]
    food.protein_g = row["protein_g"]
    food.carbs_g = row["carbs_g"]
    food.fat_g = row["fat_g"]
    return True
