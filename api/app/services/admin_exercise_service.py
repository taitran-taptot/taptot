"""Staff CRUD for public exercise catalog."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, can_hide_catalog_item
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.models.entities import Exercise, MuscleGroup
from app.schemas.dynamic import model_to_dict
from app.services.exercise_catalog_validate import validate_exercise_catalog_fields


def _now() -> datetime:
    return datetime.now(UTC)


def exercise_to_dict(ex: Exercise, muscle: MuscleGroup | None = None) -> dict[str, Any]:
    d = model_to_dict(ex)
    d["created_by"] = str(ex.created_by) if ex.created_by else None
    if muscle is not None:
        d["muscle_slug"] = muscle.slug
        d["muscle_name_vi"] = muscle.name_vi
    return d


class AdminExerciseService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _get(self, exercise_id: int) -> Exercise:
        row = self.db.get(Exercise, exercise_id)
        if not row:
            raise NotFoundError("Exercise", exercise_id)
        return row

    def _muscle(self, muscle_group_id: int) -> MuscleGroup:
        mg = self.db.get(MuscleGroup, muscle_group_id)
        if not mg:
            raise BadRequestError(f"Không tìm thấy nhóm cơ muscle_group_id={muscle_group_id}")
        return mg

    def create(self, data: dict[str, Any], *, created_by: str) -> dict:
        payload = validate_exercise_catalog_fields(dict(data))
        name = str(payload.get("name_vi") or "").strip()
        if not name:
            raise BadRequestError("Tên bài không được trống")
        mg_id = int(payload["muscle_group_id"])
        muscle = self._muscle(mg_id)
        now = _now()
        row = Exercise(
            name_vi=name,
            name_en=(str(payload["name_en"]).strip() if payload.get("name_en") else None),
            muscle_group_id=mg_id,
            exercise_type=payload.get("exercise_type") or "main",
            movement_role=payload.get("movement_role"),
            movement_pattern=payload.get("movement_pattern"),
            venue=payload.get("venue"),
            difficulty=int(payload.get("difficulty") or 2),
            difficulty_label=payload.get("difficulty_label"),
            notes_vi=(str(payload["notes_vi"]).strip() if payload.get("notes_vi") else None),
            is_active=bool(payload.get("is_active", True)),
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return exercise_to_dict(row, muscle)

    def update(self, exercise_id: int, data: dict[str, Any], *, actor: CurrentUser) -> dict:
        row = self._get(exercise_id)
        payload = validate_exercise_catalog_fields(dict(data))
        if "name_vi" in payload and payload["name_vi"] is not None:
            name = str(payload["name_vi"]).strip()
            if not name:
                raise BadRequestError("Tên bài không được trống")
            row.name_vi = name
        if "name_en" in payload:
            en = payload["name_en"]
            row.name_en = en.strip() if isinstance(en, str) and en.strip() else None
        if "muscle_group_id" in payload and payload["muscle_group_id"] is not None:
            self._muscle(int(payload["muscle_group_id"]))
            row.muscle_group_id = int(payload["muscle_group_id"])
        for field in ("exercise_type", "movement_role", "movement_pattern", "venue", "difficulty_label"):
            if field in payload and payload[field] is not None:
                setattr(row, field, payload[field])
        if "difficulty" in payload and payload["difficulty"] is not None:
            row.difficulty = int(payload["difficulty"])
            if payload.get("difficulty_label"):
                row.difficulty_label = payload["difficulty_label"]
        if "notes_vi" in payload:
            notes = payload["notes_vi"]
            row.notes_vi = notes.strip() if isinstance(notes, str) and notes.strip() else None
        if "is_active" in payload and payload["is_active"] is not None:
            next_active = bool(payload["is_active"])
            if next_active != bool(row.is_active):
                created_by = str(row.created_by) if row.created_by else None
                if not can_hide_catalog_item(actor, created_by):
                    raise ForbiddenError("Chỉ được ẩn bài do bạn tạo.")
            row.is_active = next_active
        row.updated_at = _now()
        self.db.commit()
        self.db.refresh(row)
        muscle = self.db.get(MuscleGroup, row.muscle_group_id)
        return exercise_to_dict(row, muscle)
