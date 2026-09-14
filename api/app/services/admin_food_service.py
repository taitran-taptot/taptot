"""Admin CRUD for public food catalog (owner_user_id is null)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.pagination import PaginatedResponse, PaginationParams
from app.models.entities import Food, FoodCategory
from app.services.slug import unique_slug

PREP_STATES = frozenset({"raw", "cooked", "dry"})
STATUSES = frozenset({"active", "deprecated"})


def _now() -> datetime:
    return datetime.now(UTC)


def _scale(value: float | None, grams: float) -> float | None:
    if value is None:
        return None
    return round(float(value) * grams / 100.0, 4)


def food_to_dict(row: Food) -> dict[str, Any]:
    return {
        "id": row.id,
        "slug": row.slug,
        "name_vi": row.name_vi,
        "name_en": row.name_en,
        "category_id": row.category_id,
        "serving_size": row.serving_size,
        "serving_grams": row.serving_grams,
        "calories": row.calories,
        "protein_g": row.protein_g,
        "carbs_g": row.carbs_g,
        "fat_g": row.fat_g,
        "fiber_g": row.fiber_g,
        "sugar_g": row.sugar_g,
        "sodium_mg": row.sodium_mg,
        "kcal_100g": row.kcal_100g,
        "protein_100g": row.protein_100g,
        "carbs_100g": row.carbs_100g,
        "fat_100g": row.fat_100g,
        "fiber_100g": row.fiber_100g,
        "sugar_100g": row.sugar_100g,
        "sodium_100mg": row.sodium_100mg,
        "image_url": row.image_url,
        "is_common": bool(row.is_common),
        "prep_state": row.prep_state,
        "status": row.status,
        "food_kind": row.food_kind,
        "region_slug": getattr(row, "region_slug", None),
        "province_id": getattr(row, "province_id", None),
        "description_vi": getattr(row, "description_vi", None),
    }


class AdminFoodService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _catalog_query(self):
        return self.db.query(Food).filter(Food.owner_user_id.is_(None))

    def _get_catalog(self, food_id: int) -> Food:
        row = self._catalog_query().filter(Food.id == food_id).first()
        if not row:
            raise NotFoundError("Food", food_id)
        return row

    def _assert_category(self, category_id: int | None) -> None:
        if category_id is None:
            return
        if not self.db.get(FoodCategory, category_id):
            raise BadRequestError(f"Không tìm thấy quầy category_id={category_id}")

    def _assert_prep(self, prep_state: str | None) -> str | None:
        if prep_state is None or prep_state == "":
            return None
        key = prep_state.strip().lower()
        if key not in PREP_STATES:
            raise BadRequestError("prep_state phải là raw, cooked hoặc dry")
        return key

    def _assert_status(self, status: str) -> str:
        key = (status or "active").strip().lower()
        if key not in STATUSES:
            raise BadRequestError("status phải là active hoặc deprecated")
        return key

    def _apply_macros_from_100g(
        self,
        food: Food,
        *,
        kcal_100g: float,
        protein_100g: float,
        carbs_100g: float,
        fat_100g: float,
        fiber_100g: float | None,
        sugar_100g: float | None,
        sodium_100mg: float | None,
        serving_grams: float,
    ) -> None:
        grams = float(serving_grams)
        if grams <= 0:
            raise BadRequestError("serving_grams phải > 0")
        food.kcal_100g = float(kcal_100g)
        food.protein_100g = float(protein_100g)
        food.carbs_100g = float(carbs_100g)
        food.fat_100g = float(fat_100g)
        food.fiber_100g = None if fiber_100g is None else float(fiber_100g)
        food.sugar_100g = None if sugar_100g is None else float(sugar_100g)
        food.sodium_100mg = None if sodium_100mg is None else float(sodium_100mg)
        food.serving_grams = grams
        food.calories = float(_scale(kcal_100g, grams) or 0)
        food.protein_g = float(_scale(protein_100g, grams) or 0)
        food.carbs_g = float(_scale(carbs_100g, grams) or 0)
        food.fat_g = float(_scale(fat_100g, grams) or 0)
        food.fiber_g = _scale(food.fiber_100g, grams)
        food.sugar_g = _scale(food.sugar_100g, grams)
        food.sodium_mg = _scale(food.sodium_100mg, grams)

    def list_admin(
        self,
        pagination: PaginationParams,
        *,
        q: str | None = None,
        category_id: int | None = None,
        status: str | None = None,
    ) -> PaginatedResponse[dict]:
        query = self._catalog_query()
        if q and q.strip():
            term = f"%{q.strip()}%"
            query = query.filter((Food.name_vi.ilike(term)) | (Food.slug.ilike(term)))
        if category_id is not None:
            query = query.filter(Food.category_id == category_id)
        if status and status.strip():
            query = query.filter(Food.status == self._assert_status(status))
        total = query.count()
        rows = (
            query.order_by(Food.name_vi.asc(), Food.id.asc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
            .all()
        )
        return PaginatedResponse.create(
            [food_to_dict(r) for r in rows],
            total,
            pagination.page,
            pagination.page_size,
        )

    def create(
        self,
        *,
        name_vi: str,
        kcal_100g: float,
        protein_100g: float,
        carbs_100g: float,
        fat_100g: float,
        name_en: str | None = None,
        category_id: int | None = None,
        serving_size: str = "100g",
        serving_grams: float = 100,
        fiber_100g: float | None = None,
        sugar_100g: float | None = None,
        sodium_100mg: float | None = None,
        image_url: str | None = None,
        is_common: bool = False,
        prep_state: str | None = None,
        status: str = "active",
        slug: str | None = None,
    ) -> dict:
        name = name_vi.strip()
        if not name:
            raise BadRequestError("Tên món không được trống")
        self._assert_category(category_id)
        row = Food(
            slug=unique_slug(self.db, Food, (slug or name), fallback="thuc-pham"),
            name_vi=name,
            name_en=(name_en.strip() if name_en and name_en.strip() else None),
            category_id=category_id,
            serving_size=(serving_size or "").strip() or "100g",
            is_verified=True,
            is_common=bool(is_common),
            tags=[],
            vitamins_json={},
            image_url=(image_url.strip() if image_url and image_url.strip() else None),
            owner_user_id=None,
            food_kind="ingredient",
            prep_state=self._assert_prep(prep_state),
            status=self._assert_status(status),
            confidence="estimated",
            macro_roles=[],
            meal_slots=[],
            ai_eligible=True,
            ai_priority=0,
            created_at=_now(),
        )
        self._apply_macros_from_100g(
            row,
            kcal_100g=kcal_100g,
            protein_100g=protein_100g,
            carbs_100g=carbs_100g,
            fat_100g=fat_100g,
            fiber_100g=fiber_100g,
            sugar_100g=sugar_100g,
            sodium_100mg=sodium_100mg,
            serving_grams=serving_grams,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return food_to_dict(row)

    def update(self, food_id: int, data: dict[str, Any]) -> dict:
        row = self._get_catalog(food_id)
        if "name_vi" in data and data["name_vi"] is not None:
            name = str(data["name_vi"]).strip()
            if not name:
                raise BadRequestError("Tên món không được trống")
            row.name_vi = name
        if "name_en" in data:
            en = data["name_en"]
            row.name_en = en.strip() if isinstance(en, str) and en.strip() else None
        if "category_id" in data:
            self._assert_category(data["category_id"])
            row.category_id = data["category_id"]
        if "serving_size" in data and data["serving_size"] is not None:
            row.serving_size = str(data["serving_size"]).strip() or row.serving_size
        if "image_url" in data:
            url = data["image_url"]
            row.image_url = url.strip() if isinstance(url, str) and url.strip() else None
        if "is_common" in data and data["is_common"] is not None:
            row.is_common = bool(data["is_common"])
        if "prep_state" in data:
            row.prep_state = self._assert_prep(data["prep_state"])
        if "status" in data and data["status"] is not None:
            row.status = self._assert_status(str(data["status"]))
        if "slug" in data and data["slug"]:
            row.slug = unique_slug(
                self.db, Food, str(data["slug"]), exclude_id=row.id, fallback="thuc-pham"
            )

        macro_keys = (
            "kcal_100g",
            "protein_100g",
            "carbs_100g",
            "fat_100g",
            "fiber_100g",
            "sugar_100g",
            "sodium_100mg",
            "serving_grams",
        )
        if any(k in data for k in macro_keys):
            grams = data["serving_grams"] if "serving_grams" in data else row.serving_grams
            self._apply_macros_from_100g(
                row,
                kcal_100g=data["kcal_100g"] if "kcal_100g" in data else (row.kcal_100g or 0),
                protein_100g=data["protein_100g"] if "protein_100g" in data else (row.protein_100g or 0),
                carbs_100g=data["carbs_100g"] if "carbs_100g" in data else (row.carbs_100g or 0),
                fat_100g=data["fat_100g"] if "fat_100g" in data else (row.fat_100g or 0),
                fiber_100g=data["fiber_100g"] if "fiber_100g" in data else row.fiber_100g,
                sugar_100g=data["sugar_100g"] if "sugar_100g" in data else row.sugar_100g,
                sodium_100mg=data["sodium_100mg"] if "sodium_100mg" in data else row.sodium_100mg,
                serving_grams=float(grams or 100),
            )

        self.db.commit()
        self.db.refresh(row)
        return food_to_dict(row)
