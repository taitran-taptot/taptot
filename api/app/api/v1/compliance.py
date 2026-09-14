"""Custom foods and trainer client management."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require_trainer
from app.services.custom_food_service import CustomFoodService
from app.services.trainer_client_service import TrainerClientService

router = APIRouter(tags=["Foods & Trainer clients"])


class CreateCustomFoodIn(BaseModel):
    name_vi: str = Field(min_length=1, max_length=200)
    serving_size: str = Field(default="1 phần", max_length=100)
    serving_grams: float | None = Field(default=None, ge=0, le=5000)
    calories: float = Field(ge=0, le=5000)
    protein_g: float = Field(ge=0, le=500)
    carbs_g: float = Field(ge=0, le=500)
    fat_g: float = Field(ge=0, le=500)
    category_id: int | None = None
    tags: list[str] = Field(default_factory=lambda: ["custom"])


class AddClientIn(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=120)
    goal: str | None = Field(default=None, max_length=40)
    gender: str | None = Field(default=None, max_length=20)
    age: int | None = Field(default=None, ge=10, le=100)
    height_cm: float | None = Field(default=None, ge=80, le=250)
    weight_kg: float | None = Field(default=None, ge=20, le=400)


class ClientInfoIn(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    goal: str | None = Field(default=None, max_length=40)
    gender: str | None = Field(default=None, max_length=20)
    age: int | None = Field(default=None, ge=10, le=100)
    height_cm: float | None = Field(default=None, ge=80, le=250)
    weight_kg: float | None = Field(default=None, ge=20, le=400)


@router.get("/my-foods")
def list_my_foods(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    return CustomFoodService(db).list_mine(user.id)


@router.post("/my-foods", status_code=201)
def create_my_food(
    payload: CreateCustomFoodIn,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return CustomFoodService(db).create(
        user.id,
        name_vi=payload.name_vi,
        serving_size=payload.serving_size,
        calories=payload.calories,
        protein_g=payload.protein_g,
        carbs_g=payload.carbs_g,
        fat_g=payload.fat_g,
        serving_grams=payload.serving_grams,
        category_id=payload.category_id,
        tags=payload.tags,
    )


@router.delete("/my-foods/{food_id}", status_code=204)
def delete_my_food(
    food_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    CustomFoodService(db).delete(user.id, food_id)


@router.get("/trainer/clients")
def list_trainer_clients(
    user: CurrentUser = Depends(require_trainer),
    db: Session = Depends(get_db),
) -> list[dict]:
    return TrainerClientService(db).list_clients(user.id)


@router.post("/trainer/clients", status_code=201)
def add_trainer_client(
    payload: AddClientIn,
    user: CurrentUser = Depends(require_trainer),
    db: Session = Depends(get_db),
) -> dict:
    return TrainerClientService(db).add_by_email(
        user.id,
        str(payload.email),
        client_info={
            "full_name": payload.full_name,
            "goal": payload.goal,
            "gender": payload.gender,
            "age": payload.age,
            "height_cm": payload.height_cm,
            "weight_kg": payload.weight_kg,
        },
    )


@router.patch("/trainer/clients/{client_id}")
def update_trainer_client_info(
    client_id: str,
    payload: ClientInfoIn,
    user: CurrentUser = Depends(require_trainer),
    db: Session = Depends(get_db),
) -> dict:
    return TrainerClientService(db).update_client_info(
        user.id,
        client_id,
        full_name=payload.full_name,
        goal=payload.goal,
        gender=payload.gender,
        age=payload.age,
        height_cm=payload.height_cm,
        weight_kg=payload.weight_kg,
    )


@router.delete("/trainer/clients/{client_id}", status_code=204)
def remove_trainer_client(
    client_id: str,
    user: CurrentUser = Depends(require_trainer),
    db: Session = Depends(get_db),
) -> None:
    TrainerClientService(db).remove(user.id, client_id)
