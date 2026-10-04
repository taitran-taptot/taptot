"""Rename knowledge_articles.slug from garbled IDs to title-based slugs."""

from __future__ import annotations

import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.entities import KnowledgeArticle
from app.services.knowledge_slug_aliases import KNOWLEDGE_SLUG_ALIASES


def run() -> None:
    db = SessionLocal()
    try:
        updated = 0
        for old, new in KNOWLEDGE_SLUG_ALIASES.items():
            if old == new:
                continue
            row = db.scalar(select(KnowledgeArticle).where(KnowledgeArticle.slug == old))
            if row is None:
                continue
            clash = db.scalar(select(KnowledgeArticle).where(KnowledgeArticle.slug == new))
            if clash is not None and clash.id != row.id:
                print(f"skip {old}: target {new} already exists id={clash.id}")
                continue
            print(f"{old} -> {new}")
            row.slug = new
            updated += 1
        db.commit()
        print(f"updated {updated} rows")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
