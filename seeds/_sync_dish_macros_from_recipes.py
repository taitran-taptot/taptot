"""Compute traditional-dish macros from cooking-post ingredient BOMs."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEEDS = ROOT / "seeds"
COOKING_POSTS = SEEDS / "cooking_posts"
DISHES_PATH = SEEDS / "foods_traditional_dishes.json"
API = ROOT / "api"

if str(API) not in sys.path:
    sys.path.insert(0, str(API))

from app.services.recipe_nutrition import (  # noqa: E402
    cooked_profile,
    index_per_100g,
    scale_line,
    sum_lines,
)

Macro = dict[str, float]


def _food_rows(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        foods = payload.get("foods")
        if isinstance(foods, list):
            return [row for row in foods if isinstance(row, dict)]
    return []


def _as_macro(row: dict) -> Macro | None:
    slug = str(row.get("slug") or "").strip()
    if not slug:
        return None
    kcal = row.get("kcal_100g")
    protein = row.get("protein_100g")
    carbs = row.get("carbs_100g")
    fat = row.get("fat_100g")
    fiber = row.get("fiber_100g")
    if kcal is None:
        grams = float(row.get("serving_grams") or 0)
        calories = row.get("calories")
        if calories is None or grams <= 0:
            return None
        scale = 100.0 / grams
        kcal = float(calories) * scale
        protein = float(row.get("protein_g") or 0) * scale
        carbs = float(row.get("carbs_g") or 0) * scale
        fat = float(row.get("fat_g") or 0) * scale
        fiber = float(row.get("fiber_g") or 0) * scale
    return {
        "kcal_100g": float(kcal or 0),
        "protein_100g": float(protein or 0),
        "carbs_100g": float(carbs or 0),
        "fat_100g": float(fat or 0),
        "fiber_100g": float(fiber or 0),
    }


def _merge_map() -> dict[str, str]:
    import sys

    api_root = ROOT / "api"
    if str(api_root) not in sys.path:
        sys.path.insert(0, str(api_root))
    from app.core.migrations.ensures import DEPRECATED_FOOD_MERGES

    return dict(DEPRECATED_FOOD_MERGES)


def load_macro_index() -> dict[str, Macro]:
    """kcal/protein/carbs/fat per 100g, keyed by food slug (including merge aliases)."""
    index: dict[str, Macro] = {}
    paths = (
        SEEDS / "foods_catalog_v2.json",
        SEEDS / "foods_cooking_pantry.json",
        SEEDS / "grain_nut_foods.json",
        SEEDS / "foods_recipe_macros.json",
    )
    for path in paths:
        if not path.is_file():
            continue
        for row in _food_rows(json.loads(path.read_text(encoding="utf-8"))):
            slug = str(row.get("slug") or "").strip()
            macro = _as_macro(row)
            if slug and macro is not None:
                index[slug] = macro

    merges = _merge_map()
    for src, dest in merges.items():
        if dest not in index and src in index:
            index[dest] = index[src]
        if src not in index and dest in index:
            index[src] = index[dest]
    return index


def load_cooking_posts() -> list[dict]:
    posts: list[dict] = []
    for path in sorted(COOKING_POSTS.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            posts.extend(row for row in payload if isinstance(row, dict))
    return posts


def missing_ingredient_slugs(
    posts: list[dict] | None = None,
    index: dict[str, Macro] | None = None,
) -> list[str]:
    index = index if index is not None else load_macro_index()
    posts = posts if posts is not None else load_cooking_posts()
    missing: set[str] = set()
    for post in posts:
        for ing in post.get("ingredients") or []:
            slug = str((ing or {}).get("food_slug") or "").strip()
            if slug and slug not in index:
                missing.add(slug)
    return sorted(missing)


def recipe_batch_macros(post: dict, index: dict[str, Macro]) -> dict[str, float]:
    lines: list[dict[str, float]] = []
    missing: list[str] = []
    for ing in post.get("ingredients") or []:
        slug = str((ing or {}).get("food_slug") or "").strip()
        grams = float((ing or {}).get("grams") or 0)
        if not slug:
            continue
        macro = index.get(slug)
        if macro is None:
            missing.append(slug)
            continue
        lines.append(scale_line(index_per_100g(macro), grams))
    if missing:
        raise KeyError("missing ingredient macros: " + ", ".join(sorted(set(missing))))
    return sum_lines(lines)


def recipe_serving_macros(post: dict, index: dict[str, Macro] | None = None) -> dict[str, float]:
    index = index if index is not None else load_macro_index()
    servings = float(post.get("servings") or 0)
    yield_grams = float(post.get("yield_grams") or 0)
    if servings <= 0:
        raise ValueError(f"{post.get('slug')}: servings must be > 0")
    if yield_grams <= 0:
        raise ValueError(f"{post.get('slug')}: yield_grams must be > 0")
    batch = recipe_batch_macros(post, index)
    profile = cooked_profile(batch, servings, yield_grams)
    serving = profile["serving"]
    per100 = profile["per_100g"]
    return {
        "calories": serving["calories"],
        "protein_g": serving["protein_g"],
        "carbs_g": serving["carbs_g"],
        "fat_g": serving["fat_g"],
        "fiber_g": serving["fiber_g"],
        "serving_grams": serving["grams"],
        "kcal_100g": per100["kcal_100g"],
        "protein_100g": per100["protein_100g"],
        "carbs_100g": per100["carbs_100g"],
        "fat_100g": per100["fat_100g"],
        "fiber_100g": per100["fiber_100g"],
    }


def dump_missing_macros_from_db(slugs: list[str]) -> list[dict]:
    """Fill recipe-only slugs from the live foods table."""
    import sys

    api_root = ROOT / "api"
    if str(api_root) not in sys.path:
        sys.path.insert(0, str(api_root))
    from sqlalchemy import text

    from app.core.database import engine

    rows: list[dict] = []
    with engine.connect() as conn:
        for slug in slugs:
            row = conn.execute(
                text(
                    "SELECT slug, kcal_100g, protein_100g, carbs_100g, fat_100g, fiber_100g, "
                    "calories, protein_g, carbs_g, fat_g, fiber_g, serving_grams "
                    "FROM foods WHERE slug = :slug"
                ),
                {"slug": slug},
            ).mappings().first()
            if not row:
                continue
            payload = dict(row)
            macro = _as_macro(payload)
            if macro is None:
                continue
            rows.append({"slug": slug, **macro})
    return rows


def sync_dishes(index: dict[str, Macro] | None = None) -> list[dict]:
    index = index if index is not None else load_macro_index()
    posts = load_cooking_posts()
    missing = missing_ingredient_slugs(posts, index)
    if missing:
        dumped = dump_missing_macros_from_db(missing)
        dump_path = SEEDS / "foods_recipe_macros.json"
        existing = []
        if dump_path.is_file():
            raw = json.loads(dump_path.read_text(encoding="utf-8"))
            existing = _food_rows(raw)
        by_slug = {str(row.get("slug")): row for row in existing}
        for row in dumped:
            by_slug[row["slug"]] = row
        dump_path.write_text(
            json.dumps(list(by_slug.values()), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        index = load_macro_index()
        missing = missing_ingredient_slugs(posts, index)
    if missing:
        raise SystemExit("missing ingredient macros: " + ", ".join(missing))

    by_slug = {str(post.get("slug")): post for post in posts}
    dishes = json.loads(DISHES_PATH.read_text(encoding="utf-8"))
    if not isinstance(dishes, list):
        raise SystemExit("foods_traditional_dishes.json must be a list")
    updated: list[dict] = []
    for dish in dishes:
        slug = str(dish.get("slug") or "")
        post = by_slug.get(slug)
        if post is None:
            raise SystemExit(f"no cooking post for dish {slug}")
        macros = recipe_serving_macros(post, index)
        dish["calories"] = float(macros["calories"])
        dish["protein_g"] = float(macros["protein_g"])
        dish["carbs_g"] = float(macros["carbs_g"])
        dish["fat_g"] = float(macros["fat_g"])
        dish["fiber_g"] = float(macros["fiber_g"])
        dish["serving_grams"] = float(macros["serving_grams"])
        dish["kcal_100g"] = float(macros["kcal_100g"])
        dish["protein_100g"] = float(macros["protein_100g"])
        dish["carbs_100g"] = float(macros["carbs_100g"])
        dish["fat_100g"] = float(macros["fat_100g"])
        dish["fiber_100g"] = float(macros["fiber_100g"])
        dish["prep_state"] = "cooked"
        dish["source_ref"] = "recipe-bom"
        updated.append(dish)
    DISHES_PATH.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return updated


def main() -> None:
    dishes = sync_dishes()
    print(f"updated {len(dishes)} dishes in {DISHES_PATH.name}")


if __name__ == "__main__":
    main()
