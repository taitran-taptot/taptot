from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health")
def health():
    return {"status": "ok", "env": settings.app_env}


@router.get("/health/deep")
def health_deep(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "env": settings.app_env,
        "database": "connected",
        "redis_rate_limit": settings.use_redis_rate_limit,
        "email_provider": settings.email_provider,
        "ai_configured": False,
    }
