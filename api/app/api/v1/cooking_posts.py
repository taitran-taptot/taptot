from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, require_admin, require_admin_write
from app.core.pagination import PaginationParams
from app.services.cooking_post_service import CookingPostService

router = APIRouter(tags=["Cooking"])


class CookingIngredientIn(BaseModel):
    food_slug: str = Field(min_length=1, max_length=150)
    grams: float | None = Field(default=None, ge=0)
    amount_label: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=255)


class CookingPostIn(BaseModel):
    title_vi: str = Field(min_length=2, max_length=255)
    content_md: str = Field(min_length=1)
    excerpt: str | None = Field(default=None, max_length=500)
    cover_image_url: str | None = None
    slug: str | None = Field(default=None, max_length=150)
    is_published: bool = False
    sort_order: int = 0
    dish_slug: str | None = Field(default=None, max_length=150)
    servings: int = Field(default=1, ge=1, le=50)
    yield_grams: float | None = Field(default=None, ge=0)
    ingredients: list[CookingIngredientIn] = Field(default_factory=list)


class CookingPostPatch(BaseModel):
    title_vi: str | None = Field(default=None, min_length=2, max_length=255)
    content_md: str | None = Field(default=None, min_length=1)
    excerpt: str | None = Field(default=None, max_length=500)
    cover_image_url: str | None = None
    slug: str | None = Field(default=None, max_length=150)
    is_published: bool | None = None
    sort_order: int | None = None
    dish_slug: str | None = Field(default=None, max_length=150)
    servings: int | None = Field(default=None, ge=1, le=50)
    yield_grams: float | None = Field(default=None, ge=0)
    ingredients: list[CookingIngredientIn] | None = None


@router.get("/cooking-posts")
def list_cooking_posts(
    pagination: Annotated[PaginationParams, Depends()],
    db: Session = Depends(get_db),
):
    return CookingPostService(db).list_public(pagination)


@router.get("/cooking-posts/{slug}")
def get_cooking_post(slug: str, db: Session = Depends(get_db)):
    return CookingPostService(db).get_public_by_slug(slug)


@router.get("/admin/cooking-posts")
def admin_list_cooking_posts(
    pagination: Annotated[PaginationParams, Depends()],
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin),
    q: str | None = Query(default=None),
    is_published: bool | None = None,
):
    return CookingPostService(db).list_admin(
        pagination, q=q, is_published=is_published
    )


@router.post("/admin/cooking-posts", status_code=201)
def admin_create_cooking_post(
    payload: CookingPostIn,
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(require_admin_write),
):
    return CookingPostService(db).create(
        author_user_id=admin.id,
        title_vi=payload.title_vi,
        content_md=payload.content_md,
        excerpt=payload.excerpt,
        cover_image_url=payload.cover_image_url,
        slug=payload.slug,
        is_published=payload.is_published,
        sort_order=payload.sort_order,
        dish_slug=payload.dish_slug,
        servings=payload.servings,
        yield_grams=payload.yield_grams,
        ingredients=[item.model_dump() for item in payload.ingredients],
    )


@router.patch("/admin/cooking-posts/{post_id}")
def admin_update_cooking_post(
    post_id: int,
    payload: CookingPostPatch,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(require_admin_write),
):
    data = payload.model_dump(exclude_unset=True)
    return CookingPostService(db).update(post_id, data)
