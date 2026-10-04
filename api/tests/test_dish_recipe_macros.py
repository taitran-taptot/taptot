"""Traditional dish calories come from recipe BOMs, not Perfect Master."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "api"
sys.path.insert(0, str(ROOT / "seeds"))
sys.path.insert(0, str(API))

import _sync_dish_macros_from_recipes as dish_macros  # noqa: E402

COOKED_PRODUCT_SLUGS = frozenset(
    {
        "cha-trung",
        "com-trang",
        "rau-muong-luoc",
        "bap-ngot-luoc",
    }
)


def test_all_recipe_ingredient_slugs_resolve_macros() -> None:
    assert dish_macros.missing_ingredient_slugs() == []


def test_recipe_ingredients_have_grams_and_labels() -> None:
    for post in dish_macros.load_cooking_posts():
        ings = post.get("ingredients") or []
        assert ings, post.get("slug")
        for ing in ings:
            assert str(ing.get("food_slug") or "").strip(), post.get("slug")
            assert float(ing.get("grams") or 0) > 0, (post.get("slug"), ing.get("food_slug"))
            assert str(ing.get("amount_label") or "").strip(), (post.get("slug"), ing.get("food_slug"))
            assert re.search(r"\d+(?:[.,]\d+)?\s*g", str(ing.get("amount_label"))), (
                post.get("slug"),
                ing.get("food_slug"),
                ing.get("amount_label"),
            )


def test_recipe_bom_avoids_cooked_product_slugs() -> None:
    used: list[tuple[str, str]] = []
    dish_slugs = {
        str(d.get("slug"))
        for d in json.loads((ROOT / "seeds" / "foods_traditional_dishes.json").read_text(encoding="utf-8"))
    }
    for post in dish_macros.load_cooking_posts():
        for ing in post.get("ingredients") or []:
            slug = str(ing.get("food_slug") or "")
            if slug in COOKED_PRODUCT_SLUGS or slug in dish_slugs:
                used.append((str(post.get("slug")), slug))
    assert used == []


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
    assert macros["fiber_g"] == 1.0
    assert macros["serving_grams"] == 150.0
    batch = dish_macros.recipe_batch_macros(post, index)
    assert macros["kcal_100g"] == round(batch["kcal"] / post["yield_grams"] * 100, 2)


def test_com_tam_bom_uses_raw_egg_and_minced_pork() -> None:
    post = next(
        p for p in dish_macros.load_cooking_posts() if p["slug"] == "com-tam-suon-bi-cha-day-du"
    )
    slugs = {ing["food_slug"]: ing["grams"] for ing in post["ingredients"]}
    assert "cha-trung" not in slugs
    assert slugs["trung-ga-ca-qua-song"] == 100
    assert slugs["thit-lon-xay-song"] == 40
    macros = dish_macros.recipe_serving_macros(post)
    dish = next(
        d
        for d in json.loads((ROOT / "seeds" / "foods_traditional_dishes.json").read_text(encoding="utf-8"))
        if d["slug"] == "com-tam-suon-bi-cha-day-du"
    )
    assert float(dish["calories"]) == float(macros["calories"])
    assert float(dish["protein_g"]) == float(macros["protein_g"])
    assert float(dish["carbs_g"]) == float(macros["carbs_g"])
    assert float(dish["fat_g"]) == float(macros["fat_g"])
    assert float(dish["fiber_g"]) == float(macros["fiber_g"])
    assert dish.get("source_ref") == "recipe-bom"


def test_traditional_dish_seed_matches_recipe_bom() -> None:
    index = dish_macros.load_macro_index()
    posts = {p["slug"]: p for p in dish_macros.load_cooking_posts()}
    dishes = json.loads((ROOT / "seeds" / "foods_traditional_dishes.json").read_text(encoding="utf-8"))
    by_slug = {d["slug"]: d for d in dishes}
    for slug in ("com-trang-gao-te", "com-tam-suon-bi-cha-day-du"):
        macros = dish_macros.recipe_serving_macros(posts[slug], index)
        dish = by_slug[slug]
        assert float(dish["calories"]) == float(macros["calories"]), slug
        assert float(dish["protein_g"]) == float(macros["protein_g"]), slug
        assert float(dish["carbs_g"]) == float(macros["carbs_g"]), slug
        assert float(dish["fat_g"]) == float(macros["fat_g"]), slug
        assert float(dish["fiber_g"]) == float(macros["fiber_g"]), slug
        assert float(dish["serving_grams"]) == float(macros["serving_grams"]), slug
        assert dish.get("prep_state") == "cooked"
        assert dish.get("source_ref") == "recipe-bom"
