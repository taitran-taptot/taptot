"""Raw ingredient seeds: no fiber keys; classic Atwater ±5%."""

from __future__ import annotations

import json
from pathlib import Path

from app.services.food_energy import SKIP_ENERGY_SLUGS, classic_atwater_kcal, relative_error

ROOT = Path(__file__).resolve().parents[2]
FILES = (
    ROOT / "seeds" / "foods_catalog_v2.json",
    ROOT / "seeds" / "grain_nut_foods.json",
    ROOT / "seeds" / "foods_cooking_pantry.json",
)


def _foods(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    return list(payload.get("foods") or [])


def test_raw_seeds_have_no_fiber_keys() -> None:
    for path in FILES:
        for row in _foods(path):
            assert "fiber_g" not in row, path.name
            assert "fiber_100g" not in row, f"{path.name}:{row.get('slug')}"


def test_raw_seeds_classic_atwater_within_5pct() -> None:
    for path in FILES:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload if isinstance(payload, list) else payload.get("foods") or []
        for row in rows:
            if str(row.get("food_kind") or "ingredient") == "dish":
                continue
            if str(row.get("prep_state") or "raw") != "raw":
                continue
            slug = str(row.get("slug") or "")
            if slug in SKIP_ENERGY_SLUGS:
                continue
            protein = float(row.get("protein_100g") or 0)
            carbs = float(row.get("carbs_100g") or 0)
            fat = float(row.get("fat_100g") or 0)
            kcal = float(row.get("kcal_100g") or 0)
            expected = classic_atwater_kcal(protein, carbs, fat)
            assert relative_error(kcal, expected) <= 0.05, slug
