#!/usr/bin/env python3
"""Publish audited grain/nut photos from Downloads/gemini-folder-1 and upsert catalog rows."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "api"))

from publish_food_catalog_images import (  # noqa: E402
    MEDIA_FOODS,
    load_catalog,
    load_map,
    write_merged_map,
)

SOURCE = Path(r"C:\Users\Tran Tai\Downloads\gemini-folder-1")
FILE_RE = re.compile(r"^(\d{3})_(\d+)-", re.IGNORECASE)
STT_TO_SLUG = {
    1: "gao-te",
    2: "gao-lut",
    3: "gao-nep",
    4: "yen-mach",
    5: "hat-dieu",
    6: "hat-huong-duong",
}


def collect_sources() -> dict[str, Path]:
    found: dict[str, Path] = {}
    if not SOURCE.is_dir():
        raise SystemExit(f"missing {SOURCE}")
    for path in SOURCE.iterdir():
        if not path.is_file():
            continue
        match = FILE_RE.match(path.name)
        if not match:
            continue
        stt = int(match.group(2))
        slug = STT_TO_SLUG.get(stt)
        if not slug:
            continue
        found[slug] = path
    missing = [slug for slug in STT_TO_SLUG.values() if slug not in found]
    if missing:
        raise SystemExit(f"missing photos for {missing}")
    return found


def convert_to_jpeg(src: Path, dest: Path) -> None:
    from PIL import Image, ImageOps

    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im) or im
        im.convert("RGB").save(dest, "JPEG", quality=90, optimize=True)


def main() -> None:
    sources = collect_sources()
    mapping = load_map()
    for slug, src in sources.items():
        rel = f"foods/{slug}.jpg"
        dest = MEDIA_FOODS / f"{slug}.jpg"
        convert_to_jpeg(src, dest)
        mapping[slug] = rel
        print(f"ok {slug} <- {src.name}")
    write_merged_map(load_catalog(), mapping)

    sys.path.insert(0, str(ROOT / "api"))
    from app.core.database import engine
    from app.core.migrations import ensure_grain_nut_foods

    ensure_grain_nut_foods(engine)
    print("upserted grain/nut foods")


if __name__ == "__main__":
    main()
