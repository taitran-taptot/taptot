from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_optional
from app.services.search_service import SearchService

router = APIRouter(prefix="/programs", tags=["Programs"])


@router.get("/{program_id}/detail")
def program_detail(
    program_id: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user_optional),
):
    detail = SearchService(db).get_program_detail(program_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Program not found")
    return detail
