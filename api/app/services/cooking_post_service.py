from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.pagination import PaginatedResponse, PaginationParams
from app.models.entities import CookingPost
from app.services.slug import unique_slug


def _now() -> datetime:
    return datetime.now(UTC)


def post_to_dict(row: CookingPost) -> dict:
    return {
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
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


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
            [post_to_dict(r) for r in rows],
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
        return post_to_dict(row)

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
            [post_to_dict(r) for r in rows],
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
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return post_to_dict(row)

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
            if not want:
                row.published_at = row.published_at
            row.is_published = want
        row.updated_at = _now()
        self.db.commit()
        self.db.refresh(row)
        return post_to_dict(row)
