from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends

from app.core.database import get_db
from app.core.deps import require_admin_write
from app.services.site_page_media import SitePageMediaService

router = APIRouter(tags=["Site"])


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
