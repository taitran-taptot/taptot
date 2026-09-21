from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import BadRequestError
from app.core.rate_limit import client_ip
from app.services.pushup_challenge import finish_session, start_session, verify_ticket

router = APIRouter(prefix="/pushup-challenge", tags=["Pushup challenge"])


class PushupFinishIn(BaseModel):
    reps: int = Field(ge=0, le=500)


@router.post("/sessions")
def create_session(request: Request, db: Session = Depends(get_db)) -> dict:
    return start_session(db, ip=client_ip(request))


@router.post("/sessions/{session_id}/finish")
def complete_session(session_id: str, payload: PushupFinishIn, db: Session = Depends(get_db)) -> dict:
    return finish_session(db, session_id=session_id, reps=payload.reps)


@router.get("/tickets/verify")
def get_ticket_verify(ticket: str = Query(min_length=20), db: Session = Depends(get_db)) -> dict:
    return verify_ticket(db, ticket)


@router.post("/tickets/verify")
def post_ticket_verify(payload: dict, db: Session = Depends(get_db)) -> dict:
    ticket = str((payload or {}).get("ticket") or "")
    if len(ticket) < 20:
        raise BadRequestError("Phiếu tập không hợp lệ.")
    return verify_ticket(db, ticket)
