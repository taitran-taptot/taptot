"""Scale inflated traditional-dish servings in seeds/foods_traditional_dishes.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
ROOT = API_DIR.parent
sys.path.insert(0, str(API_DIR))

from app.services.food_catalog_audit_cleanup import (  # noqa: E402
    NUTRIENT_100G_PATCHES,
    correct_inflated_dish_serving,
    scale_serving_from_100g,
)


def main() -> None:
    path = ROOT / "seeds" / "foods_traditional_dishes.json"
    dishes = json.loads(path.read_text(encoding="utf-8"))
    changed = 0
    for dish in dishes:
        if not isinstance(dish, dict):
            continue
        slug = str(dish.get("slug") or "")
        dish["prep_state"] = "cooked"
        if slug in NUTRIENT_100G_PATCHES:
            patch = NUTRIENT_100G_PATCHES[slug]
            serving_grams = float(patch.get("serving_grams") or dish.get("serving_grams") or 100)
            serving = scale_serving_from_100g(
                kcal_100g=float(patch["kcal_100g"]),
                protein_100g=float(patch["protein_100g"]),
                carbs_100g=float(patch["carbs_100g"]),
                fat_100g=float(patch["fat_100g"]),
                fiber_100g=None if patch.get("fiber_100g") is None else float(patch["fiber_100g"]),
                serving_grams=serving_grams,
            )
            dish["serving_grams"] = serving_grams
            dish["serving_size"] = patch.get("serving_size") or dish.get("serving_size")
            dish["calories"] = serving["calories"]
            dish["protein_g"] = serving["protein_g"]
            dish["carbs_g"] = serving["carbs_g"]
            dish["fat_g"] = serving["fat_g"]
            if serving["fiber_g"] is not None:
                dish["fiber_g"] = serving["fiber_g"]
            changed += 1
            continue

        fixed = correct_inflated_dish_serving(
            calories=float(dish.get("calories") or 0),
            protein_g=float(dish.get("protein_g") or 0),
            carbs_g=float(dish.get("carbs_g") or 0),
            fat_g=float(dish.get("fat_g") or 0),
            fiber_g=dish.get("fiber_g"),
            serving_grams=float(dish.get("serving_grams") or 400),
        )
        if fixed is None:
            continue
        dish["calories"] = fixed["calories"]
        dish["protein_g"] = fixed["protein_g"]
        dish["carbs_g"] = fixed["carbs_g"]
        dish["fat_g"] = fixed["fat_g"]
        if fixed["fiber_g"] is not None:
            dish["fiber_g"] = fixed["fiber_g"]
        changed += 1

    path.write_text(json.dumps(dishes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"updated {changed}/{len(dishes)} dishes → {path}")


if __name__ == "__main__":
    main()
