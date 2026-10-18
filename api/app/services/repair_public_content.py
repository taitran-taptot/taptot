"""Fix knowledge markdown + cooking covers using files on disk (VPS-safe)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.models.entities import CookingPost, KnowledgeArticle
from app.services.complete_exercise_library_seed import seed_complete_exercise_library
from app.services.exercise_copy_seed import seed_exercise_copy
from app.services.exercise_name_vi import preferred_name_vi
from app.services.muscle_group_hierarchy_seed import (
    remap_exercises_to_leaf_regions,
    seed_muscle_group_hierarchy,
)


def repair_knowledge(db: Session) -> int:
    md_dir = Path(__file__).resolve().parents[1] / "data" / "knowledge"
    if not md_dir.is_dir():
        return 0
    now = datetime.now(UTC).replace(tzinfo=None)
    n = 0
    for path in sorted(md_dir.glob("*.md")):
        slug = path.stem
        content = path.read_text(encoding="utf-8").strip() + "\n"
        title = slug
        for line in content.splitlines():
            if line.startswith("# "):
                title = line[2:].strip() or slug
                break
        row = db.query(KnowledgeArticle).filter(KnowledgeArticle.slug == slug).first()
        if row is None:
            db.add(
                KnowledgeArticle(
                    slug=slug,
                    title_vi=title,
                    content_md=content,
                    level="beginner",
                    is_published=True,
                    published_at=now,
                )
            )
        else:
            row.content_md = content
            row.title_vi = title
            row.is_published = True
        n += 1
    return n


def repair_cooking_covers(db: Session) -> int:
    media = Path(get_settings().upload_dir) / "media"
    n = 0
    for row in db.query(CookingPost).all():
        candidates: list[str] = []
        for raw in (row.cover_image_url, f"foods/{row.dish_slug}.jpg" if row.dish_slug else None, f"foods/{row.slug}.jpg"):
            if not raw:
                continue
            rel = str(raw).strip().replace("\\", "/").lstrip("/")
            if rel.startswith("media/"):
                rel = rel[len("media/") :]
            if rel and rel not in candidates:
                candidates.append(rel)
        chosen = None
        for rel in candidates:
            if (media / rel.split("?", 1)[0]).is_file():
                chosen = rel
                break
        if chosen and row.cover_image_url != chosen:
            row.cover_image_url = chosen
            n += 1
        elif chosen and not row.cover_image_url:
            row.cover_image_url = chosen
            n += 1
        elif chosen:
            n += 1
    return n


def _apply_vietnamese_titles(conn) -> int:
    from sqlalchemy import text

    rows = conn.execute(text("SELECT id, name_en, name_vi FROM exercises")).mappings().all()
    n = 0
    for row in rows:
        next_vi = preferred_name_vi(
            name_en=str(row["name_en"] or ""),
            name_vi=str(row["name_vi"] or ""),
            copy_vi=None,
        )
        if next_vi and next_vi != row["name_vi"]:
            conn.execute(
                text("UPDATE exercises SET name_vi = :vi WHERE id = :id"),
                {"vi": next_vi, "id": int(row["id"])},
            )
            n += 1
    return n


def main() -> None:
    db = SessionLocal()
    try:
        k = repair_knowledge(db)
        c = repair_cooking_covers(db)
        db.commit()
        with engine.begin() as conn:
            seed_muscle_group_hierarchy(conn, is_sqlite=False)
        e = seed_complete_exercise_library(db)
        db.commit()
        with engine.begin() as conn:
            seed_muscle_group_hierarchy(conn, is_sqlite=False)
            remap_exercises_to_leaf_regions(conn, is_sqlite=False)
            vi = seed_exercise_copy(conn, is_sqlite=False)
            named = _apply_vietnamese_titles(conn)
        print(
            f"knowledge={k} cooking_covers={c} exercises={e} vi_copy={vi} "
            f"vi_names={named} muscles=relabeled"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
