#!/usr/bin/env python3
"""Publish audited-correct traditional dish photos from Downloads/gemini-folder-1.

Filename STT is the second number (``001_3-…`` → ORDER[2]).
When a STT has multiple files, the newest mtime wins.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_traditional_dish_prompts import ORDER
from publish_food_catalog_images import (
    MEDIA_FOODS,
    load_catalog,
    load_map,
    save_as_jpeg,
    update_db,
    write_merged_map,
)

SOURCE = Path(r"C:\Users\Tran Tai\Downloads\gemini-folder-1")
DISH_SEED = ROOT / "seeds" / "foods_traditional_dishes.json"
FILE_RE = re.compile(r"^(\d{3})_(\d+)-.*\.(jfif|jpe?g|png|webp)$", re.IGNORECASE)

# All 95 dishes: 88 previously correct + 7 regenerated (STT 3, 6, 10, 45, 52, 76, 86).
DUNG_STTS = frozenset(range(1, len(ORDER) + 1))


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def collect_newest(stts: frozenset[int]) -> dict[int, Path]:
    picked: dict[int, Path] = {}
    for path in SOURCE.iterdir():
        if not path.is_file():
            continue
        match = FILE_RE.match(path.name)
        if not match:
            continue
        stt = int(match.group(2))
        if stt not in stts:
            continue
        prev = picked.get(stt)
        if prev is None or path.stat().st_mtime >= prev.stat().st_mtime:
            picked[stt] = path
    missing = sorted(stts - set(picked))
    if missing:
        raise SystemExit(f"correct STTs have no file: {missing}")
    return picked


def load_dish_seed() -> list[dict]:
    data = json.loads(DISH_SEED.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit(f"invalid dish seed: {DISH_SEED}")
    return data


def main() -> None:
    if not SOURCE.is_dir():
        raise SystemExit(f"Source folder not found: {SOURCE}")
    if len(ORDER) != 95:
        raise SystemExit(f"ORDER must have 95 dishes, got {len(ORDER)}")

    dishes = load_dish_seed()
    by_slug = {str(item.get("slug") or ""): item for item in dishes}
    missing_seed = [s for s in ORDER if s not in by_slug]
    if missing_seed:
        raise SystemExit(f"ORDER slugs missing from dish seed: {missing_seed}")

    picked = collect_newest(DUNG_STTS)
    catalog = load_catalog() + dishes
    mapping = load_map()
    old_count = len(mapping)
    rows: list[tuple[int, Path, str, str]] = []
    for stt in sorted(picked):
        slug = ORDER[stt - 1]
        rel = f"foods/{slug}.jpg"
        rows.append((stt, picked[stt], slug, rel))
        mapping[slug] = rel

    print(f"publishing {len(rows)} traditional dishes from {SOURCE}")
    MEDIA_FOODS.mkdir(parents=True, exist_ok=True)
    for stt, src, slug, rel in rows:
        dest = MEDIA_FOODS / f"{slug}.jpg"
        save_as_jpeg(src, dest)
        print(f"  {stt:3d} → {rel}")

    write_merged_map(catalog, mapping)
    print(f"wrote seeds/food_images.json ({old_count} → {len(mapping)} slugs)")

    updated = update_db(mapping)
    print(f"updated {updated} foods.image_url rows")


if __name__ == "__main__":
    main()
