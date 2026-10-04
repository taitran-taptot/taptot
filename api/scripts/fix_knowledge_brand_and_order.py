"""Replace TFIT→TAPTOT, re-order Cơ bản/Trung cấp, export markdown files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.entities import KnowledgeArticle

ROOT = API_DIR / "app" / "data" / "knowledge"

HELPER_ORDER = {
    "cach-doc-lich-tap-quy-uoc-buoi-tap": 10,
    "dau-moi-co-doms-va-chan-thuong-cach-phan-biet-va-xu-ly": 11,
    "tuan-xa-tai-nhe-deload-cho-nguoi-moi": 12,
}

BRAND_RE = re.compile(r"\b(?:TFIT|Tfit|TFit|tfit)\b")
NUM_RE = re.compile(r"^(\d+)\.(\d+)\s*")


def brand_fix(text: str | None) -> str | None:
    if text is None:
        return None
    return BRAND_RE.sub("TAPTOT", text)


def sort_for(row: KnowledgeArticle) -> int | None:
    if row.slug in HELPER_ORDER:
        return HELPER_ORDER[row.slug]
    m = NUM_RE.match((row.title_vi or "").strip())
    if not m:
        return None
    major, minor = int(m.group(1)), int(m.group(2))
    if major == 1:
        return minor
    if major == 2:
        return 20 + minor
    return None


def run() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    try:
        rows = list(db.scalars(select(KnowledgeArticle)).all())
        replaced = 0
        for row in rows:
            if row.level not in ("beginner", "basic", "intermediate", "advanced"):
                continue
            before = "\0".join(
                filter(None, [row.content_md, row.seo_description, row.seo_title])
            )
            hits = len(BRAND_RE.findall(before))
            replaced += hits
            row.content_md = brand_fix(row.content_md) or ""
            row.seo_description = brand_fix(row.seo_description)
            row.seo_title = brand_fix(row.seo_title)

            if row.level in ("beginner", "basic", "intermediate"):
                new_order = sort_for(row)
                if new_order is not None:
                    row.sort_order = new_order

            path = ROOT / f"{row.slug}.md"
            path.write_text((row.content_md or "").rstrip() + "\n", encoding="utf-8")
            print(f"export {row.slug} sort={row.sort_order} replaced={hits}")

        db.commit()

        left = 0
        for row in db.scalars(select(KnowledgeArticle)).all():
            blob = " ".join(
                filter(None, [row.content_md, row.seo_description, row.seo_title, row.title_vi])
            )
            left += len(BRAND_RE.findall(blob))
        print(f"total_replaced={replaced}; remaining_brand_hits={left}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
