"""Staff-owned private exercises (exercises.owner_user_id)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.pagination import PaginationParams
from app.models.entities import Exercise, MuscleGroup, UserDailyPlanExercise
from app.services.admin_exercise_service import exercise_to_dict
from app.services.exercise_catalog_validate import VALID_EXERCISE_TYPES


def _now() -> datetime:
    return datetime.now(UTC)


class CustomExerciseService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_mine(
        self, user_id: str, pagination: PaginationParams | None = None
    ) -> tuple[list[dict[str, Any]], int]:
        query = (
            self.db.query(Exercise, MuscleGroup)
            .join(MuscleGroup, MuscleGroup.id == Exercise.muscle_group_id)
            .filter(Exercise.owner_user_id == user_id)
        )
        total = query.count()
        q = query.order_by(Exercise.updated_at.desc())
        if pagination:
            q = q.offset(pagination.offset).limit(pagination.page_size)
        rows = q.all()
        return [exercise_to_dict(ex, mg) for ex, mg in rows], total

    def _muscle(self, muscle_group_id: int) -> MuscleGroup:
        mg = self.db.get(MuscleGroup, muscle_group_id)
        if not mg:
            raise BadRequestError(f"Không tìm thấy nhóm cơ muscle_group_id={muscle_group_id}")
        return mg

    def create(
        self,
        user_id: str,
        *,
        name_vi: str,
        muscle_group_id: int,
        exercise_type: str = "main",
        notes_vi: str | None = None,
        video_url: str | None = None,
        image_url: str | None = None,
        gif_url: str | None = None,
        instruction_vi: str | None = None,
    ) -> dict[str, Any]:
        name = name_vi.strip()
        if not name:
            raise BadRequestError("Tên bài không được trống")
        et = (exercise_type or "main").strip().lower()
        if et not in VALID_EXERCISE_TYPES:
            raise BadRequestError("exercise_type phải là warmup, main, cooldown hoặc cardio")
        muscle = self._muscle(int(muscle_group_id))
        now = _now()
        row = Exercise(
            name_vi=name,
            muscle_group_id=muscle.id,
            exercise_type=et,
            notes_vi=(notes_vi.strip() if notes_vi and notes_vi.strip() else None),
            video_url=(video_url.strip() if video_url and video_url.strip() else None),
            image_url=(image_url.strip() if image_url and image_url.strip() else None),
            gif_url=(gif_url.strip() if gif_url and gif_url.strip() else None),
            instruction_vi=(instruction_vi.strip() if instruction_vi and instruction_vi.strip() else None),
            venue="both",
            difficulty=2,
            secondary_muscles=[],
            is_active=True,
            owner_user_id=user_id,
            created_by=user_id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return exercise_to_dict(row, muscle)

    def _owned(self, user_id: str, exercise_id: int) -> Exercise:
        row = self.db.get(Exercise, exercise_id)
        if not row or row.owner_user_id is None:
            raise NotFoundError("Exercise", exercise_id)
        if str(row.owner_user_id) != str(user_id):
            raise ForbiddenError("Không phải bài tập của bạn")
        return row

    def update(self, user_id: str, exercise_id: int, data: dict[str, Any]) -> dict[str, Any]:
        row = self._owned(user_id, exercise_id)
        if "name_vi" in data and data["name_vi"] is not None:
            name = str(data["name_vi"]).strip()
            if not name:
                raise BadRequestError("Tên bài không được trống")
            row.name_vi = name
        if "muscle_group_id" in data and data["muscle_group_id"] is not None:
            self._muscle(int(data["muscle_group_id"]))
            row.muscle_group_id = int(data["muscle_group_id"])
        if "exercise_type" in data and data["exercise_type"] is not None:
            et = str(data["exercise_type"]).strip().lower()
            if et not in VALID_EXERCISE_TYPES:
                raise BadRequestError("exercise_type phải là warmup, main, cooldown hoặc cardio")
            row.exercise_type = et
        for field in ("notes_vi", "video_url", "image_url", "gif_url", "instruction_vi"):
            if field in data:
                raw = data[field]
                setattr(row, field, raw.strip() if isinstance(raw, str) and raw.strip() else None)
        row.updated_at = _now()
        self.db.commit()
        self.db.refresh(row)
        muscle = self.db.get(MuscleGroup, row.muscle_group_id)
        return exercise_to_dict(row, muscle)

    def delete(self, user_id: str, exercise_id: int) -> None:
        row = self._owned(user_id, exercise_id)
        used = (
            self.db.query(UserDailyPlanExercise.id)
            .filter(UserDailyPlanExercise.exercise_id == exercise_id)
            .first()
        )
        if used:
            row.is_active = False
            row.updated_at = _now()
            self.db.commit()
            return
        self.db.delete(row)
        self.db.commit()
