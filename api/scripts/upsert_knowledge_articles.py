"""Upsert beginner knowledge articles from markdown files."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.entities import KnowledgeArticle

ROOT = API_DIR / "app" / "data" / "knowledge"

ARTICLES = (
    {
        "slug": "cach-doc-lich-tap",
        "title_vi": "Cách đọc lịch tập",
        "level": "beginner",
        "sort_order": 7,
        "read_time_min": 4,
        "seo_description": "Sets, reps, nghỉ và ngày nghỉ trên lịch TAPTOT — đọc trước khi tập.",
        "file": "cach-doc-lich-tap.md",
    },
    {
        "slug": "dau-nhuc-va-chan-thuong",
        "title_vi": "Đau nhức và chấn thương",
        "level": "beginner",
        "sort_order": 8,
        "read_time_min": 5,
        "seo_description": "Phân biệt mỏi cơ sau tập với đau cần dừng — hướng dẫn cho người mới.",
        "file": "dau-nhuc-va-chan-thuong.md",
    },
    {
        "slug": "tuan-nhe-cho-nguoi-moi",
        "title_vi": "Tuần nhẹ cho người mới",
        "level": "beginner",
        "sort_order": 9,
        "read_time_min": 4,
        "seo_description": "Tuần 4, 8 và 14 trên thử thách 100 ngày là giảm tải có chủ đích, không phải nghỉ hết.",
        "file": "tuan-nhe-cho-nguoi-moi.md",
    },
)


def upsert() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    db = SessionLocal()
    try:
        for spec in ARTICLES:
            path = ROOT / spec["file"]
            content = path.read_text(encoding="utf-8").strip() + "\n"
            row = db.scalar(select(KnowledgeArticle).where(KnowledgeArticle.slug == spec["slug"]))
            if row is None:
                row = KnowledgeArticle(slug=spec["slug"], is_published=True, published_at=now)
                db.add(row)
            row.title_vi = spec["title_vi"]
            row.content_md = content
            row.level = spec["level"]
            row.sort_order = spec["sort_order"]
            row.read_time_min = spec["read_time_min"]
            row.seo_description = spec["seo_description"]
            row.is_published = True
            if row.published_at is None:
                row.published_at = now
            print(f"upsert {spec['slug']}")
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    upsert()
