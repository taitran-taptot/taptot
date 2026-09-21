"""Meal templates + plan templates owned by the signed-in user."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.schemas.plans import (
    CreateMealTemplateRequest,
    MealTemplateOut,
    MealTemplateSummaryOut,
    PlanDetailOut,
    PlanSummaryOut,
)
from app.services.meal_template_service import MealTemplateService
from app.services.plan_service import PlanService

router = APIRouter(tags=["Meal Templates"])


class SaveAsTemplateRequest(BaseModel):
    title_vi: str | None = Field(default=None, max_length=255)


@router.get("/meal-templates", response_model=list[MealTemplateSummaryOut])
def list_meal_templates(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    return MealTemplateService(db).list_templates(user.id)


@router.post("/meal-templates", response_model=MealTemplateOut, status_code=201)
def create_meal_template(
    payload: CreateMealTemplateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return MealTemplateService(db).create_template(user.id, payload)


@router.get("/meal-templates/{template_id}", response_model=MealTemplateOut)
def get_meal_template(
    template_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return MealTemplateService(db).get_template(user.id, template_id)


@router.delete("/meal-templates/{template_id}", status_code=204)
def delete_meal_template(
    template_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    MealTemplateService(db).delete_template(user.id, template_id)


@router.get("/my-plans/templates", response_model=list[PlanSummaryOut])
def list_plan_templates(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Full workout+meal plan templates owned by the user."""
    return PlanService(db).list_templates(user.id)


@router.post("/my-plans/{plan_id}/save-as-template", response_model=PlanDetailOut, status_code=201)
def save_plan_as_template(
    plan_id: int,
    payload: SaveAsTemplateRequest | None = None,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    title = payload.title_vi if payload else None
    return PlanService(db).save_as_template(user.id, plan_id, title)
