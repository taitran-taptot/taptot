"""Category/tag mapping for the gen-lịch food picker (Kho thực phẩm)."""

from __future__ import annotations

import json
import re
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
        if "hoa-qua" in tag or tag.startswith("nhom_vi:hoa"):
            return True
    return False


# Hyphen stems / slug parts for the Excel produce aisle (many fruit rows have empty tags).
_FRUIT_SLUG_STEMS = (
    "chuoi",
    "xoai",
    "cam-sanh",
    "quyt",
    "buoi",
    "kiwi",
    "nho",
    "thanh-long",
    "nhan",
    "vai-thieu",
    "vu-sua",
    "dau-tay",
    "hong-xiem",
    "hong-gion",
    "chanh-leo",
    "chanh-day",
    "dua-hau",
    "dua-le",
    "dua-luoi",
    "dua-thom",
    "dua-bo",
    "com-dua",
    "bo-sap",
    "khe",
    "coc-non",
    "coc-gia",
    "tao-ta",
    "tao-tay",
    "du-du",
    "mit",
    "man-hau",
    "roi-man",
    "lekima",
    "oi-oi",
    "oi-gang",
    "oi-le",
    "sau-rieng",
    "chom-chom",
    "mang-cut",
    "mang-cau",
    "le-mac",
)
_FRUIT_SLUG_PARTS = frozenset(
    {
        "chuoi",
        "xoai",
        "cam",
        "quyt",
        "buoi",
        "kiwi",
        "nho",
        "vai",
        "nhan",
        "mit",
        "khe",
        "tao",
        "oi",
        "lekima",
        "cherry",
    }
)
_NOT_FRUIT_SLUG_NEEDLES = (
    "ca-chua",
    "dua-chuot",
    "dua-leo",
    "ot-chuong",
    "qua-su-su",
)


def _slug_has_stem(slug: str, stem: str) -> bool:
    return (
        slug == stem
        or slug.startswith(stem + "-")
        or f"-{stem}-" in slug
        or slug.endswith("-" + stem)
    )


def food_looks_like_fruit(
    *,
    slug: str | None = None,
    name_vi: str | None = None,
    tags: Iterable[Any] | None = None,
) -> bool:
    """True for fruit rows even when the produce aisle left tags empty."""
    if food_has_fruit_tag(tags):
        return True
    s = str(slug or "").strip().lower()
    if not s:
        return False
    if any(needle in s for needle in _NOT_FRUIT_SLUG_NEEDLES):
        return False
    if any(_slug_has_stem(s, stem) for stem in _FRUIT_SLUG_STEMS):
        return True
    parts = {p for p in s.split("-") if p}
    return bool(parts & _FRUIT_SLUG_PARTS)


# GI / tỉnh / vùng trồng commonly glued onto fruit display names.
_FRUIT_PLACE_PHRASES = tuple(
    sorted(
        {
            "cát hòa lộc",
            "hòa lộc",
            "ninh thuận",
            "lục ngạn",
            "an phước",
            "lò rèn",
            "năm roi",
            "đà lạt",
            "sa pa",
            "cái bè",
            "vĩnh kim",
            "bắc giang",
            "tiền giang",
            "vĩnh long",
            "bến tre",
            "lâm đồng",
            "khánh hòa",
            "bình thuận",
            "đồng nai",
            "long khánh",
            "xuân lộc",
            "cam lâm",
            "mộc châu",
            "bắc hà",
            "phan rang",
            "nha trang",
            "hà nội",
            "hồ chí minh",
            "sài gòn",
            "đà nẵng",
            "cần thơ",
            "huế",
            "hội an",
            "sơn la",
            "hà giang",
            "lào cai",
            "yên bái",
            "tuyên quang",
            "phú thọ",
            "hòa bình",
            "ninh bình",
            "thanh hóa",
            "nghệ an",
            "hà tĩnh",
            "quảng bình",
            "quảng trị",
            "quảng nam",
            "quảng ngãi",
            "bình định",
            "phú yên",
            "ninh phước",
            "bình dương",
            "tây ninh",
            "bà rịa",
            "vũng tàu",
            "long an",
            "đồng tháp",
            "an giang",
            "kiên giang",
            "cà mau",
            "bạc liêu",
            "sóc trăng",
            "trà vinh",
            "vĩnh phúc",
            "bắc ninh",
            "hải dương",
            "hải phòng",
            "hưng yên",
            "thái bình",
            "nam định",
            "hà nam",
            "thái nguyên",
            "bắc kạn",
            "cao bằng",
            "lạng sơn",
            "quảng ninh",
            "kon tum",
            "gia lai",
            "đắk lắk",
            "đắk nông",
            "đăk lắk",
            "đăk nông",
        },
        key=len,
        reverse=True,
    )
)


def strip_fruit_place_name(name: str | None) -> str:
    """Drop tỉnh / vùng trồng glued onto fruit names. Keep variety words (tiêu, tây, sáp)."""
    text = str(name or "").strip()
    if not text:
        return ""
    for phrase in _FRUIT_PLACE_PHRASES:
        text = re.sub(rf"\(\s*{re.escape(phrase)}\s*\)", "", text, flags=re.IGNORECASE)
        text = re.sub(rf"[\s/|,;–—-]+{re.escape(phrase)}\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"\s*/\s*$", "", text)
    text = re.sub(r"^\s*/\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" /,-")


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


def roles_from_category_slug(category_slug: str | None) -> list[str]:
    slug = (category_slug or "").strip().lower()
    if slug in PROTEIN_CATEGORY_SLUGS:
        return ["protein"]
    if slug in CARB_CATEGORY_SLUGS:
        return ["carb"]
    if slug in PRODUCE_CATEGORY_SLUGS:
        return ["produce"]
    return []


def is_picker_dish(*, category_slug: str | None, food_kind: str | None, is_complete_meal: bool) -> bool:
    cat = (category_slug or "").strip().lower()
    kind = (food_kind or "").strip().lower()
    return cat in DISH_CATEGORY_SLUGS or kind == "dish" or bool(is_complete_meal)
