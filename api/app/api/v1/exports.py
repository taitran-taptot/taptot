from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.schemas.dynamic import build_schemas, model_to_dict
from app.models.entities import Export
from app.services.export_service import ExportService

router = APIRouter(prefix="/exports", tags=["Exports"])
_export_read, _, _ = build_schemas(Export, "Export")


class ExportRequest(BaseModel):
    export_type: str
    source_id: int
    format: str = "json"


@router.post("", status_code=201)
def create_export(payload: ExportRequest, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    record = ExportService(db).export_plan(user.id, payload.export_type, payload.source_id, payload.format)
    return _export_read.model_validate(model_to_dict(record))


@router.get("/{export_id}")
def get_export(export_id: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    record = ExportService(db).get_export(user.id, export_id)
    return _export_read.model_validate(model_to_dict(record))
