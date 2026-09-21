from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health")
def health():
    return {"status": "ok", "env": settings.app_env}
