"""Convert household amounts to grams. All nutrition math stays in grams.

Volume uses density_g_per_ml when set, otherwise a spoon portion labeled with ml,
otherwise the known densities below. Piece units (quả, cái, miếng) use that food's
own portion grams — never a global piece weight.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

TSP_ML = 5.0
TBSP_ML = 15.0

# Densities already implied by catalog spoon portions, plus water at 1 g/ml.
KNOWN_DENSITY_G_PER_ML: dict[str, float] = {
    "nuoc-loc": 1.0,
    "nuoc-mam": 1.2,  # pantry: 1 muỗng canh 15ml = 18g
    "dau-an": 14.0 / 15.0,  # pantry: 1 muỗng canh 15ml = 14g
    "dau-oliu": 0.91,
    "nuoc-tuong": 1.15,
}

_MASS = {"g": 1.0, "kg": 1000.0, "mg": 0.001}

_UNIT_ALIASES = {
    "g": "g",
    "gram": "g",
    "kg": "kg",
    "mg": "mg",
    "ml": "ml",
    "l": "l",
    "lit": "l",
    "tsp": "tsp",
    "thia ca phe": "tsp",
    "muong ca phe": "tsp",
    "tbsp": "tbsp",
    "thia canh": "tbsp",
    "muong canh": "tbsp",
    "muong": "tbsp",
    "thia": "tbsp",
    "mieng": "mieng",
    "qua": "qua",
    "cai": "cai",
}


def _fold(text: str) -> str:
    raw = (text or "").strip().lower().replace("đ", "d")
    raw = unicodedata.normalize("NFD", raw)
    raw = "".join(ch for ch in raw if unicodedata.category(ch) != "Mn")
    raw = raw.replace("đ", "d")
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw


def canonical_unit(unit: str) -> str:
    key = _fold(unit)
    if key not in _UNIT_ALIASES:
        raise ValueError(f"unsupported unit: {unit}")
    return _UNIT_ALIASES[key]


def _portion_rows(portions: list[dict] | None) -> list[dict]:
    return [row for row in (portions or []) if isinstance(row, dict)]


def _portion_grams(portions: list[dict] | None, *needles: str) -> float | None:
    folded = [_fold(n) for n in needles]
    for row in _portion_rows(portions):
        label = _fold(str(row.get("label_vi") or ""))
        if all(n in label for n in folded):
            try:
                grams = float(row.get("grams") or 0)
            except (TypeError, ValueError):
                continue
            if grams > 0:
                return grams
    return None


def density_g_per_ml(
    *,
    slug: str = "",
    density: float | None = None,
    portions: list[dict] | None = None,
) -> float | None:
    if density is not None and float(density) > 0:
        return float(density)
    tbsp = _portion_grams(portions, "15ml")
    if tbsp:
        return tbsp / TBSP_ML
    tsp = _portion_grams(portions, "5ml")
    if tsp:
        return tsp / TSP_ML
    known = KNOWN_DENSITY_G_PER_ML.get((slug or "").strip())
    if known:
        return known
    return None


def _piece_grams(portions: list[dict] | None, unit: str) -> float | None:
    word = {"mieng": "mieng", "qua": "qua", "cai": "cai"}[unit]
    return _portion_grams(portions, word)


def to_grams(
    quantity: float,
    unit: str,
    *,
    slug: str = "",
    density: float | None = None,
    portions: list[dict] | None = None,
) -> float:
    """Return grams for a household quantity. Raises ValueError when conversion is impossible."""
    qty = float(quantity)
    if qty < 0:
        raise ValueError("quantity must be >= 0")
    kind = canonical_unit(unit)
    if kind in _MASS:
        return qty * _MASS[kind]

    if kind in {"ml", "l", "tsp", "tbsp"}:
        dens = density_g_per_ml(slug=slug, density=density, portions=portions)
        if kind == "tsp":
            piece = _portion_grams(portions, "ca phe")
            if piece:
                return qty * piece
            if dens is None:
                raise ValueError("missing density for teaspoon")
            return qty * TSP_ML * dens
        if kind == "tbsp":
            piece = _portion_grams(portions, "canh")
            if piece:
                return qty * piece
            if dens is None:
                raise ValueError("missing density for tablespoon")
            return qty * TBSP_ML * dens
        if dens is None:
            raise ValueError("missing density for volume")
        ml = qty * 1000.0 if kind == "l" else qty
        return ml * dens

    piece = _piece_grams(portions, kind)
    if piece is None:
        raise ValueError(f"no portion grams for {unit}")
    return qty * piece


def macros_for_grams(per100: dict[str, float] | None, grams: float) -> dict[str, float | int] | None:
    from app.services.recipe_nutrition import display_macros, scale_line

    if per100 is None:
        return None
    return display_macros(scale_line(per100, grams))
