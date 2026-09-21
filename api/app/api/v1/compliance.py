"""Custom foods for the signed-in user."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.services.custom_food_service import CustomFoodService

router = APIRouter(tags=["Foods"])


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
