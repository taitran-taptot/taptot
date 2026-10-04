"""Category/tag mapping for the gen-lịch food picker (Kho thực phẩm)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from app.core.migrations.common import PROJECT_ROOT

PROTEIN_CATEGORY_SLUGS = frozenset(
    {
        "thit-gia-cam-noi-tang",
        "ca-thuy-hai-san",
        "trung-whey",
    }
)
CARB_CATEGORY_SLUGS = frozenset({"ngu-coc-hat"})
PRODUCE_CATEGORY_SLUGS = frozenset({"rau-cu-qua"})
DISH_CATEGORY_SLUGS = frozenset({"mon-an-truyen-thong", "mon-an"})
HIDDEN_PICKER_CATEGORY_SLUGS = frozenset({"gia-vi-mam-dau", "an-vat-do-uong"})
PICKER_CATEGORY_SLUGS = (
    PROTEIN_CATEGORY_SLUGS | CARB_CATEGORY_SLUGS | PRODUCE_CATEGORY_SLUGS | DISH_CATEGORY_SLUGS
)

FRUIT_TAGS = frozenset({"trai-cay", "nhom:trai-cay", "nhom:hoa-qua", "nhom:qua"})
CANONICAL_FRUIT_TAG = "trai-cay"

PICKER_MACRO_ROLES = frozenset(
    {"protein", "carb", "produce", "fruit", "dish", "meal_picker"}
)


def _norm_tag(value: Any) -> str:
    return str(value or "").strip().lower()


def food_has_fruit_tag(tags: Iterable[Any] | None) -> bool:
    for raw in tags or ():
        tag = _norm_tag(raw)
        if not tag:
            continue
        if tag in FRUIT_TAGS or tag.startswith("nhom:trai-cay") or tag.startswith("nhom:qua"):
            return True
    return False


def with_fruit_tag(tags: Iterable[Any] | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in tags or ():
        text = str(raw).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    if CANONICAL_FRUIT_TAG not in seen:
        out.append(CANONICAL_FRUIT_TAG)
    return out


def fruit_slugs_from_items(items: Iterable[dict[str, Any]]) -> set[str]:
    slugs: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        if not food_has_fruit_tag(item.get("tags")):
            continue
        slug = str(item.get("slug") or "").strip()
        if slug:
            slugs.add(slug)
    return slugs


def fruit_slugs_from_catalog_v2(path: Path | None = None) -> set[str]:
    seed_path = path or (PROJECT_ROOT / "seeds" / "foods_catalog_v2.json")
    if not seed_path.is_file():
        return set()
    raw = json.loads(seed_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return set()
    return fruit_slugs_from_items(raw)


def is_picker_dish(*, category_slug: str | None, food_kind: str | None, is_complete_meal: bool) -> bool:
    cat = (category_slug or "").strip().lower()
    kind = (food_kind or "").strip().lower()
    return cat in DISH_CATEGORY_SLUGS or kind == "dish" or bool(is_complete_meal)
