"""Trainer profile (private edit + public share) and media upload."""

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user_optional, require_trainer
from app.services.media_service import MediaService
from app.services.trainer_profile_service import TrainerProfileService

router = APIRouter(tags=["Trainer profile"])


class TrainerProfileUpdateIn(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    age: int | None = Field(default=None, ge=16, le=100)
    years_experience: int | None = Field(default=None, ge=0, le=60)
    bio_vi: str | None = Field(default=None, max_length=4000)
    business_name: str | None = Field(default=None, max_length=255)
    gym_name: str | None = Field(default=None, max_length=255)


class CredentialIn(BaseModel):
    kind: str = Field(description="award | certificate")
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    image_urls: list[str] = Field(min_length=1)


@router.get("/trainer/profile")
def get_my_trainer_profile(
    user: CurrentUser = Depends(require_trainer),
    db: Session = Depends(get_db),
) -> dict:
    return TrainerProfileService(db).get_mine(user.id)


@router.put("/trainer/profile")
def update_my_trainer_profile(
    payload: TrainerProfileUpdateIn,
    user: CurrentUser = Depends(require_trainer),
    db: Session = Depends(get_db),
) -> dict:
    return TrainerProfileService(db).update_mine(
        user.id,
        full_name=payload.full_name,
        age=payload.age,
        years_experience=payload.years_experience,
        bio_vi=payload.bio_vi,
        business_name=payload.business_name,
        gym_name=payload.gym_name,
    )


@router.post("/trainer/credentials", status_code=201)
def add_trainer_credential(
    payload: CredentialIn,
    user: CurrentUser = Depends(require_trainer),
    db: Session = Depends(get_db),
) -> dict:
    return TrainerProfileService(db).add_credential(
        user.id,
        kind=payload.kind,
        title=payload.title,
        description=payload.description,
        image_urls=payload.image_urls,
    )


@router.delete("/trainer/credentials/{credential_id}", status_code=204)
def delete_trainer_credential(
    credential_id: int,
    user: CurrentUser = Depends(require_trainer),
    db: Session = Depends(get_db),
) -> None:
    TrainerProfileService(db).delete_credential(user.id, credential_id)


@router.post("/trainer/media/upload")
async def upload_trainer_media(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(require_trainer),
) -> dict:
    return await MediaService().save(file, subdir=f"trainers/{user.id}")


@router.get("/trainer/public/{share_token}")
def get_public_trainer_profile(
    share_token: str,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user_optional),
) -> dict:
    return TrainerProfileService(db).get_public(share_token)
