"""Cooked-dish nutrition from raw ingredient weights.

Energy and macros of a batch equal the sum of raw grams × per-100g values.
Water gained or lost changes edible yield, not the batch total.
"""

from __future__ import annotations

from typing import Any

MACRO_KEYS = ("kcal", "protein_g", "carbs_g", "fat_g", "fiber_g")

NUTRITION_NOTE = (
    "Số liệu tính từ khối lượng nguyên liệu sống. "
    "Nước thêm vào hoặc nước bốc hơi làm thành phẩm nặng hơn hoặc nhẹ hơn, "
    "nên kcal trên 100g sau khi nấu khác định lượng, "
    "nhưng tổng calo và macro cả mẻ giữ nguyên."
)

DEFAULT_SOURCE_TITLE = (
    "Định lượng theo công thức trong bài. "
    "Dinh dưỡng lấy từ bảng per 100g của nguyên liệu sống, không ước lượng thêm sau khi nấu."
)


def _attr(food: Any, name: str) -> float | None:
    if isinstance(food, dict):
        if name not in food or food[name] is None:
            return None
        return float(food[name])
    value = getattr(food, name, None)
    if value is None:
        return None
    return float(value)


def food_per_100g(food: Any) -> dict[str, float] | None:
    """Per-100g kcal and macros. Serving columns are used only when per-100g is missing."""
    if food is None:
        return None
    kcal = _attr(food, "kcal_100g")
    protein = _attr(food, "protein_100g")
    carbs = _attr(food, "carbs_100g")
    fat = _attr(food, "fat_100g")
    fiber = _attr(food, "fiber_100g")
    grams = _attr(food, "serving_grams")
    if kcal is None:
        calories = _attr(food, "calories")
        if calories is None or not grams or grams <= 0:
            return None
        scale = 100.0 / grams
        kcal = calories * scale
        protein = (_attr(food, "protein_g") or 0.0) * scale
        carbs = (_attr(food, "carbs_g") or 0.0) * scale
        fat = (_attr(food, "fat_g") or 0.0) * scale
        fiber = (_attr(food, "fiber_g") or 0.0) * scale
    return {
        "kcal": float(kcal or 0),
        "protein_g": float(protein or 0),
        "carbs_g": float(carbs or 0),
        "fat_g": float(fat or 0),
        "fiber_g": float(fiber or 0),
    }


def scale_line(per100: dict[str, float], grams: float) -> dict[str, float]:
    factor = float(grams) / 100.0
    return {key: float(per100.get(key) or 0) * factor for key in MACRO_KEYS}


def sum_lines(lines: list[dict[str, float]]) -> dict[str, float]:
    totals = {key: 0.0 for key in MACRO_KEYS}
    for line in lines:
        for key in MACRO_KEYS:
            totals[key] += float(line.get(key) or 0)
    return totals


def display_macros(raw: dict[str, float]) -> dict[str, float | int]:
    return {
        "calories": int(round(float(raw.get("kcal") or 0))),
        "protein_g": round(float(raw.get("protein_g") or 0), 1),
        "carbs_g": round(float(raw.get("carbs_g") or 0), 1),
        "fat_g": round(float(raw.get("fat_g") or 0), 1),
        "fiber_g": round(float(raw.get("fiber_g") or 0), 1),
    }


def _serving_grams(yield_grams: float, servings: int) -> float:
    each = float(yield_grams) / servings
    if each % 1:
        return round(each, 1)
    return each


def cooked_profile(
    batch_raw: dict[str, float],
    servings: int | float,
    yield_grams: float,
) -> dict[str, Any]:
    """Batch totals, one serving, cooked per 100g, and k/N slices of the batch."""
    n = int(servings)
    edible = float(yield_grams)
    if n <= 0:
        raise ValueError("servings must be > 0")
    if edible <= 0:
        raise ValueError("yield_grams must be > 0")

    def scaled(factor: float) -> dict[str, float]:
        return {key: float(batch_raw.get(key) or 0) * factor for key in MACRO_KEYS}

    per100_raw = scaled(100.0 / edible)
    portions: list[dict[str, Any]] = []
    for k in range(1, n + 1):
        row = display_macros(scaled(k / n))
        row["k"] = k
        row["n"] = n
        row["label"] = f"{k}/{n}"
        row["grams"] = round(edible * k / n, 1)
        portions.append(row)

    per100_display = display_macros(per100_raw)
    per100_display.update(
        {
            "kcal_100g": round(per100_raw["kcal"], 2),
            "protein_100g": round(per100_raw["protein_g"], 2),
            "carbs_100g": round(per100_raw["carbs_g"], 2),
            "fat_100g": round(per100_raw["fat_g"], 2),
            "fiber_100g": round(per100_raw["fiber_g"], 2),
        }
    )
    serving = display_macros(scaled(1 / n))
    serving["grams"] = _serving_grams(edible, n)
    return {
        "batch": display_macros(batch_raw),
        "serving": serving,
        "per_100g": per100_display,
        "portions": portions,
        "nutrition_note": NUTRITION_NOTE,
    }


def index_per_100g(macro: dict[str, float]) -> dict[str, float]:
    """Adapt seed rows that store kcal_100g / protein_100g keys."""
    if "kcal" in macro and "kcal_100g" not in macro:
        return {
            "kcal": float(macro.get("kcal") or 0),
            "protein_g": float(macro.get("protein_g") or 0),
            "carbs_g": float(macro.get("carbs_g") or 0),
            "fat_g": float(macro.get("fat_g") or 0),
            "fiber_g": float(macro.get("fiber_g") or 0),
        }
    return {
        "kcal": float(macro.get("kcal_100g") or 0),
        "protein_g": float(macro.get("protein_100g") or 0),
        "carbs_g": float(macro.get("carbs_100g") or 0),
        "fat_g": float(macro.get("fat_100g") or 0),
        "fiber_g": float(macro.get("fiber_100g") or 0),
    }
