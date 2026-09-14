from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, get_current_user_optional
from app.services.calculator_service import CalculatorService

router = APIRouter(prefix="/calculators", tags=["Calculators"])


class TdeeInput(BaseModel):
    gender: Literal["male", "female"]
    weight_kg: float = Field(gt=0)
    height_cm: float = Field(gt=0)
    age: int = Field(ge=10, le=100)
    activity_level: Literal["sedentary", "light", "moderate", "active", "very_active"]
    goal: Literal["lose_weight", "maintain", "gain_muscle"] = "maintain"


class BmiInput(BaseModel):
    weight_kg: float = Field(gt=0)
    height_cm: float = Field(gt=0)


class MacrosInput(BaseModel):
    target_calories: int = Field(gt=800)
    weight_kg: float = Field(gt=0)
    goal: Literal["lose_weight", "maintain", "gain_muscle"] = "maintain"


@router.post("/bmi")
def calc_bmi(
    payload: BmiInput,
    db: Session = Depends(get_db),
    user: CurrentUser | None = Depends(get_current_user_optional),
):
    return CalculatorService(db).calculate_and_log("bmi", payload.model_dump(), user.id if user else None)


@router.post("/tdee")
def calc_tdee(payload: TdeeInput, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return CalculatorService(db).calculate_and_log("tdee", payload.model_dump(), user.id)


@router.post("/macros")
def calc_macros(payload: MacrosInput, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return CalculatorService(db).calculate_and_log("macros", payload.model_dump(), user.id)


@router.post("/full")
def calc_full(payload: TdeeInput, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return CalculatorService(db).calculate_and_log("full", payload.model_dump(), user.id)
