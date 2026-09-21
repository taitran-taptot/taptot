"""Push-up discount session tickets (no public leaderboard)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from jose import JWTError
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError
from app.core.security import create_pushup_ticket, decode_pushup_ticket
from app.models.entities import PushupChallengeSession

SESSION_TTL = timedelta(minutes=30)
MAX_REPS_PER_SEC = 1.2
MAX_REPS = 500


def discount_percent_for_reps(reps: int) -> int:
    if reps > 50:
        return 10
    if reps >= 21:
        return 7
    return 5


def _aware(stamp: datetime) -> datetime:
    if stamp.tzinfo is None:
        return stamp.replace(tzinfo=UTC)
    return stamp


def start_session(db: Session, *, ip: str | None = None, now: datetime | None = None) -> dict[str, Any]:
    stamp = now or datetime.now(UTC)
    row = PushupChallengeSession(id=str(uuid4()), started_at=stamp, ip=(ip or "")[:64] or None)
    db.add(row)
    db.commit()
    return {"session_id": row.id}


def finish_session(
    db: Session,
    *,
    session_id: str,
    reps: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    if reps < 0 or reps > MAX_REPS:
        raise BadRequestError("Số cái chống đẩy không hợp lệ.")
    row = db.query(PushupChallengeSession).filter(PushupChallengeSession.id == session_id).one_or_none()
    if row is None:
        raise BadRequestError("Phiên tập không hợp lệ.")
    if row.finished_at is not None:
        raise BadRequestError("Phiên tập đã kết thúc.")
    stamp = now or datetime.now(UTC)
    elapsed = max(0.0, (stamp - _aware(row.started_at)).total_seconds())
    if elapsed > SESSION_TTL.total_seconds():
        raise BadRequestError("Phiên tập đã hết hạn. Bật camera lại.")
    max_reps = min(MAX_REPS, int(elapsed * MAX_REPS_PER_SEC))
    if reps > max_reps:
        raise BadRequestError("Số cái không khớp thời gian tập.")

    jti = str(uuid4())
    percent = discount_percent_for_reps(reps)
    ticket = create_pushup_ticket(session_id=row.id, reps=reps, percent=percent, jti=jti)
    row.finished_at = stamp
    row.reps = reps
    row.ticket_jti = jti
    db.commit()
    return {"ticket": ticket, "reps": reps, "percent": percent, "session_id": row.id}


def _session_from_ticket(db: Session, ticket: str) -> tuple[dict[str, Any], PushupChallengeSession]:
    try:
        payload = decode_pushup_ticket(ticket)
    except (JWTError, ValueError):
        raise BadRequestError("Phiếu tập không hợp lệ.") from None
    sid = str(payload.get("sid") or "")
    jti = str(payload.get("jti") or "")
    row = db.query(PushupChallengeSession).filter(PushupChallengeSession.id == sid).one_or_none()
    if row is None or not row.ticket_jti or row.ticket_jti != jti:
        raise BadRequestError("Phiếu tập không hợp lệ.")
    return payload, row


def verify_ticket(db: Session, ticket: str) -> dict[str, Any]:
    try:
        payload, session = _session_from_ticket(db, ticket)
    except BadRequestError:
        return {"valid": False}
    return {
        "valid": True,
        "reps": int(payload.get("reps") or 0),
        "percent": int(payload.get("percent") or discount_percent_for_reps(int(payload.get("reps") or 0))),
        "session_id": session.id,
    }
