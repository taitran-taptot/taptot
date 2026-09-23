"""API routes for user daily plans (auth + public share)."""

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, get_current_user_optional
from app.core.exceptions import BadRequestError, UnauthorizedError
from app.schemas.plans import (
    ClaimPlansOut,
    ClaimPlansRequest,
    CreatePlanRequest,
    PlanDetailOut,
    PlanExportRequest,
    PlanQuotaOut,
    PlanSummaryOut,
    UpdatePlanContentRequest,
)
from app.services.plan_service import PlanService

router = APIRouter(tags=["My Plans"])


@router.get("/my-plans", response_model=list[PlanSummaryOut])
def list_my_plans(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    return PlanService(db).list_plans(user.id)


@router.get("/my-plans/quota", response_model=PlanQuotaOut)
def my_plans_quota(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return PlanService(db).get_quota(user.id)


@router.post("/my-plans/claim", response_model=ClaimPlansOut)
def claim_guest_plans(
    payload: ClaimPlansRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Gắn các lịch guest (chưa có user) vào tài khoản đang đăng nhập."""
    return PlanService(db).claim_guest_plans(user.id, payload.share_tokens)


@router.post("/my-plans", response_model=PlanDetailOut, status_code=201)
def create_my_plan(
    payload: CreatePlanRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return PlanService(db).create_plan(user.id, payload)


@router.post("/plans", response_model=PlanDetailOut, status_code=201)
def create_plan_public(
    payload: CreatePlanRequest,
    user: CurrentUser | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> dict:
    """Create a plan — authenticated users are linked; guests get an unassigned shareable plan."""
    if getattr(payload, "challenge_100_days", False) and not user:
        raise UnauthorizedError("Đăng nhập để tạo thử thách 100 ngày")
    return PlanService(db).create_plan(user.id if user else None, payload)


@router.get("/plans/share/{token}", response_model=PlanDetailOut)
def get_plan_by_share_token(token: str, db: Session = Depends(get_db)) -> dict:
    return PlanService(db).get_by_share_token(token)


@router.get("/my-plans/{plan_id}", response_model=PlanDetailOut)
def get_my_plan(
    plan_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return PlanService(db).get_plan(user.id, plan_id)


@router.post("/my-plans/{plan_id}/restore-ai", response_model=PlanDetailOut)
def restore_my_plan_ai(
    plan_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Overwrite edited days/meals with the original TAPTOT snapshot."""
    return PlanService(db).restore_ai(user.id, plan_id)


@router.put("/my-plans/{plan_id}/content", response_model=PlanDetailOut)
def update_my_plan_content(
    plan_id: int,
    payload: UpdatePlanContentRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Edit exercises (sets/reps) and meals. Title / calories / source stay locked."""
    return PlanService(db).update_plan_content(user.id, plan_id, payload)


@router.delete("/my-plans/{plan_id}", status_code=204)
def delete_my_plan(
    plan_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    PlanService(db).delete_plan(user.id, plan_id)


@router.post("/my-plans/{plan_id}/export")
def export_my_plan(
    plan_id: int,
    payload: PlanExportRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export plan as a branded PDF and return the file."""
    opts = payload.options.model_dump() if payload.options else None
    record = PlanService(db).export_plan(user.id, plan_id, payload.format, opts)
    if not record.file_url:
        raise BadRequestError("Export failed")
    from pathlib import Path

    from app.core.config import get_settings

    settings = get_settings()
    filename = Path(record.file_url).name
    from app.core.config import PROJECT_ROOT

    filepath = PROJECT_ROOT / "data" / "exports" / filename
    # Legacy files may still sit under uploads/exports
    if not filepath.exists():
        filepath = Path(settings.upload_dir) / "exports" / filename
    if filepath.exists():
        # Prevent path traversal via crafted file_url
        exports_root = (PROJECT_ROOT / "data" / "exports").resolve()
        legacy_root = (Path(settings.upload_dir) / "exports").resolve()
        resolved = filepath.resolve()
        if not (
            str(resolved).startswith(str(exports_root))
            or str(resolved).startswith(str(legacy_root))
        ):
            raise BadRequestError("Invalid export path")
        media = "application/pdf"
        return FileResponse(
            path=str(filepath),
            media_type=media,
            filename=filename,
            headers={"X-Export-Id": str(record.id), "X-File-Url": record.file_url or ""},
        )
    return {
        "id": record.id,
        "format": record.format,
        "file_url": record.file_url,
        "export_type": record.export_type,
        "created_at": record.created_at,
    }


@router.post("/plans/share/{token}/export")
def export_shared_plan(
    token: str,
    payload: PlanExportRequest,
    db: Session = Depends(get_db),
):
    """Export a publicly shared plan (no auth) — file only, no Export DB row."""
    detail = PlanService(db).get_by_share_token(token)
    from app.services.export_service import ExportService

    opts = payload.options.model_dump() if payload.options else None
    filepath, filename, mime = ExportService(db).render_detail_file(detail, payload.format, opts)
    return FileResponse(path=str(filepath), media_type=mime, filename=filename)
