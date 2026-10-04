"""Rewrite cooking-post amount_label as spoon/ml/g; keep BOM grams."""

from __future__ import annotations

import json
import sys
from pathlib import Path

API = Path(__file__).resolve().parents[1]
ROOT = API.parent
sys.path.insert(0, str(API))

from app.services.cooking_amount import format_amount_label  # noqa: E402

SEEDS = ROOT / "seeds"


def _food_rows(payload) -> list[dict]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("foods"), list):
        return [r for r in payload["foods"] if isinstance(r, dict)]
    return []


def load_portions() -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
    for path in (
        SEEDS / "foods_cooking_pantry.json",
        SEEDS / "grain_nut_foods.json",
        SEEDS / "foods_catalog_v2.json",
    ):
        if not path.is_file():
            continue
        for row in _food_rows(json.loads(path.read_text(encoding="utf-8"))):
            slug = str(row.get("slug") or "").strip()
            portions = row.get("portions")
            if slug and isinstance(portions, list):
                index[slug] = portions
    return index


def main() -> None:
    portions = load_portions()
    changed_posts = 0
    changed_ings = 0
    for path in sorted((SEEDS / "cooking_posts").glob("*.json")):
        posts = json.loads(path.read_text(encoding="utf-8"))
        file_changed = False
        for post in posts:
            for ing in post.get("ingredients") or []:
                if not isinstance(ing, dict):
                    continue
                grams = float(ing.get("grams") or 0)
                slug = str(ing.get("food_slug") or "")
                if grams <= 0 or not slug:
                    continue
                new_label = format_amount_label(
                    grams=grams,
                    slug=slug,
                    existing=str(ing.get("amount_label") or ""),
                    portions=portions.get(slug),
                )
                if new_label != (ing.get("amount_label") or "").strip():
                    ing["amount_label"] = new_label
                    changed_ings += 1
                    file_changed = True
        if file_changed:
            path.write_text(
                json.dumps(posts, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            changed_posts += 1
    print(f"posts_files={changed_posts} ingredients={changed_ings}")


if __name__ == "__main__":
    main()
