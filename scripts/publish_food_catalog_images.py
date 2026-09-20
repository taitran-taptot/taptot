#!/usr/bin/env python3
"""Publish verified catalog photos (STT 102–304) into /media/foods.

Filename STT is the *second* number: ``001_102-Củ-dền-….jfif`` → catalog[101].
Only the 133 audited-correct STTs are copied. Existing 65 rau-củ mappings
in seeds/food_images.json are merged, not replaced.

Usage:
    python scripts/publish_food_catalog_images.py
    python scripts/publish_food_catalog_images.py --dry-run
    python scripts/publish_food_catalog_images.py --no-db
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SEEDS = ROOT / "seeds"
CATALOG = SEEDS / "foods_catalog_v2.json"
MAP_PATH = SEEDS / "food_images.json"
MEDIA_FOODS = ROOT / "uploads" / "media" / "foods"
SOURCE_102 = Path(r"C:\Users\Tran Tai\Downloads\102-304")
SOURCE_1_101 = Path(r"C:\Users\Tran Tai\Downloads\1-101")
MISSING_OUT = Path(r"C:\Users\Tran Tai\Downloads\foods-chua-co-anh.txt")

FILE_RE_STT2 = re.compile(r"^(\d{3})_(\d{3})-.*\.(jfif|jpe?g|png|webp)$", re.IGNORECASE)
FILE_RE_STT1 = re.compile(r"^(\d{3})_.*\.(jfif|jpe?g|png|webp)$", re.IGNORECASE)

# Audited-correct STTs from Downloads/102-304 (filename = source of truth).
DUNG_STTS = frozenset(
    {
        102,
        103,
        107,
        109,
        110,
        112,
        113,
        115,
        117,
        118,
        *range(120, 125),
        *range(126, 137),
        138,
        140,
        143,
        145,
        146,
        *range(148, 157),
        *range(159, 170),
        *range(172, 175),
        *range(177, 181),
        *range(182, 187),
        190,
        191,
        193,
        *range(195, 198),
        *range(201, 204),
        205,
        207,
        208,
        210,
        212,
        214,
        215,
        *range(219, 223),
        *range(224, 227),
        *range(228, 233),
        *range(234, 238),
        239,
        240,
        *range(243, 246),
        *range(250, 253),
        254,
        *range(256, 261),
        262,
        266,
        269,
        *range(271, 274),
        *range(277, 280),
        281,
        *range(283, 286),
        288,
        290,
        *range(292, 295),
        296,
        297,
        *range(300, 303),
        304,
    }
)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def load_catalog() -> list[dict]:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise SystemExit(f"empty catalog: {CATALOG}")
    return data


def load_map() -> dict[str, str]:
    if not MAP_PATH.is_file():
        return {}
    data = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items()}


def food_name(item: dict) -> str:
    return str(item.get("name_vi") or item.get("name") or item.get("slug") or "")


def save_as_jpeg(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    suffix = src.suffix.lower()
    if suffix in {".jfif", ".jpg", ".jpeg"}:
        shutil.copyfile(src, dest)
        return
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im) or im
        if im.mode in ("RGBA", "P", "LA"):
            rgba = im.convert("RGBA")
            bg = Image.new("RGB", rgba.size, (255, 255, 255))
            bg.paste(rgba, mask=rgba.split()[-1])
            bg.save(dest, "JPEG", quality=90, optimize=True)
        else:
            im.convert("RGB").save(dest, "JPEG", quality=90, optimize=True)


def collect_102_304(source_dir: Path, catalog: list[dict]) -> list[tuple[int, Path, str, str]]:
    rows: list[tuple[int, Path, str, str]] = []
    seen: set[int] = set()
    for path in sorted(source_dir.iterdir(), key=lambda p: p.name):
        if not path.is_file():
            continue
        match = FILE_RE_STT2.match(path.name)
        if not match:
            continue
        stt = int(match.group(2))
        if stt not in DUNG_STTS:
            continue
        if stt in seen:
            raise SystemExit(f"duplicate STT {stt} in {source_dir}: {path.name}")
        if stt < 1 or stt > len(catalog):
            raise SystemExit(f"STT {stt} out of catalog range ({len(catalog)}): {path.name}")
        slug = str(catalog[stt - 1]["slug"])
        seen.add(stt)
        rows.append((stt, path, slug, f"foods/{slug}.jpg"))
    missing = sorted(DUNG_STTS - seen)
    if missing:
        raise SystemExit(f"correct STTs have no file in {source_dir}: {missing}")
    if len(rows) != len(DUNG_STTS):
        raise SystemExit(f"expected {len(DUNG_STTS)} correct files, got {len(rows)}")
    return rows


def restore_missing_1_101(catalog: list[dict], mapping: dict[str, str]) -> list[tuple[Path, str, str]]:
    """If any existing map slug has no media file, recopy from Downloads/1-101."""
    rau = [item for item in catalog if item.get("category_slug") == "rau-cu-qua"]
    slug_to_src: dict[str, Path] = {}
    if SOURCE_1_101.is_dir():
        for path in SOURCE_1_101.iterdir():
            if not path.is_file():
                continue
            match = FILE_RE_STT1.match(path.name)
            if not match:
                continue
            stt = int(match.group(1))
            if 1 <= stt <= len(rau):
                slug_to_src[str(rau[stt - 1]["slug"])] = path

    restored: list[tuple[Path, str, str]] = []
    for slug, rel in mapping.items():
        dest = MEDIA_FOODS / Path(rel.replace("\\", "/")).name
        if dest.is_file():
            continue
        src = slug_to_src.get(slug)
        if src is None:
            print(f"missing media and no 1-101 source: {slug}")
            continue
        restored.append((src, slug, rel if rel.endswith(".jpg") else f"foods/{slug}.jpg"))
    return restored


def write_merged_map(catalog: list[dict], mapping: dict[str, str]) -> None:
    ordered: dict[str, str] = {}
    for item in catalog:
        slug = str(item.get("slug") or "")
        if slug and slug in mapping:
            ordered[slug] = mapping[slug]
    for slug, rel in mapping.items():
        if slug not in ordered:
            ordered[slug] = rel
    MAP_PATH.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_database_url() -> str:
    env_path = ROOT / "api" / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    url = __import__("os").environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL not found in api/.env or environment")
    return url


def update_db(mapping: dict[str, str]) -> int:
    from sqlalchemy import create_engine, text

    engine = create_engine(_load_database_url())
    n = 0
    with engine.begin() as conn:
        for slug, rel in mapping.items():
            dest = ROOT / "uploads" / "media" / Path(*rel.replace("\\", "/").split("/"))
            if not dest.is_file():
                continue
            result = conn.execute(
                text("UPDATE foods SET image_url = :url WHERE slug = :slug"),
                {"url": rel.replace("\\", "/").lstrip("/"), "slug": slug},
            )
            n += int(result.rowcount or 0)
    return n


def write_missing_list(catalog: list[dict], mapping: dict[str, str], out_path: Path) -> int:
    media_root = ROOT / "uploads" / "media"
    have: list[tuple[int, str, str, str]] = []
    missing: list[tuple[int, str, str, str]] = []
    for i, item in enumerate(catalog):
        stt = i + 1
        slug = str(item.get("slug") or "")
        name = food_name(item)
        cat = str(item.get("category_slug") or "")
        rel = mapping.get(slug, "")
        dest = media_root / Path(*rel.replace("\\", "/").split("/")) if rel else None
        if rel and dest is not None and dest.is_file():
            have.append((stt, name, slug, cat))
        else:
            missing.append((stt, name, slug, cat))

    lines = [
        f"Tổng catalog: {len(catalog)}",
        f"Đã có ảnh: {len(have)}",
        f"Còn thiếu: {len(missing)}",
        "",
        "STT | tên | slug | category",
        "----|-----|------|---------",
    ]
    for stt, name, slug, cat in missing:
        lines.append(f"{stt} | {name} | {slug} | {cat}")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(missing)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE_102)
    parser.add_argument("--missing-out", type=Path, default=MISSING_OUT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-db", action="store_true")
    args = parser.parse_args()
    if not args.source.is_dir():
        raise SystemExit(f"Source folder not found: {args.source}")
    if len(DUNG_STTS) != 133:
        raise SystemExit(f"DUNG_STTS must have 133 items, got {len(DUNG_STTS)}")

    catalog = load_catalog()
    rows = collect_102_304(args.source, catalog)
    mapping = load_map()
    old_count = len(mapping)

    print(f"mapped {len(rows)} correct files from {args.source}")
    for stt, src, slug, rel in rows:
        print(f"  {stt:3d} {src.suffix.lower():5s} → {rel}")

    restored = restore_missing_1_101(catalog, mapping)
    if restored:
        print(f"will restore {len(restored)} missing 1–101 media files")

    if args.dry_run:
        print("dry-run: no copy / map / DB write")
        return

    MEDIA_FOODS.mkdir(parents=True, exist_ok=True)
    for _stt, src, slug, rel in rows:
        save_as_jpeg(src, MEDIA_FOODS / f"{slug}.jpg")
        mapping[slug] = rel
    for src, slug, rel in restored:
        save_as_jpeg(src, MEDIA_FOODS / f"{slug}.jpg")
        mapping[slug] = rel

    write_merged_map(catalog, mapping)
    print(f"wrote {MAP_PATH.relative_to(ROOT)} ({old_count} → {len(mapping)} slugs)")
    print(f"copied {len(rows)} files to {MEDIA_FOODS}")

    if not args.no_db:
        updated = update_db(mapping)
        print(f"updated {updated} foods.image_url rows")
    else:
        print("skipped DB update (--no-db)")

    missing_n = write_missing_list(catalog, mapping, args.missing_out)
    print(f"wrote {args.missing_out} ({missing_n} foods without photo)")


if __name__ == "__main__":
    main()
