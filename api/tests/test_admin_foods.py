"""Admin food catalog: 100g → serving sync, soft-hide, catalog-only."""

from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.pagination import PaginationParams
from app.models.base import Base
from app.models.entities import Food, FoodCategory, User
from app.services.admin_food_service import AdminFoodService
from app.services.search_service import SearchService


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _category(db: Session) -> FoodCategory:
    row = FoodCategory(slug="tinh-bot", name_vi="Tinh bột", sort_order=3)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_create_scales_serving_from_100g():
    db = _session()
    cat = _category(db)
    created = AdminFoodService(db).create(
        name_vi="Cơm trắng admin",
        category_id=cat.id,
        serving_size="1 chén cơm",
        serving_grams=150,
        kcal_100g=130,
        protein_100g=2.7,
        carbs_100g=28,
        fat_100g=0.3,
        is_common=True,
        prep_state="cooked",
    )
    assert created["calories"] == 195
    assert created["protein_g"] == 4.05
    assert created["carbs_g"] == 42
    assert created["kcal_100g"] == 130
    assert created["status"] == "active"
    assert created["slug"].startswith("com-trang")


def test_update_kcal_rescales_serving():
    db = _session()
    created = AdminFoodService(db).create(
        name_vi="Chuối",
        serving_grams=120,
        kcal_100g=89,
        protein_100g=1.1,
        carbs_100g=23,
        fat_100g=0.3,
    )
    updated = AdminFoodService(db).update(created["id"], {"kcal_100g": 100})
    assert updated["kcal_100g"] == 100
    assert updated["calories"] == 120
    assert updated["serving_grams"] == 120


def test_deprecate_hides_from_public_search():
    db = _session()
    created = AdminFoodService(db).create(
        name_vi="Món ẩn test",
        kcal_100g=50,
        protein_100g=1,
        carbs_100g=10,
        fat_100g=0,
    )
    food_id = created["id"]
    items, total = SearchService(db).search_foods(PaginationParams(), q="Món ẩn test")
    assert total == 1
    assert items[0].id == food_id

    AdminFoodService(db).update(food_id, {"status": "deprecated"})
    _, hidden_total = SearchService(db).search_foods(PaginationParams(), q="Món ẩn test")
    assert hidden_total == 0

    listed = AdminFoodService(db).list_admin(PaginationParams(), status="deprecated")
    assert listed.total == 1
    assert listed.items[0]["id"] == food_id

    AdminFoodService(db).update(food_id, {"status": "active"})
    _, restored = SearchService(db).search_foods(PaginationParams(), q="Món ẩn test")
    assert restored == 1


def test_list_admin_skips_custom_user_foods():
    db = _session()
    AdminFoodService(db).create(
        name_vi="Catalog gà",
        kcal_100g=110,
        protein_100g=23,
        carbs_100g=0,
        fat_100g=1,
    )
    db.add(
        User(
            id="11111111-1111-1111-1111-111111111111",
            email="u@test.com",
            password_hash="x",
            display_name="U",
            role="user",
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    db.add(
        Food(
            slug="u-custom-ga",
            name_vi="Gà nhà làm",
            serving_size="1 phần",
            calories=200,
            protein_g=20,
            carbs_g=0,
            fat_g=10,
            is_verified=False,
            is_common=False,
            tags=["custom"],
            vitamins_json={},
            owner_user_id="11111111-1111-1111-1111-111111111111",
            food_kind="dish",
            status="active",
            confidence="estimated",
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    listed = AdminFoodService(db).list_admin(PaginationParams())
    names = [i["name_vi"] for i in listed.items]
    assert names == ["Catalog gà"]
