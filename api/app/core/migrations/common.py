from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parents[4]

def _auth_tables_exist(conn) -> bool:
    row = conn.execute(
        text(
            "SELECT EXISTS ("
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'password_reset_tokens'"
            ")"
        )
    ).scalar()
    return bool(row)


def _has_column(conn, table: str, column: str, *, sqlite: bool) -> bool:
    if sqlite:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        return any(row[1] == column for row in rows)
    row = conn.execute(
        text(
            "SELECT EXISTS ("
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :t AND column_name = :c"
            ")"
        ),
        {"t": table, "c": column},
    ).scalar()
    return bool(row)


def _table_exists(conn, table: str, *, sqlite: bool) -> bool:
    if sqlite:
        row = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
            {"t": table},
        ).fetchone()
        return bool(row)
    row = conn.execute(
        text(
            "SELECT EXISTS ("
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :t"
            ")"
        ),
        {"t": table},
    ).scalar()
    return bool(row)


def _apply_schema_file(conn, schema_file: Path) -> None:
    sql = schema_file.read_text(encoding="utf-8")
    for statement in sql.split(";"):
        lines = [
            line.strip()
            for line in statement.splitlines()
            if line.strip() and not line.strip().startswith("--")
        ]
        if not lines:
            continue
        conn.execute(text("\n".join(lines)))


def _load_cooking_post_seeds() -> list[dict]:
    import json

    items: list[dict] = []
    legacy = PROJECT_ROOT / "seeds" / "cooking_posts.json"
    if legacy.is_file():
        data = json.loads(legacy.read_text(encoding="utf-8"))
        if isinstance(data, list):
            items.extend(data)
    folder = PROJECT_ROOT / "seeds" / "cooking_posts"
    if folder.is_dir():
        for path in sorted(folder.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                items.extend(data)
    return items


def _normalize_seed_ingredients(raw) -> list[dict]:
    out: list[dict] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        food_slug = str(item.get("food_slug") or "").strip()
        if not food_slug:
            continue
        grams = item.get("grams")
        try:
            grams_f = float(grams) if grams is not None else None
        except (TypeError, ValueError):
            grams_f = None
        out.append(
            {
                "food_slug": food_slug,
                "grams": grams_f,
                "amount_label": (str(item.get("amount_label") or "").strip() or None),
                "note": (str(item.get("note") or "").strip() or None),
            }
        )
    return out


def _seed_cooking_posts(engine: Engine) -> None:
    """Upsert cooking posts from seeds/cooking_posts.json and seeds/cooking_posts/*.json."""
    from datetime import UTC, datetime

    from sqlalchemy.orm import Session

    from app.models.entities import CookingPost

    posts = _load_cooking_post_seeds()
    if not posts:
        return

    media_root = PROJECT_ROOT / "uploads" / "media"
    now = datetime.now(UTC)
    with Session(engine) as db:
        for item in posts:
            slug = str(item.get("slug") or "").strip()
            if not slug:
                continue
            title = str(item.get("title_vi") or "").strip()
            body = str(item.get("content_md") or "").strip()
            if not title or not body:
                continue
            dish_slug = str(item.get("dish_slug") or slug).strip() or None
            cover = (item.get("cover_image_url") or "").strip().replace("\\", "/").lstrip("/") or None
            if not cover and dish_slug:
                cover = f"foods/{dish_slug}.jpg"
            if cover and not (media_root / cover).is_file():
                cover = None
            published = bool(item.get("is_published", True))
            servings = max(int(item.get("servings") or 1), 1)
            yield_raw = item.get("yield_grams")
            try:
                yield_grams = float(yield_raw) if yield_raw is not None else None
            except (TypeError, ValueError):
                yield_grams = None
            ingredients = _normalize_seed_ingredients(item.get("ingredients"))
            sort_order = int(item.get("sort_order") or 0)
            excerpt = (item.get("excerpt") or "").strip() or None

            row = db.query(CookingPost).filter(CookingPost.slug == slug).first()
            if row is None:
                db.add(
                    CookingPost(
                        slug=slug,
                        title_vi=title,
                        excerpt=excerpt,
                        content_md=body,
                        cover_image_url=cover,
                        is_published=published,
                        published_at=now if published else None,
                        sort_order=sort_order,
                        dish_slug=dish_slug,
                        servings=servings,
                        yield_grams=yield_grams,
                        ingredients=ingredients,
                        created_at=now,
                        updated_at=now,
                    )
                )
                continue
            row.title_vi = title
            row.excerpt = excerpt
            row.content_md = body
            row.cover_image_url = cover
            row.sort_order = sort_order
            row.dish_slug = dish_slug
            row.servings = servings
            row.yield_grams = yield_grams
            row.ingredients = ingredients
            if published and not row.is_published:
                row.published_at = now
            if not published:
                row.is_published = False
            else:
                row.is_published = True
                if row.published_at is None:
                    row.published_at = now
            row.updated_at = now
        db.commit()


def _foods_table_exists(conn, *, sqlite: bool) -> bool:
    if sqlite:
        row = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='foods'")
        ).fetchone()
        return bool(row)
    row = conn.execute(
        text(
            "SELECT EXISTS ("
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'foods'"
            ")"
        )
    ).scalar()
    return bool(row)

