"""Traditional dish calories come from cooking-post ingredient BOMs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "seeds"))

import _sync_dish_macros_from_recipes as dish_macros  # noqa: E402


def test_all_recipe_ingredient_slugs_resolve_macros() -> None:
    assert dish_macros.missing_ingredient_slugs() == []


def test_com_trang_serving_macros_match_gao_te_bom() -> None:
    index = dish_macros.load_macro_index()
    assert index["gao-te"]["kcal_100g"] == 365
    post = next(p for p in dish_macros.load_cooking_posts() if p["slug"] == "com-trang-gao-te")
    assert post["servings"] == 4
    assert post["yield_grams"] == 600
    slugs = {ing["food_slug"]: ing["grams"] for ing in post["ingredients"]}
    assert slugs["gao-te"] == 320
    macros = dish_macros.recipe_serving_macros(post, index)
    assert macros["calories"] == 292
    assert macros["protein_g"] == 5.7
    assert macros["carbs_g"] == 64.0
    assert macros["fat_g"] == 0.6
    assert macros["serving_grams"] == 150.0


def test_traditional_dish_seed_matches_recipe_macros() -> None:
    index = dish_macros.load_macro_index()
    posts = {p["slug"]: p for p in dish_macros.load_cooking_posts()}
    dishes = json.loads((ROOT / "seeds" / "foods_traditional_dishes.json").read_text(encoding="utf-8"))
    by_slug = {d["slug"]: d for d in dishes}
    for slug in (
        "com-trang-gao-te",
        "bun-cha-ha-noi",
        "thit-kho-tau-nuoc-dua",
        "com-tam-suon-bi-cha-day-du",
    ):
        expected = dish_macros.recipe_serving_macros(posts[slug], index)
        dish = by_slug[slug]
        assert dish["calories"] == expected["calories"], slug
        assert dish["protein_g"] == expected["protein_g"], slug
        assert dish["carbs_g"] == expected["carbs_g"], slug
        assert dish["fat_g"] == expected["fat_g"], slug
        assert dish["serving_grams"] == expected["serving_grams"], slug
