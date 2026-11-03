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
MAX_REPS = 500
PUSHUP_SCORE_CAP = 100
PUSHUP_FULL_SEC = 75
PLANK_MIN_ELAPSED_SEC = 55
PLANK_PERCENT = 10


def discount_percent_for_reps(reps: int) -> float:
    """0.2% per rep, capped at 100 reps (20%)."""
    counted = min(max(int(reps), 0), PUSHUP_SCORE_CAP)
    return (counted * 2) / 10


def quantize_percent(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if number != number or number in (float("inf"), float("-inf")):
        return 0.0
    return round(number * 10) / 10


def max_pushup_reps(elapsed: float) -> int:
    """Full attempt is 15s prep + 60s work. That window allows 100 reps."""
    if elapsed <= 0:
        return 0
    return min(PUSHUP_SCORE_CAP, int(elapsed * PUSHUP_SCORE_CAP // PUSHUP_FULL_SEC))


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
    kind: str = "pushup",
    now: datetime | None = None,
) -> dict[str, Any]:
    event_kind = "plank" if kind == "plank" else "pushup"
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

    if event_kind == "plank":
        if elapsed < PLANK_MIN_ELAPSED_SEC:
            raise BadRequestError("Phiên plank chưa đủ thời gian.")
        reps = 0
        percent = PLANK_PERCENT
    else:
        max_reps = max_pushup_reps(elapsed)
        if reps > max_reps:
            raise BadRequestError("Số cái không khớp thời gian tập.")
        percent = discount_percent_for_reps(reps)

    row.finished_at = stamp
    row.reps = reps
    if percent <= 0:
        db.commit()
        return {"ticket": "", "reps": reps, "percent": 0, "session_id": row.id, "kind": event_kind}

    jti = str(uuid4())
    ticket = create_pushup_ticket(session_id=row.id, reps=reps, percent=percent, jti=jti, kind=event_kind)
    row.ticket_jti = jti
    db.commit()
    return {"ticket": ticket, "reps": reps, "percent": percent, "session_id": row.id, "kind": event_kind}


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
    if session.entry_used_at is not None:
        return {"valid": False}
    return {
        "valid": True,
        "reps": int(payload.get("reps") or 0),
        "percent": quantize_percent(
            payload.get("percent")
            if payload.get("percent") is not None
            else discount_percent_for_reps(int(payload.get("reps") or 0))
        ),
        "session_id": session.id,
    }


def ticket_for_checkout(db: Session, ticket: str) -> tuple[float, PushupChallengeSession]:
    """Validate a ticket for checkout. Does not mark it used."""
    try:
        payload, session = _session_from_ticket(db, ticket)
    except BadRequestError:
        raise BadRequestError("Phiếu giảm giá không hợp lệ hoặc đã hết hạn.") from None
    if session.entry_used_at is not None:
        raise BadRequestError("Phiếu giảm giá đã được dùng.")
    raw = payload.get("percent")
    percent = quantize_percent(
        raw if raw is not None else discount_percent_for_reps(int(payload.get("reps") or 0))
    )
    if percent <= 0:
        raise BadRequestError("Phiếu giảm giá không hợp lệ hoặc đã hết hạn.")
    return percent, session
