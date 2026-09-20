# -*- coding: utf-8 -*-
"""Export active catalog foods that still have no photo on disk."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from sqlalchemy import text

from app.core.database import engine

OUT = Path(r"C:\Users\Tran Tai\Downloads\foods-chua-co-anh.txt")
MEDIA = ROOT / "uploads" / "media"
HIDDEN_CATEGORY_SLUGS = {"an-vat-do-uong"}


def media_exists(image_url: str | None) -> bool:
    if not image_url:
        return False
    rel = image_url.split("?", 1)[0].replace("\\", "/").lstrip("/")
    if not rel:
        return False
    return (MEDIA / rel).is_file()


def main() -> None:
    sql = """
        SELECT
            f.slug,
            f.name_vi,
            f.image_url,
            f.food_kind,
            c.slug AS category_slug,
            c.name_vi AS category_name,
            c.sort_order
        FROM foods f
        LEFT JOIN food_categories c ON c.id = f.category_id
        WHERE f.status = 'active'
          AND f.owner_user_id IS NULL
        ORDER BY COALESCE(c.sort_order, 999), f.name_vi
    """
    with engine.connect() as conn:
        rows = list(conn.execute(text(sql)).mappings())

    visible = [r for r in rows if (r["category_slug"] or "") not in HIDDEN_CATEGORY_SLUGS]
    missing = [r for r in visible if not media_exists(r["image_url"])]
    have = len(visible) - len(missing)

    by_cat: dict[str, int] = {}
    for r in missing:
        cat = r["category_name"] or r["category_slug"] or "(không quầy)"
        by_cat[cat] = by_cat.get(cat, 0) + 1

    lines = [
        f"Tổng đang hiện trên kho (active, không ẩn): {len(visible)}",
        f"Đã có ảnh: {have}",
        f"Còn thiếu: {len(missing)}",
        "",
        "Thiếu theo quầy:",
        *[f"  {n}  {name}" for name, n in by_cat.items()],
        "",
        "STT | tên | slug | category",
        "----|-----|------|---------",
    ]
    for i, r in enumerate(missing, 1):
        cat = r["category_slug"] or ""
        lines.append(f"{i} | {r['name_vi']} | {r['slug']} | {cat}")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT} missing={len(missing)} have={have} total={len(visible)}")


if __name__ == "__main__":
    main()
