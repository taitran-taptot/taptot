from fastapi import APIRouter, Depends, File, UploadFile

from app.core.deps import require_admin
from app.services.media_service import MediaService

router = APIRouter(prefix="/media", tags=["Media"])


@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    _admin=Depends(require_admin),
):
    return await MediaService().save(file)
