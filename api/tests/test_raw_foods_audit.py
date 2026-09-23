"""Basic integrity checks for the Excel-derived foods catalog."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SEEDS = ROOT / "seeds"
CATALOG = SEEDS / "foods_catalog_v2.json"
CATEGORIES = SEEDS / "food_categories.json"

EXPECTED_CATEGORY_SLUGS = {
    "rau-cu-qua",
    "thit-gia-cam-noi-tang",
    "ca-thuy-hai-san",
    "trung-whey",
    "mon-an-truyen-thong",
    "an-vat-do-uong",
    "gia-vi-mam-dau",
}


@pytest.fixture(scope="module")
def foods() -> list[dict]:
    assert CATALOG.exists(), f"missing {CATALOG}"
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    return data


@pytest.fixture(scope="module")
def categories() -> list[dict]:
    assert CATEGORIES.exists(), f"missing {CATEGORIES}"
    data = json.loads(CATEGORIES.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    return data


def test_categories_match_excel_aisles(categories: list[dict]) -> None:
    slugs = {c["slug"] for c in categories}
    assert slugs == EXPECTED_CATEGORY_SLUGS


def test_catalog_size_and_unique_slugs(foods: list[dict]) -> None:
    assert len(foods) >= 400
    slugs = [f["slug"] for f in foods]
    assert len(slugs) == len(set(slugs))


def test_foods_have_subgroup_tags_and_macros(foods: list[dict]) -> None:
    for f in foods[:50]:
        tags = f.get("tags") or []
        assert any(str(t).startswith("nhom:") for t in tags), f["slug"]
        assert any(str(t).startswith("nhom_vi:") for t in tags), f["slug"]
        assert f.get("category_slug") in EXPECTED_CATEGORY_SLUGS
        assert float(f.get("calories") or 0) >= 0
        assert f.get("source_ref") == "excel:csdl-dinh-duong-vn-2026"


def test_dish_and_packaged_kinds(foods: list[dict]) -> None:
    dishes = [f for f in foods if f.get("food_kind") == "dish"]
    packaged = [f for f in foods if f.get("food_kind") == "packaged"]
    assert len(dishes) >= 40
    assert len(packaged) >= 50
    assert all(f.get("category_slug") == "mon-an-truyen-thong" for f in dishes)


def test_traditional_dishes_seed_is_empty() -> None:
    path = SEEDS / "foods_traditional_dishes.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == []


def test_food_images_map_points_to_existing_jpegs() -> None:
    path = SEEDS / "food_images.json"
    assert path.exists()
    mapping = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(mapping, dict)
    assert mapping
    media = ROOT / "uploads" / "media"
    for slug, rel in mapping.items():
        assert isinstance(slug, str) and slug
        assert isinstance(rel, str) and rel.replace("\\", "/").startswith("foods/")
        dest = media / rel.replace("\\", "/").lstrip("/")
        assert dest.is_file(), f"{slug} -> {rel}"
