"""Day-level meal templates backed by meal_plans / meal_plan_items."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.models.entities import Food, MealPlan, MealPlanItem
from app.schemas.plans import CreateMealTemplateRequest
from app.services.meal_constants import VALID_MEALS


class MealTemplateService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_templates(self, user_id: str) -> list[dict[str, Any]]:
        rows = (
            self.db.query(MealPlan)
            .filter(MealPlan.user_id == user_id)
            .order_by(MealPlan.created_at.desc())
            .all()
        )
        items_by_plan, foods = self._load_items_and_foods([r.id for r in rows])
        return [self._summary(r, items_by_plan.get(r.id, []), foods) for r in rows]

    def get_template(self, user_id: str, template_id: int) -> dict[str, Any]:
        plan = self._get_owned(user_id, template_id)
        return self._detail(plan)

    def create_template(self, user_id: str, payload: CreateMealTemplateRequest) -> dict[str, Any]:
        if not payload.items:
            raise BadRequestError("Template cần ít nhất 1 món ăn")
        now = datetime.now(UTC)
        notes = {
            str(k): str(v).strip()
            for k, v in (payload.meal_notes or {}).items()
            if v is not None and str(v).strip()
        }
        plan = MealPlan(
            user_id=user_id,
            title_vi=payload.title_vi.strip(),
            target_calories=payload.target_calories,
            target_date=None,
            source="manual",
            meal_notes_json=notes,
            created_at=now,
        )
        self.db.add(plan)
        self.db.flush()

        food_ids = {item.food_id for item in payload.items}
        found = {
            int(fid)
            for (fid,) in self.db.query(Food.id).filter(Food.id.in_(food_ids)).all()
        }
        for idx, item in enumerate(payload.items):
            if item.food_id not in found:
                raise BadRequestError(f"Unknown food_id: {item.food_id}")
            meal_type = item.meal_type if item.meal_type in VALID_MEALS else "lunch"
            self.db.add(
                MealPlanItem(
                    meal_plan_id=plan.id,
                    meal_type=meal_type,
                    food_id=item.food_id,
                    servings=item.servings,
                    sort_order=item.sort_order if item.sort_order is not None else idx,
                    notes_vi=item.notes_vi,
                )
            )
        self.db.commit()
        return self._detail(plan)

    def delete_template(self, user_id: str, template_id: int) -> None:
        plan = self._get_owned(user_id, template_id)
        self.db.delete(plan)
        self.db.commit()

    def _get_owned(self, user_id: str, template_id: int) -> MealPlan:
        plan = self.db.get(MealPlan, template_id)
        if not plan:
            raise NotFoundError("MealPlan", template_id)
        if str(plan.user_id) != str(user_id):
            raise ForbiddenError("Not your meal template")
        return plan

    def _load_items_and_foods(
        self, plan_ids: list[int]
    ) -> tuple[dict[int, list[MealPlanItem]], dict[int, Food]]:
        if not plan_ids:
            return {}, {}
        items = (
            self.db.query(MealPlanItem)
            .filter(MealPlanItem.meal_plan_id.in_(plan_ids))
            .all()
        )
        items_by_plan: dict[int, list[MealPlanItem]] = {}
        for item in items:
            items_by_plan.setdefault(item.meal_plan_id, []).append(item)
        food_ids = {item.food_id for item in items}
        foods: dict[int, Food] = {}
        if food_ids:
            foods = {f.id: f for f in self.db.query(Food).filter(Food.id.in_(food_ids)).all()}
        return items_by_plan, foods

    def _summary(
        self,
        plan: MealPlan,
        items: list[MealPlanItem],
        foods: dict[int, Food],
    ) -> dict[str, Any]:
        total = 0
        for item in items:
            food = foods.get(item.food_id)
            if food:
                total += int(round((food.calories or 0) * float(item.servings or 1)))
        return {
            "id": plan.id,
            "title_vi": plan.title_vi,
            "target_calories": plan.target_calories,
            "item_count": len(items),
            "total_calories": total,
            "created_at": plan.created_at,
        }

    def _detail(self, plan: MealPlan) -> dict[str, Any]:
        items = (
            self.db.query(MealPlanItem)
            .filter(MealPlanItem.meal_plan_id == plan.id)
            .order_by(MealPlanItem.sort_order.asc())
            .all()
        )
        food_ids = {item.food_id for item in items}
        foods: dict[int, Food] = {}
        if food_ids:
            foods = {f.id: f for f in self.db.query(Food).filter(Food.id.in_(food_ids)).all()}
        out_items = []
        total = 0
        for item in items:
            food = foods.get(item.food_id)
            servings = float(item.servings or 1)
            cal = int(round((food.calories or 0) * servings)) if food else 0
            total += cal
            out_items.append(
                {
                    "id": item.id,
                    "food_id": item.food_id,
                    "name_vi": food.name_vi if food else f"#{item.food_id}",
                    "meal_type": item.meal_type,
                    "servings": servings,
                    "calories": cal,
                    "protein_g": (food.protein_g * servings) if food and food.protein_g is not None else None,
                    "carbs_g": (food.carbs_g * servings) if food and food.carbs_g is not None else None,
                    "fat_g": (food.fat_g * servings) if food and food.fat_g is not None else None,
                    "serving_size": food.serving_size if food else None,
                    "serving_grams": food.serving_grams if food else None,
                    "sort_order": item.sort_order,
                    "notes_vi": getattr(item, "notes_vi", None),
                }
            )
        notes = plan.meal_notes_json if isinstance(plan.meal_notes_json, dict) else {}
        return {
            "id": plan.id,
            "title_vi": plan.title_vi,
            "target_calories": plan.target_calories,
            "meal_notes": {str(k): str(v) for k, v in notes.items()},
            "item_count": len(out_items),
            "total_calories": total,
            "created_at": plan.created_at,
            "items": out_items,
        }
