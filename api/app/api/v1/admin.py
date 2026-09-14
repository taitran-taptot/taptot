from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.pagination import PaginatedResponse, PaginationParams
from app.models.entities import Equipment, Exercise, ExerciseEquipment, MuscleGroup
from app.schemas.dynamic import model_to_dict
from app.services.admin_food_service import AdminFoodService
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["Admin"])


class EquipmentIdsIn(BaseModel):
    equipment_ids: list[int] = Field(default_factory=list)


@router.get("/stats")
def admin_stats(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    return AdminService(db).stats()


@router.get("/exercises")
def admin_list_exercises(
    pagination: Annotated[PaginationParams, Depends()],
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
    q: str | None = Query(default=None),
    muscle_group_id: int | None = None,
    movement_pattern: str | None = None,
    movement_role: str | None = None,
    venue: str | None = None,
    difficulty: int | None = None,
    is_active: bool | None = None,
    exercise_type: str | None = None,
):
    query = (
        db.query(Exercise, MuscleGroup)
        .join(MuscleGroup, MuscleGroup.id == Exercise.muscle_group_id)
    )
    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(
            (Exercise.name_vi.ilike(term)) | (Exercise.name_en.ilike(term))
        )
    if muscle_group_id is not None:
        query = query.filter(Exercise.muscle_group_id == muscle_group_id)
    if movement_pattern:
        query = query.filter(Exercise.movement_pattern == movement_pattern)
    if movement_role:
        query = query.filter(Exercise.movement_role == movement_role)
    if venue:
        query = query.filter(Exercise.venue == venue)
    if difficulty is not None:
        query = query.filter(Exercise.difficulty == difficulty)
    if is_active is not None:
        query = query.filter(Exercise.is_active.is_(is_active))
    if exercise_type:
        query = query.filter(Exercise.exercise_type == exercise_type)
    total = query.count()
    rows = (
        query.order_by(Exercise.id.asc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
        .all()
    )
    items: list[dict[str, Any]] = []
    for ex, mg in rows:
        d = model_to_dict(ex)
        d["muscle_slug"] = mg.slug
        d["muscle_name_vi"] = mg.name_vi
        items.append(d)
    return PaginatedResponse.create(items, total, pagination.page, pagination.page_size)


@router.get("/exercises/{exercise_id}/equipment")
def admin_get_exercise_equipment(
    exercise_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    if not db.get(Exercise, exercise_id):
        raise NotFoundError("Exercise", exercise_id)
    rows = (
        db.query(ExerciseEquipment.equipment_id)
        .filter(ExerciseEquipment.exercise_id == exercise_id)
        .all()
    )
    return {"equipment_ids": [int(r[0]) for r in rows]}


@router.put("/exercises/{exercise_id}/equipment")
def admin_put_exercise_equipment(
    exercise_id: int,
    payload: EquipmentIdsIn,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    if not db.get(Exercise, exercise_id):
        raise NotFoundError("Exercise", exercise_id)
    ids = sorted({int(i) for i in payload.equipment_ids if int(i) > 0})
    if ids:
        found = {
            int(r[0])
            for r in db.query(Equipment.id).filter(Equipment.id.in_(ids)).all()
        }
        missing = [i for i in ids if i not in found]
        if missing:
            raise BadRequestError(f"Không tìm thấy equipment_id: {missing}")
    db.query(ExerciseEquipment).filter(ExerciseEquipment.exercise_id == exercise_id).delete()
    for eid in ids:
        db.add(ExerciseEquipment(exercise_id=exercise_id, equipment_id=eid))
    db.commit()
    return {"equipment_ids": ids}


class AdminFoodIn(BaseModel):
    name_vi: str = Field(min_length=1, max_length=200)
    name_en: str | None = None
    category_id: int | None = None
    serving_size: str = "100g"
    serving_grams: float = Field(default=100, gt=0)
    kcal_100g: float = Field(ge=0)
    protein_100g: float = Field(ge=0)
    carbs_100g: float = Field(ge=0)
    fat_100g: float = Field(ge=0)
    fiber_100g: float | None = Field(default=None, ge=0)
    sugar_100g: float | None = Field(default=None, ge=0)
    sodium_100mg: float | None = Field(default=None, ge=0)
    image_url: str | None = None
    is_common: bool = False
    prep_state: str | None = None
    status: str = "active"
    slug: str | None = Field(default=None, max_length=150)


class AdminFoodPatch(BaseModel):
    name_vi: str | None = Field(default=None, min_length=1, max_length=200)
    name_en: str | None = None
    category_id: int | None = None
    serving_size: str | None = None
    serving_grams: float | None = Field(default=None, gt=0)
    kcal_100g: float | None = Field(default=None, ge=0)
    protein_100g: float | None = Field(default=None, ge=0)
    carbs_100g: float | None = Field(default=None, ge=0)
    fat_100g: float | None = Field(default=None, ge=0)
    fiber_100g: float | None = Field(default=None, ge=0)
    sugar_100g: float | None = Field(default=None, ge=0)
    sodium_100mg: float | None = Field(default=None, ge=0)
    image_url: str | None = None
    is_common: bool | None = None
    prep_state: str | None = None
    status: str | None = None
    slug: str | None = Field(default=None, max_length=150)


@router.get("/foods")
def admin_list_foods(
    pagination: Annotated[PaginationParams, Depends()],
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
    q: str | None = Query(default=None),
    category_id: int | None = None,
    status: str | None = None,
):
    return AdminFoodService(db).list_admin(
        pagination, q=q, category_id=category_id, status=status
    )


@router.post("/foods", status_code=201)
def admin_create_food(
    payload: AdminFoodIn,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    return AdminFoodService(db).create(**payload.model_dump())


@router.patch("/foods/{food_id}")
def admin_update_food(
    food_id: int,
    payload: AdminFoodPatch,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    return AdminFoodService(db).update(food_id, payload.model_dump(exclude_unset=True))
