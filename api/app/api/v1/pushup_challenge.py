from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.pushup_challenge import finish_session, start_session

router = APIRouter(prefix="/pushup-challenge", tags=["Pushup challenge"])


class PushupFinishIn(BaseModel):
    reps: int = Field(ge=0, le=500)
    kind: str = Field(default="pushup", max_length=16)


@router.post("/sessions")
def create_session(db: Session = Depends(get_db)) -> dict:
    return start_session(db)


@router.post("/sessions/{session_id}/finish")
def complete_session(session_id: str, payload: PushupFinishIn, db: Session = Depends(get_db)) -> dict:
    return finish_session(db, session_id=session_id, reps=payload.reps, kind=payload.kind)
