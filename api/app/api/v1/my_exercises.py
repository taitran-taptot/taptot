"""HLV/admin private exercises for client plans only."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_staff
from app.core.pagination import PaginatedResponse, PaginationParams
from app.services.custom_exercise_service import CustomExerciseService

router = APIRouter(tags=["My exercises"])


class MyExerciseIn(BaseModel):
    name_vi: str = Field(min_length=1, max_length=200)
    muscle_group_id: int
    exercise_type: str = "main"
    notes_vi: str | None = None
    video_url: str | None = None
    image_url: str | None = None
    gif_url: str | None = None
    instruction_vi: str | None = None


class MyExercisePatch(BaseModel):
    name_vi: str | None = Field(default=None, min_length=1, max_length=200)
    muscle_group_id: int | None = None
    exercise_type: str | None = None
    notes_vi: str | None = None
    video_url: str | None = None
    image_url: str | None = None
    gif_url: str | None = None
    instruction_vi: str | None = None


@router.get("/my-exercises")
def list_my_exercises(
    pagination: Annotated[PaginationParams, Depends()],
    user=Depends(require_staff),
    db: Session = Depends(get_db),
):
    items, total = CustomExerciseService(db).list_mine(user.id, pagination)
    return PaginatedResponse.create(items, total, pagination.page, pagination.page_size)


@router.post("/my-exercises", status_code=201)
def create_my_exercise(
    payload: MyExerciseIn,
    user=Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    return CustomExerciseService(db).create(
        user.id,
        name_vi=payload.name_vi,
        muscle_group_id=payload.muscle_group_id,
        exercise_type=payload.exercise_type,
        notes_vi=payload.notes_vi,
        video_url=payload.video_url,
        image_url=payload.image_url,
        gif_url=payload.gif_url,
        instruction_vi=payload.instruction_vi,
    )


@router.patch("/my-exercises/{exercise_id}")
def update_my_exercise(
    exercise_id: int,
    payload: MyExercisePatch,
    user=Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    return CustomExerciseService(db).update(
        user.id, exercise_id, payload.model_dump(exclude_unset=True)
    )


@router.delete("/my-exercises/{exercise_id}", status_code=204)
def delete_my_exercise(
    exercise_id: int,
    user=Depends(require_staff),
    db: Session = Depends(get_db),
) -> None:
    CustomExerciseService(db).delete(user.id, exercise_id)
