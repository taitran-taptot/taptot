from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_optional
from app.core.exceptions import NotFoundError
from app.core.pagination import PaginatedResponse, PaginationParams
from app.models.entities import Food
from app.schemas.dynamic import build_schemas, model_to_dict
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["Search"])

_food_read_schema, _, _ = build_schemas(Food, "Food")


class ExerciseSearchItem(BaseModel):
    id: int
    name_en: str = ""
    name_vi: str
    body_part: str
    muscle_group: str | None = None
    muscle_group_id: int | None = None
    equipment: str
    equipment_slugs: list[str] = Field(default_factory=list)
    exercise_type: str = "main"
    exercise_type_label: str | None = None
    movement_role: str | None = None
    movement_pattern: str | None = None
    difficulty: int
    difficulty_label: str | None = None
    notes_vi: str | None = None
    is_beginner_friendly: bool = True
    gif_url: str | None = None
    image_url: str | None = None
    video_url: str | None = None


class ExerciseDetailItem(ExerciseSearchItem):
    target_muscle: str | None = None
    secondary_muscles: list[str] = []
    image_url: str | None = None
    instruction_vi: str | None = None
    instruction_steps_vi: list[str] | None = None
    instruction_en: str | None = None
    instruction_steps_en: list[str] | None = None
    common_mistakes_vi: str | None = None
    tips_vi: str | None = None


class LabelItem(BaseModel):
    key: str
    label_vi: str
    id: int | None = None
    category: str | None = None
    name_en: str | None = None
    parent_id: int | None = None
    parent_slug: str | None = None
    is_filter_only: bool | None = None
    image_url: str | None = None
    image_source: str | None = None
    image_attribution: str | None = None


class MuscleTreeNode(BaseModel):
    key: str
    label_vi: str
    id: int | None = None
    name_en: str | None = None
    is_filter_only: bool = False
    children: list["MuscleTreeNode"] = Field(default_factory=list)


MuscleTreeNode.model_rebuild()


class EquipmentImageItem(BaseModel):
    url: str
    thumb: str
    alt: str = ""


def _int_list(raw: str | None) -> list[int] | None:
    if not raw:
        return None
    values = [v.strip() for v in raw.split(",") if v.strip().isdigit()]
    return [int(v) for v in values] or None


def _str_list(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return [v.strip() for v in raw.split(",") if v.strip()] or None


@router.get("/exercises", response_model=PaginatedResponse[ExerciseSearchItem])
def search_exercises(
    pagination: Annotated[PaginationParams, Depends()],
    q: str | None = None,
    body_part: str | None = None,
    equipment: str | None = None,
    difficulty: str | None = None,
    beginner_only: bool = False,
    exercise_type: str | None = None,
    muscle_group_id: int | None = None,
    muscle_group_ids: str | None = None,
    difficulties: str | None = None,
    equipment_categories: str | None = None,
    movement_roles: str | None = None,
    movement_patterns: str | None = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user_optional),
):
    items, total = SearchService(db).search_exercises(
        pagination,
        q,
        body_part,
        equipment,
        difficulty,
        beginner_only,
        exercise_type=exercise_type,
        muscle_group_id=muscle_group_id,
        muscle_group_ids=_int_list(muscle_group_ids),
        difficulties=_int_list(difficulties),
        equipment_categories=_str_list(equipment_categories),
        movement_roles=_str_list(movement_roles),
        movement_patterns=_str_list(movement_patterns),
    )
    return PaginatedResponse.create(items, total, pagination.page, pagination.page_size)


@router.get("/exercises/{exercise_id}", response_model=ExerciseDetailItem)
def get_exercise_detail(
    exercise_id: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user_optional),
):
    detail = SearchService(db).get_exercise_detail(exercise_id)
    if not detail:
        raise NotFoundError("Exercise", exercise_id)
    return detail


@router.get("/muscle-groups", response_model=list[LabelItem])
def list_muscle_groups(db: Session = Depends(get_db), _user=Depends(get_current_user_optional)):
    return SearchService(db).list_muscle_group_labels()


@router.get("/muscle-groups/tree", response_model=list[MuscleTreeNode])
def list_muscle_group_tree(
    db: Session = Depends(get_db), _user=Depends(get_current_user_optional)
):
    return SearchService(db).list_muscle_group_tree()


@router.get("/equipment", response_model=list[LabelItem])
def list_equipment(db: Session = Depends(get_db), _user=Depends(get_current_user_optional)):
    return SearchService(db).list_equipment_labels()


@router.get("/equipment-images", response_model=list[EquipmentImageItem])
def list_equipment_images(slug: str, _user=Depends(get_current_user_optional)):
    """List every local image inside uploads/media/equipment/<slug>/."""
    from app.services.equipment_media import list_equipment_images as list_images

    return [EquipmentImageItem.model_validate(i) for i in list_images(slug)]


@router.get("/foods", response_model=PaginatedResponse[Any])
def search_foods(
    pagination: Annotated[PaginationParams, Depends()],
    q: str | None = None,
    category_id: int | None = None,
    is_common: bool | None = None,
    tag: str | None = None,
    diet: str | None = None,
    mine_only: bool = False,
    exclude_raw: bool = False,
    macro_role: str | None = None,
    complete_meal: bool | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
):
    owner_id = user.id if user else None
    items, total = SearchService(db).search_foods(
        pagination,
        q,
        category_id,
        is_common,
        tag=tag,
        diet=diet,
        owner_user_id=owner_id,
        mine_only=mine_only and bool(owner_id),
        exclude_raw=exclude_raw,
        macro_role=macro_role,
        complete_meal=complete_meal,
    )
    return PaginatedResponse.create(
        [_food_read_schema.model_validate(model_to_dict(i)) for i in items],
        total,
        pagination.page,
        pagination.page_size,
    )


@router.get("/exercises/{exercise_id}/alternatives", response_model=list[ExerciseSearchItem])
def exercise_alternatives(
    exercise_id: int,
    limit: int = 5,
    location: str | None = Query(default=None),
    no_equipment: bool = Query(default=False),
    equipment: Annotated[list[str] | None, Query()] = None,
    db: Session = Depends(get_db),
):
    items = SearchService(db).exercise_alternatives(
        exercise_id,
        limit=limit,
        location=location,
        no_equipment=no_equipment,
        equipment=equipment,
    )
    if not items and not SearchService(db).get_exercise_detail(exercise_id):
        raise NotFoundError("Exercise", exercise_id)
    return [ExerciseSearchItem.model_validate(i) for i in items]
