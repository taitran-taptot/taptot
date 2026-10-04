"""Check that measured liquids in the cook steps also sit on the ingredient BOM.

Only ## Sơ chế and ## Cách nấu count. Troubleshooting tips (thêm 50ml nếu khô)
are not part of the batch.
"""

from __future__ import annotations

import re
from typing import Any

WATER_SLUG = "nuoc-loc"
OIL_SLUGS = frozenset({"dau-an", "dau-oliu", "dau-me"})

_SECTION = re.compile(
    r"^##\s*(Sơ chế|Cách nấu)\s*$([\s\S]*?)(?=^##\s|\Z)",
    re.M,
)
# Plain water, not fish sauce / coconut water / broth.
_WATER_ML = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*ml\s+nước(?!\s*(?:mắm|tương|dừa|màu|dùng|hàng|cốt|lá|chan|lèo|chấm))",
    re.I,
)
_OIL_ML = re.compile(r"(\d+(?:[.,]\d+)?)\s*ml\s+dầu", re.I)


def method_text(content_md: str) -> str:
    parts = [match.group(2) for match in _SECTION.finditer(content_md or "")]
    return "\n".join(parts)


def _sum_ml(pattern: re.Pattern[str], text: str) -> float:
    total = 0.0
    for match in pattern.finditer(text):
        total += float(match.group(1).replace(",", "."))
    return total


def _grams_of(post: dict, slugs: set[str] | frozenset[str]) -> float:
    total = 0.0
    for ing in post.get("ingredients") or []:
        if not isinstance(ing, dict):
            continue
        if str(ing.get("food_slug") or "") in slugs:
            total += float(ing.get("grams") or 0)
    return total


def method_liquid_gaps(post: dict) -> list[str]:
    """Return human-readable gaps when a stated ml amount is missing from the BOM."""
    text = method_text(str(post.get("content_md") or ""))
    gaps: list[str] = []
    water_ml = _sum_ml(_WATER_ML, text)
    if water_ml > 0:
        grams = _grams_of(post, {WATER_SLUG})
        if grams <= 0:
            gaps.append(f"plain water {water_ml:g}ml missing from BOM")
        elif abs(grams - water_ml) > max(5.0, water_ml * 0.15):
            gaps.append(f"plain water BOM {grams:g}g vs method {water_ml:g}ml")
    oil_ml = _sum_ml(_OIL_ML, text)
    if oil_ml > 0 and _grams_of(post, OIL_SLUGS) <= 0:
        gaps.append(f"oil {oil_ml:g}ml missing from BOM")
    return gaps


def water_ingredient(ml: float) -> dict[str, Any]:
    grams = round(ml, 1)
    label_g = int(grams) if grams == int(grams) else grams
    ml_label = int(ml) if ml == int(ml) else ml
    return {
        "food_slug": WATER_SLUG,
        "grams": grams,
        "amount_label": f"{ml_label}ml nước lọc (≈{label_g}g)",
        "note": "Nước nấu, 0 kcal. Khối này nằm trong thành phẩm hoặc bốc hơi.",
    }


def with_stated_water(post: dict) -> dict:
    """Add nước lọc when the method states plain-water millilitres and the BOM does not."""
    text = method_text(str(post.get("content_md") or ""))
    water_ml = _sum_ml(_WATER_ML, text)
    if water_ml <= 0 or _grams_of(post, {WATER_SLUG}) > 0:
        return post
    ingredients = [dict(ing) for ing in (post.get("ingredients") or []) if isinstance(ing, dict)]
    ingredients.append(water_ingredient(water_ml))
    updated = dict(post)
    updated["ingredients"] = ingredients
    return updated
