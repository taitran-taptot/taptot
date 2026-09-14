"""User-owned custom foods (stored in foods.owner_user_id)."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.models.entities import Food


def _slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s[:80] or "mon-an"


class CustomFoodService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_mine(self, user_id: str) -> list[dict[str, Any]]:
        rows = (
            self.db.query(Food)
            .filter(Food.owner_user_id == user_id)
            .order_by(Food.created_at.desc())
            .all()
        )
        return [self._to_dict(r) for r in rows]

    def create(
        self,
        user_id: str,
        *,
        name_vi: str,
        serving_size: str,
        calories: float,
        protein_g: float,
        carbs_g: float,
        fat_g: float,
        serving_grams: float | None = None,
        category_id: int | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        name = name_vi.strip()
        if not name:
            raise BadRequestError("Tên món không được trống")
        base = _slugify(name)
        slug = f"u-{user_id[:8]}-{base}"
        # ensure unique
        n = 1
        while self.db.query(Food).filter(Food.slug == slug).first():
            n += 1
            slug = f"u-{user_id[:8]}-{base}-{n}"

        food = Food(
            slug=slug,
            name_vi=name,
            name_en=None,
            category_id=category_id,
            serving_size=serving_size.strip() or "1 phần",
            serving_grams=serving_grams,
            calories=float(calories),
            protein_g=float(protein_g),
            carbs_g=float(carbs_g),
            fat_g=float(fat_g),
            fiber_g=None,
            sugar_g=None,
            sodium_mg=None,
            is_verified=False,
            is_common=False,
            tags=list(tags or ["custom"]),
            vitamins_json={},
            image_url=None,
            owner_user_id=user_id,
            food_kind="dish",
            prep_state=None,
            status="active",
            confidence="estimated",
            source_ref="user-custom",
            created_at=datetime.now(UTC),
        )
        if serving_grams and serving_grams > 0:
            scale = 100.0 / float(serving_grams)
            food.kcal_100g = float(calories) * scale
            food.protein_100g = float(protein_g) * scale
            food.carbs_100g = float(carbs_g) * scale
            food.fat_100g = float(fat_g) * scale
        self.db.add(food)
        self.db.commit()
        self.db.refresh(food)
        if serving_grams and serving_grams > 0:
            from app.models.entities import FoodPortion

            self.db.add(
                FoodPortion(
                    food_id=food.id,
                    label_vi=food.serving_size,
                    grams=float(serving_grams),
                    is_default=True,
                    sort_order=0,
                )
            )
            self.db.commit()
        return self._to_dict(food)

    def delete(self, user_id: str, food_id: int) -> None:
        food = self.db.get(Food, food_id)
        if not food or food.owner_user_id is None:
            raise NotFoundError("Food", food_id)
        if str(food.owner_user_id) != str(user_id):
            raise ForbiddenError("Not your custom food")
        self.db.delete(food)
        self.db.commit()

    def _to_dict(self, food: Food) -> dict[str, Any]:
        return {
            "id": food.id,
            "slug": food.slug,
            "name_vi": food.name_vi,
            "name_en": food.name_en,
            "category_id": food.category_id,
            "serving_size": food.serving_size,
            "serving_grams": food.serving_grams,
            "calories": food.calories,
            "protein_g": food.protein_g,
            "carbs_g": food.carbs_g,
            "fat_g": food.fat_g,
            "fiber_g": food.fiber_g,
            "sugar_g": food.sugar_g,
            "sodium_mg": food.sodium_mg,
            "is_verified": food.is_verified,
            "is_common": food.is_common,
            "tags": food.tags or [],
            "image_url": food.image_url,
            "owner_user_id": str(food.owner_user_id) if food.owner_user_id else None,
            "is_custom": True,
            "created_at": food.created_at,
        }
