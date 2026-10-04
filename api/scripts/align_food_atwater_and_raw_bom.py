"""One-shot: raw BOM slugs, pantry produce, Atwater seed alignment."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "api"
sys.path.insert(0, str(API))

from app.services.food_energy import apply_energy_alignment_dict  # noqa: E402

SEEDS = ROOT / "seeds"
COOKING = SEEDS / "cooking_posts"

RAU_MUONG = {
    "slug": "rau-muong",
    "name_vi": "Rau muống",
    "name_en": "Water spinach, raw",
    "category_slug": "rau-cu-qua",
    "food_kind": "ingredient",
    "prep_state": "raw",
    "kcal_100g": 19,
    "protein_100g": 2.6,
    "carbs_100g": 2.9,
    "fat_100g": 0.2,
    "fiber_100g": 2.1,
    "sodium_100mg": None,
    "source_ref": "usda-vn-table",
    "confidence": "reference",
    "is_common": True,
    "tags": ["rau", "produce", "giam-can"],
    "aliases": ["rau muống tươi"],
    "image_url": "foods/rau-muong-luoc.jpg",
    "portions": [
        {"label_vi": "100g", "grams": 100.0, "is_default": True, "sort_order": 0},
        {"label_vi": "1 bó (~400g)", "grams": 400, "is_default": False, "sort_order": 1},
    ],
    "serving_size": "100g",
    "serving_grams": 100,
    "macro_roles": ["produce"],
    "meal_slots": ["lunch", "dinner"],
    "ai_priority": 8,
    "default_for_ai": True,
}

BAP_NGOT = {
    "slug": "bap-ngot",
    "name_vi": "Bắp ngọt",
    "name_en": "Sweet corn, raw kernels",
    "category_slug": "rau-cu-qua",
    "food_kind": "ingredient",
    "prep_state": "raw",
    "kcal_100g": 86,
    "protein_100g": 3.3,
    "carbs_100g": 19.0,
    "fat_100g": 1.4,
    "fiber_100g": 2.7,
    "sodium_100mg": None,
    "source_ref": "usda-vn-table",
    "confidence": "reference",
    "is_common": True,
    "tags": ["produce", "carb"],
    "aliases": ["hạt bắp tươi"],
    "image_url": "foods/bap-ngot-luoc.jpg",
    "portions": [
        {"label_vi": "100g", "grams": 100.0, "is_default": True, "sort_order": 0},
        {"label_vi": "1 trái (~150g hạt)", "grams": 150, "is_default": False, "sort_order": 1},
    ],
    "serving_size": "100g",
    "serving_grams": 100,
    "macro_roles": ["produce", "carb"],
    "meal_slots": ["lunch", "dinner", "snack"],
    "ai_priority": 6,
    "default_for_ai": False,
}

CHA_REPL = [
    {
        "food_slug": "trung-ga-ca-qua-song",
        "grams": 100,
        "amount_label": "2 quả trứng (~100g)",
        "note": "đánh với thịt xay, hấp thành chả",
    },
    {
        "food_slug": "thit-lon-xay-song",
        "grams": 40,
        "amount_label": "40g thịt heo xay",
        "note": "nhân chả trứng",
    },
]


def _dump(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _food_rows(payload) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("foods"), list):
        return payload["foods"]
    return []


def upsert_pantry() -> None:
    path = SEEDS / "foods_cooking_pantry.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    foods = payload["foods"]
    by_slug = {str(f.get("slug")): i for i, f in enumerate(foods)}
    for item in (RAU_MUONG, BAP_NGOT):
        apply_energy_alignment_dict(item)
        if item["slug"] in by_slug:
            foods[by_slug[item["slug"]]] = item
        else:
            foods.append(item)
    _dump(path, payload)


def rewrite_cooking_posts() -> None:
    for path in sorted(COOKING.glob("*.json")):
        posts = json.loads(path.read_text(encoding="utf-8"))
        file_changed = False
        for post in posts:
            ings = post.get("ingredients") or []
            new_ings: list[dict] = []
            post_changed = False
            for ing in ings:
                slug = str(ing.get("food_slug") or "")
                if slug == "cha-trung":
                    new_ings.extend(deepcopy(CHA_REPL))
                    post_changed = True
                    continue
                if slug == "com-trang":
                    grams = float(ing.get("grams") or 0)
                    raw = round(grams / 2.5)
                    new_ings.append(
                        {
                            **{k: v for k, v in ing.items() if k not in {"food_slug", "grams", "amount_label"}},
                            "food_slug": "gao-te",
                            "grams": raw,
                            "amount_label": f"{raw}g gạo tẻ (nấu thành ~{int(grams)}g cơm)",
                        }
                    )
                    post_changed = True
                    continue
                if slug == "rau-muong-luoc":
                    ing = {**ing, "food_slug": "rau-muong"}
                    label = str(ing.get("amount_label") or "")
                    if "tươi" not in label:
                        ing["amount_label"] = (label + " tươi").strip() if label else "rau muống tươi"
                    post_changed = True
                elif slug == "bap-ngot-luoc":
                    ing = {**ing, "food_slug": "bap-ngot", "amount_label": "350g hạt bắp tươi"}
                    post_changed = True
                new_ings.append(ing)
            if post_changed:
                post["ingredients"] = new_ings
                file_changed = True
        if file_changed:
            _dump(path, posts)


def align_seed_files() -> int:
    n = 0
    paths = (
        SEEDS / "foods_catalog_v2.json",
        SEEDS / "foods_cooking_pantry.json",
        SEEDS / "grain_nut_foods.json",
        SEEDS / "foods_recipe_macros.json",
    )
    for path in paths:
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = _food_rows(payload)
        file_changed = False
        for row in rows:
            if apply_energy_alignment_dict(row):
                file_changed = True
                n += 1
        if file_changed:
            _dump(path, payload)
    return n


def main() -> None:
    upsert_pantry()
    rewrite_cooking_posts()
    changed = align_seed_files()
    print(f"energy-aligned rows={changed}")


if __name__ == "__main__":
    main()
