from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.pagination import PaginatedResponse, PaginationParams
from app.models.entities import CookingPost, Food
from app.services.slug import unique_slug

GROUP_SLUG_TO_VI = {
    "mon-com-gia-dinh": "Món Cơm Gia Đình",
    "dac-san-vung-mien": "Đặc sản vùng miền",
    "mon-nuoc-soi": "Món Nước & Sợi",
    "banh-mi-mon-cuon": "Bánh Mì & Món Cuốn",
}


def _now() -> datetime:
    return datetime.now(UTC)


def _as_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    return []


def _group_from_tags(tags: Any) -> tuple[str | None, str | None]:
    slug = None
    name = None
    for raw in _as_list(tags):
        tag = str(raw)
        if tag.startswith("nhom_vi:"):
            name = tag[len("nhom_vi:") :].strip() or None
        elif tag.startswith("nhom:"):
            slug = tag[len("nhom:") :].strip() or None
    if slug and not name:
        name = GROUP_SLUG_TO_VI.get(slug, slug)
    return slug, name


def _ingredient_rows(raw: Any, foods_by_slug: dict[str, Food] | None) -> list[dict]:
    out: list[dict] = []
    for item in _as_list(raw):
        if not isinstance(item, dict):
            continue
        food_slug = str(item.get("food_slug") or "").strip()
        grams = item.get("grams")
        try:
            grams_f = float(grams) if grams is not None else None
        except (TypeError, ValueError):
            grams_f = None
        food = foods_by_slug.get(food_slug) if foods_by_slug and food_slug else None
        out.append(
            {
                "food_slug": food_slug or None,
                "grams": grams_f,
                "amount_label": (str(item.get("amount_label") or "").strip() or None),
                "note": (str(item.get("note") or "").strip() or None),
                "name_vi": food.name_vi if food else (str(item.get("name_vi") or "").strip() or food_slug or None),
                "image_url": food.image_url if food else None,
            }
        )
    return out


def post_to_dict(
    row: CookingPost,
    *,
    dish: Food | None = None,
    foods_by_slug: dict[str, Food] | None = None,
    hydrate_ingredients: bool = False,
) -> dict:
    group_slug, group_vi = _group_from_tags(dish.tags if dish is not None else None)
    grams_each = None
    if row.yield_grams and row.servings:
        grams_each = round(float(row.yield_grams) / max(int(row.servings), 1), 1)
    payload = {
        "id": row.id,
        "slug": row.slug,
        "title_vi": row.title_vi,
        "excerpt": row.excerpt,
        "content_md": row.content_md,
        "cover_image_url": row.cover_image_url,
        "is_published": bool(row.is_published),
        "published_at": row.published_at.isoformat() if row.published_at else None,
        "author_user_id": str(row.author_user_id) if row.author_user_id else None,
        "sort_order": row.sort_order,
        "dish_slug": row.dish_slug,
        "servings": int(row.servings or 1),
        "yield_grams": float(row.yield_grams) if row.yield_grams is not None else None,
        "grams_per_serving": grams_each,
        "group_slug": group_slug,
        "group_vi": group_vi,
        "dish_name_vi": dish.name_vi if dish else None,
        "dish_serving_grams": float(dish.serving_grams) if dish and dish.serving_grams else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
    if hydrate_ingredients:
        payload["ingredients"] = _ingredient_rows(row.ingredients, foods_by_slug)
    else:
        payload["ingredients"] = _as_list(row.ingredients)
    return payload


def _foods_by_slugs(db: Session, slugs: list[str]) -> dict[str, Food]:
    clean = [s for s in dict.fromkeys(slugs) if s]
    if not clean:
        return {}
    rows = db.query(Food).filter(Food.slug.in_(clean)).all()
    return {row.slug: row for row in rows}


def _collect_slugs(rows: list[CookingPost], *, hydrate_ingredients: bool) -> list[str]:
    slugs: list[str] = []
    for row in rows:
        if row.dish_slug:
            slugs.append(row.dish_slug)
        if hydrate_ingredients:
            for item in _as_list(row.ingredients):
                if isinstance(item, dict) and item.get("food_slug"):
                    slugs.append(str(item["food_slug"]))
    return slugs


def serialize_posts(
    db: Session, rows: list[CookingPost], *, hydrate_ingredients: bool
) -> list[dict]:
    foods = _foods_by_slugs(db, _collect_slugs(rows, hydrate_ingredients=hydrate_ingredients))
    return [
        post_to_dict(
            row,
            dish=foods.get(row.dish_slug) if row.dish_slug else None,
            foods_by_slug=foods,
            hydrate_ingredients=hydrate_ingredients,
        )
        for row in rows
    ]


def _normalize_ingredients(raw: Any) -> list[dict]:
    out: list[dict] = []
    for item in _as_list(raw):
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


class CookingPostService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_public(self, pagination: PaginationParams) -> PaginatedResponse[dict]:
        query = self.db.query(CookingPost).filter(CookingPost.is_published.is_(True))
        total = query.count()
        rows = (
            query.order_by(
                CookingPost.sort_order.asc(),
                CookingPost.published_at.desc(),
                CookingPost.id.desc(),
            )
            .offset(pagination.offset)
            .limit(pagination.page_size)
            .all()
        )
        return PaginatedResponse.create(
            serialize_posts(self.db, rows, hydrate_ingredients=False),
            total,
            pagination.page,
            pagination.page_size,
        )

    def get_public_by_slug(self, slug: str) -> dict:
        row = (
            self.db.query(CookingPost)
            .filter(CookingPost.slug == slug, CookingPost.is_published.is_(True))
            .first()
        )
        if not row:
            raise NotFoundError("CookingPost", slug)
        return serialize_posts(self.db, [row], hydrate_ingredients=True)[0]

    def list_admin(
        self,
        pagination: PaginationParams,
        *,
        q: str | None = None,
        is_published: bool | None = None,
    ) -> PaginatedResponse[dict]:
        query = self.db.query(CookingPost)
        if q and q.strip():
            term = f"%{q.strip()}%"
            query = query.filter(
                (CookingPost.title_vi.ilike(term)) | (CookingPost.slug.ilike(term))
            )
        if is_published is not None:
            query = query.filter(CookingPost.is_published.is_(is_published))
        total = query.count()
        rows = (
            query.order_by(CookingPost.updated_at.desc(), CookingPost.id.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
            .all()
        )
        return PaginatedResponse.create(
            serialize_posts(self.db, rows, hydrate_ingredients=False),
            total,
            pagination.page,
            pagination.page_size,
        )

    def create(
        self,
        *,
        author_user_id: str,
        title_vi: str,
        content_md: str,
        excerpt: str | None = None,
        cover_image_url: str | None = None,
        slug: str | None = None,
        is_published: bool = False,
        sort_order: int = 0,
        dish_slug: str | None = None,
        servings: int = 1,
        yield_grams: float | None = None,
        ingredients: list | None = None,
    ) -> dict:
        title = title_vi.strip()
        body = content_md.strip()
        if not title:
            raise BadRequestError("title_vi không được trống")
        if not body:
            raise BadRequestError("content_md không được trống")
        now = _now()
        published = bool(is_published)
        row = CookingPost(
            slug=unique_slug(
                self.db, CookingPost, (slug or title), fallback="bai-viet"
            ),
            title_vi=title,
            excerpt=(excerpt or "").strip() or None,
            content_md=body,
            cover_image_url=(cover_image_url or "").strip() or None,
            is_published=published,
            published_at=now if published else None,
            author_user_id=author_user_id,
            sort_order=sort_order,
            dish_slug=(dish_slug or "").strip() or None,
            servings=max(int(servings or 1), 1),
            yield_grams=float(yield_grams) if yield_grams is not None else None,
            ingredients=_normalize_ingredients(ingredients),
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return serialize_posts(self.db, [row], hydrate_ingredients=True)[0]

    def update(self, post_id: int, data: dict) -> dict:
        row = self.db.get(CookingPost, post_id)
        if not row:
            raise NotFoundError("CookingPost", post_id)
        if "title_vi" in data and data["title_vi"] is not None:
            title = str(data["title_vi"]).strip()
            if not title:
                raise BadRequestError("title_vi không được trống")
            row.title_vi = title
        if "content_md" in data and data["content_md"] is not None:
            body = str(data["content_md"]).strip()
            if not body:
                raise BadRequestError("content_md không được trống")
            row.content_md = body
        if "excerpt" in data:
            excerpt = (data["excerpt"] or "").strip() if data["excerpt"] is not None else ""
            row.excerpt = excerpt or None
        if "cover_image_url" in data:
            url = (data["cover_image_url"] or "").strip() if data["cover_image_url"] else ""
            row.cover_image_url = url or None
        if "sort_order" in data and data["sort_order"] is not None:
            row.sort_order = int(data["sort_order"])
        if "dish_slug" in data:
            row.dish_slug = (str(data["dish_slug"] or "").strip() or None)
        if "servings" in data and data["servings"] is not None:
            row.servings = max(int(data["servings"]), 1)
        if "yield_grams" in data:
            row.yield_grams = (
                float(data["yield_grams"]) if data["yield_grams"] is not None else None
            )
        if "ingredients" in data and data["ingredients"] is not None:
            row.ingredients = _normalize_ingredients(data["ingredients"])
        if "slug" in data and data["slug"]:
            row.slug = unique_slug(
                self.db,
                CookingPost,
                str(data["slug"]),
                exclude_id=row.id,
                fallback="bai-viet",
            )
        if "is_published" in data and data["is_published"] is not None:
            want = bool(data["is_published"])
            if want and not row.is_published:
                row.published_at = _now()
            row.is_published = want
        row.updated_at = _now()
        self.db.commit()
        self.db.refresh(row)
        return serialize_posts(self.db, [row], hydrate_ingredients=True)[0]
