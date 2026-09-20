#!/usr/bin/env python3
"""Copy verified rau-cu-qua Gemini photos into /media/foods and set foods.image_url.

Usage:
    python scripts/publish_rau_cu_food_images.py              # copy + map + UPDATE DB
    python scripts/publish_rau_cu_food_images.py --dry-run
    python scripts/publish_rau_cu_food_images.py --no-db
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEEDS = ROOT / "seeds"
CATALOG = SEEDS / "foods_catalog_v2.json"
MAP_PATH = SEEDS / "food_images.json"
MEDIA_FOODS = ROOT / "uploads" / "media" / "foods"
DEFAULT_SOURCE = Path(r"C:\Users\Tran Tai\Downloads\1-101")
FILE_RE = re.compile(r"^(\d{3})_.*\.(jfif|jpe?g|png|webp)$", re.IGNORECASE)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def load_rau_cu_qua() -> list[dict]:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    return [item for item in data if item.get("category_slug") == "rau-cu-qua"]


def collect_sources(source_dir: Path, rau: list[dict]) -> list[tuple[Path, str, str]]:
    rows: list[tuple[Path, str, str]] = []
    for path in sorted(source_dir.iterdir()):
        if not path.is_file():
            continue
        match = FILE_RE.match(path.name)
        if not match:
            continue
        stt = int(match.group(1))
        if stt < 1 or stt > len(rau):
            raise SystemExit(f"STT {stt:03d} out of range for rau-cu-qua ({len(rau)} items): {path.name}")
        slug = str(rau[stt - 1]["slug"])
        rows.append((path, slug, f"foods/{slug}.jpg"))
    return rows


def write_map(rows: list[tuple[Path, str, str]]) -> None:
    mapping = {slug: rel for _src, slug, rel in rows}
    MAP_PATH.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def copy_files(rows: list[tuple[Path, str, str]]) -> int:
    MEDIA_FOODS.mkdir(parents=True, exist_ok=True)
    n = 0
    for src, slug, _rel in rows:
        dest = MEDIA_FOODS / f"{slug}.jpg"
        shutil.copyfile(src, dest)
        n += 1
    return n


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


def _update_db_with_url(url: str, rows: list[tuple[Path, str, str]]) -> int:
    from sqlalchemy import create_engine, text

    engine = create_engine(url)
    n = 0
    with engine.begin() as conn:
        for _src, slug, rel in rows:
            result = conn.execute(
                text("UPDATE foods SET image_url = :url WHERE slug = :slug"),
                {"url": rel, "slug": slug},
            )
            n += int(result.rowcount or 0)
    return n


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-db", action="store_true")
    args = parser.parse_args()
    if not args.source.is_dir():
        raise SystemExit(f"Source folder not found: {args.source}")

    rau = load_rau_cu_qua()
    rows = collect_sources(args.source, rau)
    if not rows:
        raise SystemExit(f"No numbered image files in {args.source}")

    print(f"mapped {len(rows)} files from {args.source}")
    for src, slug, rel in rows:
        print(f"  {src.name[:7]}… → {rel}")

    if args.dry_run:
        print("dry-run: no copy / map / DB write")
        return

    write_map(rows)
    copied = copy_files(rows)
    print(f"wrote {MAP_PATH.relative_to(ROOT)} ({len(rows)} slugs)")
    print(f"copied {copied} files to {MEDIA_FOODS}")

    if args.no_db:
        print("skipped DB update (--no-db)")
        return
    updated = _update_db_with_url(_load_database_url(), rows)
    print(f"updated {updated} foods.image_url rows")


if __name__ == "__main__":
    main()
