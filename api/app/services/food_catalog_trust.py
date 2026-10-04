"""Internal consistency checks for raw ingredients.

Per-100g values stay the authority. This does not invent macros from an outside table;
it flags rows that disagree with themselves or store one piece as 100g.
"""

from __future__ import annotations

import re
from typing import Any

from app.services.food_energy import (
    SKIP_ENERGY_SLUGS,
    classic_atwater_kcal,
    is_produce_category,
    modified_atwater_kcal,
    relative_error,
)

_PIECE = re.compile(r"(quả|cái|miếng)", re.I)
_HAS_100G = re.compile(r"100\s*g", re.I)


def _f(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def ingredient_issues(row: dict) -> list[str]:
    kind = str(row.get("food_kind") or "ingredient")
    if kind == "dish":
        return []
    issues: list[str] = []
    slug = str(row.get("slug") or "")
    if not str(row.get("source_ref") or "").strip():
        issues.append("missing_source")

    kcal = _f(row.get("kcal_100g"))
    grams = _f(row.get("serving_grams")) or 0.0
    calories = _f(row.get("calories"))
    if kcal is not None and grams > 0 and calories is not None:
        expected = kcal * grams / 100.0
        if abs(expected - calories) > max(1.0, 0.02 * abs(expected)):
            issues.append("serving_kcal_drift")

    protein_100 = _f(row.get("protein_100g"))
    protein = _f(row.get("protein_g"))
    if protein_100 is not None and grams > 0 and protein is not None:
        expected_p = protein_100 * grams / 100.0
        if abs(expected_p - protein) > max(0.6, 0.05 * abs(expected_p)):
            issues.append("serving_protein_drift")

    label = str(row.get("serving_size") or "")
    if (
        _PIECE.search(label)
        and not _HAS_100G.search(label)
        and grams >= 99
        and abs(grams - 100) < 1
    ):
        issues.append("piece_as_100g")

    if kcal is not None and slug not in SKIP_ENERGY_SLUGS and kcal > 5:
        protein_a = protein_100 or 0.0
        carbs_a = _f(row.get("carbs_100g")) or 0.0
        fat_a = _f(row.get("fat_100g")) or 0.0
        fiber_a = _f(row.get("fiber_100g")) or 0.0
        classic = classic_atwater_kcal(protein_a, carbs_a, fat_a)
        modified = modified_atwater_kcal(protein_a, carbs_a, fat_a, fiber_a)
        err = min(relative_error(kcal, classic), relative_error(kcal, modified))
        produce = is_produce_category(
            str(row.get("category_slug") or ""),
            row.get("tags"),
            row.get("macro_roles"),
        )
        if produce:
            net = modified_atwater_kcal(
                protein_a, carbs_a, fat_a, fiber_a, carbs_include_fiber=False
            )
            err = min(err, relative_error(kcal, net))
        if err > 0.10:
            issues.append("atwater")
    return issues


def audit_ingredients(rows: list[dict]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        slug = str(row.get("slug") or "").strip()
        if not slug:
            continue
        issues = ingredient_issues(row)
        if issues:
            found[slug] = issues
    return found
