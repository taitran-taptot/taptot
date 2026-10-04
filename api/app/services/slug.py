from __future__ import annotations

import re
import unicodedata

from sqlalchemy.orm import Session

_CHAPTER_PREFIX_RE = re.compile(r"^\d+\.\d+\s*[—–\-]\s*")


def slugify(text: str, *, fallback: str = "muc") -> str:
    normalized = unicodedata.normalize("NFD", (text or "").strip())
    without_marks = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    without_marks = without_marks.replace("đ", "d").replace("Đ", "d")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", without_marks.lower()).strip("-")
    return (slug[:140] or fallback)


def knowledge_slug_from_title(title: str, *, fallback: str = "bai-viet") -> str:
    """Public knowledge URL slug from article title (drop 1.0 — numbering)."""
    body = _CHAPTER_PREFIX_RE.sub("", (title or "").strip())
    return slugify(body, fallback=fallback)


def unique_slug(
    db: Session,
    model,
    base: str,
    *,
    exclude_id: int | None = None,
    fallback: str = "muc",
) -> str:
    root = slugify(base, fallback=fallback)
    slug = root
    n = 2
    while True:
        query = db.query(model).filter(model.slug == slug)
        if exclude_id is not None:
            query = query.filter(model.id != exclude_id)
        if query.first() is None:
            return slug
        slug = f"{root}-{n}"[:150]
        n += 1
