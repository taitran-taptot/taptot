from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends

from app.core.database import get_db
from app.core.deps import require_admin_write
from app.services.site_legal import SiteLegalService
from app.services.site_page_media import SitePageMediaService

router = APIRouter(tags=["Site"])


class SuccessStoryIn(BaseModel):
    image_url: str = Field(default="", max_length=500)
    logo_url: str = Field(default="", max_length=500)
    name: str = Field(default="", max_length=80)
    occupation: str = Field(default="", max_length=80)
    quote: str = Field(default="", max_length=280)


class SitePageMediaPatch(BaseModel):
    home_challenge_youtube: str | None = Field(default=None, max_length=400)
    home_challenge_youtube_id: str | None = Field(default=None, max_length=32)
    shop_guide_youtube: str | None = Field(default=None, max_length=400)
    shop_guide_youtube_id: str | None = Field(default=None, max_length=32)
    service_lo_trinh_image_url: str | None = Field(default=None, max_length=500)
    service_dung_cu_image_url: str | None = Field(default=None, max_length=500)
    service_hlv_image_url: str | None = Field(default=None, max_length=500)
    about_hero_image_url: str | None = Field(default=None, max_length=500)
    about_founder_image_url: str | None = Field(default=None, max_length=500)
    about_trainer_image_url: str | None = Field(default=None, max_length=500)
    contact_trainer_image_url: str | None = Field(default=None, max_length=500)
    success_stories: list[SuccessStoryIn] | None = None
    success_stories_visible: bool | None = None
    bo_cong_thuong_url: str | None = Field(default=None, max_length=500)
    footer_phone_href: str | None = Field(default=None, max_length=500)
    footer_email_href: str | None = Field(default=None, max_length=500)
    footer_facebook_href: str | None = Field(default=None, max_length=500)
    footer_tiktok_href: str | None = Field(default=None, max_length=500)


@router.get("/site/page-media")
def get_site_page_media(db: Session = Depends(get_db)):
    return SitePageMediaService(db).get_public()


@router.patch("/admin/site/page-media")
def patch_site_page_media(
    payload: SitePageMediaPatch,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin_write),
):
    data = payload.model_dump(exclude_unset=True)
    return SitePageMediaService(db).upsert(data)


class LegalSectionIn(BaseModel):
    id: str = Field(default="", max_length=40)
    title: str = Field(default="", max_length=300)
    paragraphs: list[str] = Field(default_factory=list, max_length=20)
    bullets: list[str] = Field(default_factory=list, max_length=30)


class LegalDocumentIn(BaseModel):
    updated_label: str = Field(default="", max_length=200)
    intro: str = Field(default="", max_length=4000)
    agreement: str = Field(default="", max_length=4000)
    sections: list[LegalSectionIn] = Field(min_length=1, max_length=40)


@router.get("/site/legal/{slug}")
def get_site_legal(slug: str, db: Session = Depends(get_db)):
    return SiteLegalService(db).get_public(slug)


@router.put("/admin/site/legal/{slug}")
def put_site_legal(
    slug: str,
    payload: LegalDocumentIn,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin_write),
):
    return SiteLegalService(db).upsert(slug, payload.model_dump())


@router.delete("/admin/site/legal/{slug}")
def delete_site_legal(
    slug: str,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin_write),
):
    return SiteLegalService(db).reset(slug)
