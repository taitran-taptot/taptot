from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.pagination import PaginationParams
from app.models.base import Base
from app.models.entities import Food, FoodCategory
from app.services.search_service import SearchService


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _cat(db: Session, slug: str, name: str, order: int = 0) -> FoodCategory:
    row = FoodCategory(slug=slug, name_vi=name, sort_order=order)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _food(
    db: Session,
    *,
    slug: str,
    name: str,
    category: FoodCategory | None,
    calories: float = 100,
    protein_g: float = 1,
    carbs_g: float = 1,
    fat_g: float = 1,
    tags: list[str] | None = None,
    food_kind: str = "ingredient",
    is_complete_meal: bool = False,
) -> Food:
    row = Food(
        slug=slug,
        name_vi=name,
        serving_size="100g",
        calories=calories,
        protein_g=protein_g,
        carbs_g=carbs_g,
        fat_g=fat_g,
        tags=tags or [],
        vitamins_json={},
        food_kind=food_kind,
        status="active",
        confidence="estimated",
        category_id=category.id if category else None,
        is_complete_meal=is_complete_meal,
        created_at=datetime.now(UTC),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _names(items) -> set[str]:
    return {row.name_vi for row in items}


def test_macro_role_uses_category_not_protein_grams():
    db = _session()
    meat = _cat(db, "thit-gia-cam-noi-tang", "Thịt")
    spice = _cat(db, "gia-vi-mam-dau", "Gia vị")
    snack = _cat(db, "an-vat-do-uong", "Ăn vặt")
    grain = _cat(db, "ngu-coc-hat", "Ngũ cốc")
    produce = _cat(db, "rau-cu-qua", "Rau củ")
    dish_cat = _cat(db, "mon-an-truyen-thong", "Món truyền thống")

    chicken = _food(db, slug="uc-ga", name="Ức gà", category=meat, protein_g=5, calories=110)
    nuoc_mam = _food(db, slug="nuoc-mam", name="Nước mắm", category=spice, protein_g=20, calories=30)
    banh = _food(db, slug="banh-quy", name="Bánh quy", category=snack, carbs_g=40, calories=400)
    rice = _food(db, slug="com", name="Cơm", category=grain, protein_g=2, carbs_g=28, calories=130)
    rau = _food(db, slug="rau-muong", name="Rau muống", category=produce, tags=["rau"], calories=20)
    chuoi = _food(db, slug="chuoi", name="Chuối", category=produce, tags=["trai-cay"], carbs_g=23, calories=89)
    cam = _food(
        db,
        slug="cam-sanh",
        name="Cam sành",
        category=produce,
        tags=["nhom:qua-thap-duong"],
        carbs_g=12,
        calories=47,
    )
    pho = _food(
        db,
        slug="pho-bo",
        name="Phở bò",
        category=dish_cat,
        food_kind="dish",
        is_complete_meal=True,
        calories=520,
        protein_g=28,
        carbs_g=68,
    )

    svc = SearchService(db)
    protein_items, protein_total = svc.search_foods(PaginationParams(), macro_role="protein")
    assert protein_total == 1
    assert _names(protein_items) == {"Ức gà"}
    assert chicken.id == protein_items[0].id

    carb_items, carb_total = svc.search_foods(PaginationParams(), macro_role="carb")
    assert carb_total == 1
    assert _names(carb_items) == {"Cơm"}
    assert rice.id == carb_items[0].id

    veg_items, veg_total = svc.search_foods(PaginationParams(), macro_role="produce")
    assert veg_total == 1
    assert _names(veg_items) == {"Rau muống"}
    assert rau.id == veg_items[0].id

    fruit_items, fruit_total = svc.search_foods(PaginationParams(), macro_role="fruit")
    assert fruit_total == 2
    assert _names(fruit_items) == {"Chuối", "Cam sành"}
    assert {chuoi.id, cam.id} == {row.id for row in fruit_items}

    dish_items, dish_total = svc.search_foods(PaginationParams(), macro_role="dish")
    assert dish_total == 1
    assert _names(dish_items) == {"Phở bò"}
    assert pho.id == dish_items[0].id

    picker_items, picker_total = svc.search_foods(PaginationParams(), macro_role="meal_picker")
    names = _names(picker_items)
    assert picker_total == 6
    assert names == {"Ức gà", "Cơm", "Rau muống", "Chuối", "Cam sành", "Phở bò"}
    assert nuoc_mam.name_vi not in names
    assert banh.name_vi not in names
