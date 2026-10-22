"""Admin CRM for /lien-he trainer consultation leads."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.pagination import PaginatedResponse, PaginationParams
from app.models.entities import TrainerContactRequest

LEAD_NEW = "new"
LEAD_CONTACTED = "contacted"
LEAD_WON = "won"
LEAD_LOST = "lost"
LEAD_STATUSES = frozenset({LEAD_NEW, LEAD_CONTACTED, LEAD_WON, LEAD_LOST})


def _iso(stamp: datetime | None) -> str | None:
    if stamp is None:
        return None
    return stamp.isoformat(timespec="seconds")


def serialize_lead(row: TrainerContactRequest) -> dict[str, Any]:
    return {
        "id": row.id,
        "full_name": row.full_name,
        "phone_zalo": row.phone_zalo,
        "goal": row.goal,
        "message": row.message,
        "status": str(row.status or LEAD_NEW),
        "admin_note": row.admin_note,
        "created_at": _iso(row.created_at),
    }


class TrainerContactService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_leads(
        self,
        pagination: PaginationParams,
        *,
        q: str | None = None,
        status: str | None = None,
        created_from: date | None = None,
        created_to: date | None = None,
    ) -> PaginatedResponse[dict[str, Any]]:
        query = self.db.query(TrainerContactRequest)
        term = (q or "").strip()
        if term:
            like = f"%{term}%"
            query = query.filter(
                or_(
                    TrainerContactRequest.full_name.ilike(like),
                    TrainerContactRequest.phone_zalo.ilike(like),
                    TrainerContactRequest.message.ilike(like),
                )
            )
        if status:
            st = status.strip().lower()
            if st not in LEAD_STATUSES:
                raise BadRequestError("Trạng thái không hợp lệ")
            query = query.filter(TrainerContactRequest.status == st)
        if created_from:
            start = datetime(created_from.year, created_from.month, created_from.day)
            query = query.filter(TrainerContactRequest.created_at >= start)
        if created_to:
            end = datetime(created_to.year, created_to.month, created_to.day) + timedelta(days=1)
            query = query.filter(TrainerContactRequest.created_at < end)
        total = query.count()
        rows = (
            query.order_by(
                TrainerContactRequest.created_at.desc(),
                TrainerContactRequest.id.desc(),
            )
            .offset(pagination.offset)
            .limit(pagination.page_size)
            .all()
        )
        return PaginatedResponse.create(
            [serialize_lead(row) for row in rows],
            total,
            pagination.page,
            pagination.page_size,
        )

    def update_lead(self, lead_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        row = self.db.query(TrainerContactRequest).filter(TrainerContactRequest.id == lead_id).first()
        if not row:
            raise NotFoundError("TrainerContactRequest", lead_id)
        if "status" in payload and payload["status"] is not None:
            st = str(payload["status"]).strip().lower()
            if st not in LEAD_STATUSES:
                raise BadRequestError("Trạng thái không hợp lệ")
            row.status = st
        if "admin_note" in payload:
            note = payload["admin_note"]
            row.admin_note = (str(note).strip() or None) if note is not None else None
        self.db.commit()
        self.db.refresh(row)
        return serialize_lead(row)
