from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin, require_admin_write, require_staff, require_staff_write
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.pagination import PaginatedResponse, PaginationParams
from app.models.entities import Equipment, Exercise, ExerciseEquipment, MuscleGroup
from app.schemas.auth import CreateStaffRequest, UserResponse
from app.services.admin_exercise_service import AdminExerciseService, exercise_to_dict
from app.services.admin_food_service import AdminFoodService
from app.services.admin_stats_service import AdminStatsService
from app.services.auth_service import AuthService

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats")
def admin_stats(
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
    year: int | None = Query(default=None, ge=2000, le=2100),
):
    return AdminStatsService(db).year_stats(year)


class EquipmentIdsIn(BaseModel):
    equipment_ids: list[int] = Field(default_factory=list)


@router.post("/staff", response_model=UserResponse, status_code=201)
def admin_create_staff(
    payload: CreateStaffRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin_write),
) -> UserResponse:
    user = AuthService(db).create_staff(
        payload.email, payload.password, payload.display_name, payload.role
    )
    return UserResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        email_verified=user.email_verified_at is not None,
    )


@router.get("/exercises")
def admin_list_exercises(
    pagination: Annotated[PaginationParams, Depends()],
    db: Session = Depends(get_db),
    user=Depends(require_staff),
    q: str | None = Query(default=None),
    muscle_group_id: int | None = None,
    movement_pattern: str | None = None,
    movement_role: str | None = None,
    venue: str | None = None,
    difficulty: int | None = None,
    is_active: bool | None = None,
    exercise_type: str | None = None,
    mine: bool = Query(default=False),
):
    query = (
        db.query(Exercise, MuscleGroup)
        .join(MuscleGroup, MuscleGroup.id == Exercise.muscle_group_id)
    )
    if mine:
        query = query.filter(Exercise.created_by == user.id)
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
        items.append(exercise_to_dict(ex, mg))
    return PaginatedResponse.create(items, total, pagination.page, pagination.page_size)


class AdminExerciseIn(BaseModel):
    name_vi: str = Field(min_length=1, max_length=200)
    name_en: str | None = None
    muscle_group_id: int
    exercise_type: str = "main"
    movement_role: str | None = None
    movement_pattern: str | None = None
    venue: str | None = None
    difficulty: int = 2
    notes_vi: str | None = None
    is_active: bool = True


class AdminExercisePatch(BaseModel):
    name_vi: str | None = Field(default=None, min_length=1, max_length=200)
    name_en: str | None = None
    muscle_group_id: int | None = None
    exercise_type: str | None = None
    movement_role: str | None = None
    movement_pattern: str | None = None
    venue: str | None = None
    difficulty: int | None = None
    notes_vi: str | None = None
    is_active: bool | None = None


@router.get("/exercises/{exercise_id}/equipment")
def admin_get_exercise_equipment(
    exercise_id: int,
    db: Session = Depends(get_db),
    _staff=Depends(require_staff),
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
    _staff=Depends(require_staff_write),
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


@router.post("/exercises", status_code=201)
def admin_create_exercise(
    payload: AdminExerciseIn,
    db: Session = Depends(get_db),
    user=Depends(require_staff_write),
):
    return AdminExerciseService(db).create(payload.model_dump(), created_by=user.id)


@router.patch("/exercises/{exercise_id}")
def admin_update_exercise(
    exercise_id: int,
    payload: AdminExercisePatch,
    db: Session = Depends(get_db),
    user=Depends(require_staff_write),
):
    return AdminExerciseService(db).update(
        exercise_id, payload.model_dump(exclude_unset=True), actor=user
    )


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
    user=Depends(require_staff),
    q: str | None = Query(default=None),
    category_id: int | None = None,
    status: str | None = None,
    mine: bool = Query(default=False),
):
    return AdminFoodService(db).list_admin(
        pagination,
        q=q,
        category_id=category_id,
        status=status,
        mine_user_id=user.id if mine else None,
    )


@router.post("/foods", status_code=201)
def admin_create_food(
    payload: AdminFoodIn,
    db: Session = Depends(get_db),
    user=Depends(require_staff_write),
):
    return AdminFoodService(db).create(**payload.model_dump(), created_by=user.id)


@router.patch("/foods/{food_id}")
def admin_update_food(
    food_id: int,
    payload: AdminFoodPatch,
    db: Session = Depends(get_db),
    user=Depends(require_staff_write),
):
    return AdminFoodService(db).update(
        food_id, payload.model_dump(exclude_unset=True), actor=user
    )
