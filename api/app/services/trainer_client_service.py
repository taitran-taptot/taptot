"""Trainer–client relationship helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.models.entities import TrainerAssignedPlan, TrainerClient, User


class TrainerClientService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_clients(self, trainer_id: str) -> list[dict[str, Any]]:
        rows = (
            self.db.query(TrainerClient, User)
            .join(User, User.id == TrainerClient.client_id)
            .filter(TrainerClient.trainer_id == trainer_id)
            .order_by(TrainerClient.started_at.desc())
            .all()
        )
        client_ids = [link.client_id for link, _user in rows]
        assigned_counts: dict[Any, int] = {}
        if client_ids:
            assigned_counts = dict(
                self.db.query(TrainerAssignedPlan.client_id, func.count(TrainerAssignedPlan.id))
                .filter(
                    TrainerAssignedPlan.trainer_id == trainer_id,
                    TrainerAssignedPlan.client_id.in_(client_ids),
                    TrainerAssignedPlan.status == "active",
                )
                .group_by(TrainerAssignedPlan.client_id)
                .all()
            )
        out = []
        for link, user in rows:
            assigned = int(assigned_counts.get(link.client_id, 0))
            out.append(
                {
                    "id": link.id,
                    "client_id": str(link.client_id),
                    "email": user.email,
                    "display_name": user.display_name,
                    "status": link.status,
                    "started_at": link.started_at.isoformat() if link.started_at else None,
                    "ended_at": link.ended_at.isoformat() if link.ended_at else None,
                    "active_plans": assigned,
                    "full_name": link.full_name,
                    "goal": link.goal,
                    "gender": link.gender,
                    "age": link.age,
                    "height_cm": float(link.height_cm) if link.height_cm is not None else None,
                    "weight_kg": float(link.weight_kg) if link.weight_kg is not None else None,
                }
            )
        return out

    @staticmethod
    def _apply_client_info(link: TrainerClient, info: dict[str, Any] | None) -> None:
        if not info:
            return
        for field in ("full_name", "goal", "gender", "age", "height_cm", "weight_kg"):
            if field in info:
                setattr(link, field, info[field])

    def update_client_info(
        self,
        trainer_id: str,
        client_id: str,
        *,
        full_name: str | None = None,
        goal: str | None = None,
        gender: str | None = None,
        age: int | None = None,
        height_cm: float | None = None,
        weight_kg: float | None = None,
    ) -> dict[str, Any]:
        link = (
            self.db.query(TrainerClient)
            .filter(
                TrainerClient.trainer_id == trainer_id,
                TrainerClient.client_id == client_id,
            )
            .first()
        )
        if not link:
            raise NotFoundError("TrainerClient", client_id)
        if link.status != "active":
            raise BadRequestError("Học viên đã bị gỡ — hãy thêm lại trước khi sửa")
        link.full_name = (full_name or "").strip() or None
        link.goal = goal or None
        link.gender = gender or None
        link.age = age
        link.height_cm = height_cm
        link.weight_kg = weight_kg
        self.db.commit()
        return self._one(trainer_id, str(client_id))

    def add_by_email(
        self,
        trainer_id: str,
        email: str,
        client_info: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        email_norm = email.strip().lower()
        if not email_norm:
            raise BadRequestError("Email không hợp lệ")
        user = self.db.query(User).filter(User.email == email_norm).first()
        if not user:
            raise NotFoundError("User", email_norm)
        if str(user.id) == str(trainer_id):
            raise BadRequestError("Không thể thêm chính mình làm học viên")
        existing = (
            self.db.query(TrainerClient)
            .filter(
                TrainerClient.trainer_id == trainer_id,
                TrainerClient.client_id == user.id,
            )
            .first()
        )
        if existing:
            if existing.status != "active":
                existing.status = "active"
                existing.ended_at = None
            self._apply_client_info(existing, client_info)
            self.db.commit()
            return self._one(trainer_id, str(user.id))
        link = TrainerClient(
            trainer_id=trainer_id,
            client_id=user.id,
            status="active",
            started_at=datetime.now(UTC).date(),
        )
        self._apply_client_info(link, client_info)
        self.db.add(link)
        self.db.commit()
        return self._one(trainer_id, str(user.id))

    def remove(self, trainer_id: str, client_id: str) -> None:
        link = (
            self.db.query(TrainerClient)
            .filter(
                TrainerClient.trainer_id == trainer_id,
                TrainerClient.client_id == client_id,
            )
            .first()
        )
        if not link:
            raise NotFoundError("TrainerClient", client_id)
        link.status = "ended"
        link.ended_at = datetime.now(UTC).date()
        self.db.commit()

    def _one(self, trainer_id: str, client_id: str) -> dict[str, Any]:
        for row in self.list_clients(trainer_id):
            if row["client_id"] == client_id:
                return row
        raise NotFoundError("TrainerClient", client_id)

    def assert_owns_client(self, trainer_id: str, client_id: str) -> None:
        link = (
            self.db.query(TrainerClient)
            .filter(
                TrainerClient.trainer_id == trainer_id,
                TrainerClient.client_id == client_id,
                TrainerClient.status == "active",
            )
            .first()
        )
        if not link:
            raise ForbiddenError("Học viên không thuộc HLV này")
