"""Household spoon/ml/g labels and line calories for cooking BOMs."""

from __future__ import annotations

import re
from typing import Any

TSP_ML = 5.0
TBSP_ML = 15.0

LIQUID_SLUG_PREFIXES = (
    "nuoc-",
    "dau-",
    "giam-",
    "mam-",
    "sua-",
)
LIQUID_SLUGS = frozenset(
    {
        "nuoc-mam",
        "nuoc-tuong",
        "nuoc-loc",
        "nuoc-cot-dua",
        "dau-an",
        "dau-oliu",
        "dau-me",
        "giam-gao",
        "mam-tom",
        "mam-ruoc",
        "ruou-trang",
    }
)

_GRAM_IN_LABEL = re.compile(r"(\d+(?:[.,]\d+)?)\s*g\b", re.I)


def fmt_qty(value: float) -> str:
    if abs(value - round(value)) < 1e-6:
        return str(int(round(value)))
    text = f"{value:.1f}".rstrip("0").rstrip(".")
    return text


def kcal_per_100g(food: Any) -> float | None:
    kcal = getattr(food, "kcal_100g", None)
    if kcal is not None:
        return float(kcal)
    if isinstance(food, dict) and food.get("kcal_100g") is not None:
        return float(food["kcal_100g"])
    calories = getattr(food, "calories", None)
    serving = getattr(food, "serving_grams", None)
    if isinstance(food, dict):
        calories = food.get("calories") if calories is None else calories
        serving = food.get("serving_grams") if serving is None else serving
    if calories is None or not serving:
        return None
    grams = float(serving)
    if grams <= 0:
        return None
    return float(calories) * 100.0 / grams


def line_calories(grams: float | None, food: Any | None) -> int | None:
    if grams is None or grams <= 0 or food is None:
        return None
    per100 = kcal_per_100g(food)
    if per100 is None:
        return None
    return int(round(grams * per100 / 100.0))


def is_liquid_slug(slug: str, category_slug: str | None = None) -> bool:
    s = (slug or "").strip().lower()
    if s in LIQUID_SLUGS:
        return True
    if s.startswith(LIQUID_SLUG_PREFIXES):
        return True
    cat = (category_slug or "").strip().lower()
    if cat == "gia-vi-mam-dau" and s.startswith(("nuoc", "dau", "giam", "mam")):
        return True
    return False


def _portion_grams(portions: list[dict] | None, *needles: str) -> float | None:
    for row in portions or []:
        label = str(row.get("label_vi") or "").casefold()
        if all(n in label for n in needles):
            try:
                grams = float(row.get("grams") or 0)
            except (TypeError, ValueError):
                continue
            if grams > 0:
                return grams
    return None


def spoon_units(portions: list[dict] | None) -> tuple[float | None, float | None]:
    """Return (tbsp_grams, tsp_grams) from catalog portions."""
    tbsp = _portion_grams(portions, "muỗng canh") or _portion_grams(portions, "muong canh")
    tsp = _portion_grams(portions, "muỗng cà phê") or _portion_grams(portions, "muong ca phe")
    if tbsp is None:
        tbsp = _portion_grams(portions, "muỗng", "15ml")
    if tsp is None:
        tsp = _portion_grams(portions, "muỗng", "5ml")
    return tbsp, tsp


def _fit_count(grams: float, unit_g: float) -> float | None:
    if unit_g <= 0 or grams <= 0:
        return None
    ratio = grams / unit_g
    half = round(ratio * 2) / 2
    if half < 0.5:
        return None
    if abs(grams - half * unit_g) <= 0.8:
        return half
    return None


def _household_prefix(label: str) -> str | None:
    text = (label or "").strip()
    if not text:
        return None
    stripped = _GRAM_IN_LABEL.sub("", text)
    stripped = re.sub(r"\([^)]*\)", "", stripped)
    stripped = re.sub(r"\s+", " ", stripped).strip(" -–,")
    if not stripped:
        return None
    if re.search(
        r"muỗng|muong|chén|chen|tép|tep|quả|qua|nhúm|nhum|củ|cu |lát|trai|trái|bó|bo ",
        stripped,
        re.I,
    ):
        return stripped
    return None


def format_amount_label(
    *,
    grams: float,
    slug: str = "",
    existing: str | None = None,
    portions: list[dict] | None = None,
    liquid: bool | None = None,
) -> str:
    gtxt = fmt_qty(grams)
    existing = (existing or "").strip()
    tbsp_g, tsp_g = spoon_units(portions)
    use_liquid = is_liquid_slug(slug) if liquid is None else liquid

    m_tbsp = re.search(r"(\d+(?:[.,]\d+)?)\s*muỗng\s+canh", existing, re.I)
    m_tsp = re.search(r"(\d+(?:[.,]\d+)?)\s*muỗng\s+cà\s*phê", existing, re.I)
    if m_tbsp:
        count = float(m_tbsp.group(1).replace(",", "."))
        ntxt = fmt_qty(count)
        if use_liquid:
            return f"{ntxt} muỗng canh ({fmt_qty(count * TBSP_ML)}ml ≈ {gtxt}g)"
        return f"{ntxt} muỗng canh (~{gtxt}g)"
    if m_tsp:
        count = float(m_tsp.group(1).replace(",", "."))
        ntxt = fmt_qty(count)
        if use_liquid:
            return f"{ntxt} muỗng cà phê ({fmt_qty(count * TSP_ML)}ml ≈ {gtxt}g)"
        return f"{ntxt} muỗng cà phê (~{gtxt}g)"

    for unit_g, unit_ml, name in (
        (tbsp_g, TBSP_ML, "muỗng canh"),
        (tsp_g, TSP_ML, "muỗng cà phê"),
    ):
        if unit_g is None:
            continue
        count = _fit_count(grams, unit_g)
        if count is None:
            continue
        ntxt = fmt_qty(count)
        if use_liquid:
            ml = fmt_qty(count * unit_ml)
            return f"{ntxt} {name} ({ml}ml ≈ {gtxt}g)"
        return f"{ntxt} {name} (~{gtxt}g)"

    prefix = _household_prefix(existing or "")
    if prefix:
        if _GRAM_IN_LABEL.search(existing or ""):
            if "≈" in (existing or "") or "~" in (existing or ""):
                return str(existing).strip()
            return f"{prefix} (~{gtxt}g)"
        return f"{prefix} (~{gtxt}g)"

    leftover = (existing or "").strip()
    leftover = _GRAM_IN_LABEL.sub("", leftover).strip(" -–,")
    leftover = re.sub(r"\s+", " ", leftover)
    if leftover and leftover.lower() not in {slug.replace("-", " ")}:
        return f"{gtxt}g {leftover}"
    return f"{gtxt}g"
