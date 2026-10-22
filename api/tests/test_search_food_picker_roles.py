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

    fish = _cat(db, "ca-thuy-hai-san", "Cá")
    _food(db, slug="ca-thu", name="Cá thu", category=fish, protein_g=22, calories=150)
    meat_only, meat_total = svc.search_foods(
        PaginationParams(), macro_role="protein", category_slug="thit-gia-cam-noi-tang"
    )
    assert meat_total == 1
    assert _names(meat_only) == {"Ức gà"}
    fish_only, fish_total = svc.search_foods(
        PaginationParams(), macro_role="protein", category_slug="ca-thuy-hai-san"
    )
    assert fish_total == 1
    assert _names(fish_only) == {"Cá thu"}


def test_protein_picker_sorts_meat_then_seafood_then_egg():
    db = _session()
    meat = _cat(db, "thit-gia-cam-noi-tang", "Thịt", order=2)
    fish = _cat(db, "ca-thuy-hai-san", "Cá", order=3)
    egg = _cat(db, "trung-whey", "Trứng", order=4)
    _food(db, slug="uc-ga", name="Ức gà", category=meat)
    _food(db, slug="ca-thu", name="Cá thu", category=fish)
    _food(db, slug="trung-ga", name="Trứng gà", category=egg)

    svc = SearchService(db)
    items, total = svc.search_foods(PaginationParams(), macro_role="protein")
    assert total == 3
    assert [row.name_vi for row in items] == ["Ức gà", "Cá thu", "Trứng gà"]


def test_salted_egg_is_not_in_meat_chip():
    db = _session()
    meat = _cat(db, "thit-gia-cam-noi-tang", "Thịt", order=2)
    egg = _cat(db, "trung-whey", "Trứng", order=4)
    _food(db, slug="uc-ga", name="Ức gà", category=meat)
    _food(db, slug="trung-muoi", name="Trứng muối", category=egg)

    svc = SearchService(db)
    meat_only, meat_total = svc.search_foods(
        PaginationParams(), macro_role="protein", category_slug="thit-gia-cam-noi-tang"
    )
    egg_only, egg_total = svc.search_foods(
        PaginationParams(), macro_role="protein", category_slug="trung-whey"
    )
    assert meat_total == 1
    assert _names(meat_only) == {"Ức gà"}
    assert egg_total == 1
    assert _names(egg_only) == {"Trứng muối"}


def test_carb_picker_hides_flours_wrappers_and_tofu():
    db = _session()
    grain = _cat(db, "ngu-coc-hat", "Ngũ cốc")
    _food(db, slug="com", name="Cơm", category=grain, carbs_g=28)
    _food(db, slug="bot-nang", name="Bột năng", category=grain, carbs_g=88)
    _food(db, slug="bot-gao", name="Bột gạo", category=grain, carbs_g=80)
    _food(db, slug="dau-phu-chac", name="Đậu phụ chắc", category=grain, protein_g=12)
    _food(db, slug="dau-hu-non", name="Đậu hũ non", category=grain, protein_g=8)
    _food(db, slug="banh-hoi", name="Bánh hỏi", category=grain, carbs_g=25)
    _food(db, slug="banh-trang", name="Bánh tráng", category=grain, carbs_g=80)

    svc = SearchService(db)
    carb_names = _names(svc.search_foods(PaginationParams(), macro_role="carb")[0])
    picker_names = _names(svc.search_foods(PaginationParams(), macro_role="meal_picker")[0])
    assert carb_names == {"Cơm"}
    assert picker_names == {"Cơm"}
    catalog_names = _names(svc.search_foods(PaginationParams())[0])
    assert catalog_names == {
        "Cơm",
        "Bột năng",
        "Bột gạo",
        "Đậu phụ chắc",
        "Đậu hũ non",
        "Bánh hỏi",
        "Bánh tráng",
    }


def test_meal_picker_hides_ai_ineligible_but_plain_search_keeps_them():
    db = _session()
    grain = _cat(db, "ngu-coc-hat", "Ngũ cốc")
    bun = _food(db, slug="bun-tuoi", name="Bún tươi", category=grain, carbs_g=22)
    flour = _food(db, slug="bot-gao", name="Bột gạo", category=grain, carbs_g=80)
    flour.ai_eligible = False
    db.commit()

    svc = SearchService(db)
    picker, picker_total = svc.search_foods(PaginationParams(), macro_role="meal_picker")
    assert picker_total == 1
    assert _names(picker) == {"Bún tươi"}
    assert bun.id == picker[0].id

    all_items, all_total = svc.search_foods(PaginationParams())
    assert all_total == 2
    assert _names(all_items) == {"Bún tươi", "Bột gạo"}
    assert flour.id in {row.id for row in all_items}


def test_meat_picker_keeps_lean_cuts_and_catalog_keeps_offal():
    db = _session()
    meat = _cat(db, "thit-gia-cam-noi-tang", "Thịt")
    breast = _food(db, slug="uc-ga-khong-da", name="Ức gà không da", category=meat, protein_g=23)
    loin = _food(db, slug="than-noi-heo-than-chuot", name="Thăn nội heo", category=meat, protein_g=21)
    shoulder = _food(db, slug="nac-vai-heo-nac-vai-dau-gion", name="Nạc vai heo", category=meat, protein_g=20)
    liver = _food(db, slug="gan-heo", name="Gan heo", category=meat, protein_g=21)
    liver.ai_eligible = False
    offal = _food(db, slug="long-heo", name="Lòng heo", category=meat, protein_g=18)
    offal.ai_eligible = False
    bone = _food(db, slug="xuong-ong-bo-chua-tuy-vang", name="Xương ống bò", category=meat, protein_g=12)
    bone.ai_eligible = False
    db.commit()

    svc = SearchService(db)
    picker = _names(
        svc.search_foods(
            PaginationParams(),
            macro_role="protein",
            category_slug="thit-gia-cam-noi-tang",
        )[0]
    )
    assert picker == {"Ức gà không da", "Thăn nội heo", "Nạc vai heo"}
    assert {breast.id, loin.id, shoulder.id} == {
        row.id
        for row in svc.search_foods(
            PaginationParams(),
            macro_role="protein",
            category_slug="thit-gia-cam-noi-tang",
        )[0]
    }
    catalog = _names(svc.search_foods(PaginationParams())[0])
    assert {"Gan heo", "Lòng heo", "Xương ống bò"} <= catalog


def test_lean_meat_stays_eligible_and_offal_does_not():
    from app.core.migrations.ensures import _ai_meal_ineligible

    assert _ai_meal_ineligible("uc-ga-khong-da", "rau-cu-qua") is False
    assert _ai_meal_ineligible("than-noi-heo-than-chuot", "rau-cu-qua") is False
    assert _ai_meal_ineligible("nac-vai-heo-nac-vai-dau-gion", "thit-gia-cam-noi-tang") is False
    assert _ai_meal_ineligible("gan-heo", "thit-gia-cam-noi-tang") is True
    assert _ai_meal_ineligible("long-heo", "rau-cu-qua") is True
    assert _ai_meal_ineligible("xuong-ong-bo-chua-tuy-vang", "rau-cu-qua") is True
    assert _ai_meal_ineligible("thit-lon-ba-chi-song", "rau-cu-qua") is True
    assert _ai_meal_ineligible("suon-que-suon-cong-cat-khuc", "thit-gia-cam-noi-tang") is True
    assert _ai_meal_ineligible("ba-chi-ba-roi-thuong", "thit-gia-cam-noi-tang") is False
    assert _ai_meal_ineligible("canh-ga-nguyen-chiec-canh-tien", "thit-gia-cam-noi-tang") is False
    assert _ai_meal_ineligible("suon-lon-song", "thit-gia-cam-noi-tang") is False
    assert _ai_meal_ineligible("gau-mem-bo", "thit-gia-cam-noi-tang") is False
    assert _ai_meal_ineligible("bo-to-cu-chi-thit-be-bo-non-tuoi", "thit-gia-cam-noi-tang") is False


def test_potato_and_corn_are_starch_chips_not_vegetables():
    db = _session()
    grain = _cat(db, "ngu-coc-hat", "Ngũ cốc")
    produce = _cat(db, "rau-cu-qua", "Rau củ")
    _food(db, slug="com", name="Cơm", category=grain, carbs_g=28)
    _food(db, slug="khoai-lang", name="Khoai lang luộc", category=produce, carbs_g=20, tags=["rau", "carb"])
    _food(db, slug="khoai-lang-song", name="Khoai lang", category=produce, carbs_g=17.1, tags=["carb"])
    _food(db, slug="bap-ngot", name="Bắp ngọt", category=produce, carbs_g=19, tags=["produce", "carb"])
    _food(db, slug="cai-bap", name="Cải bắp", category=produce, tags=["rau"])
    _food(db, slug="rau-muong", name="Rau muống", category=produce, tags=["rau"])

    svc = SearchService(db)
    carb_names = _names(svc.search_foods(PaginationParams(), macro_role="carb")[0])
    veg_names = _names(svc.search_foods(PaginationParams(), macro_role="produce")[0])
    assert "Cơm" in carb_names
    assert "Khoai lang luộc" in carb_names
    assert "Khoai lang" in carb_names
    assert "Bắp ngọt" in carb_names
    assert "Cải bắp" not in carb_names
    assert "Khoai lang luộc" not in veg_names
    assert "Khoai lang" not in veg_names
    assert "Bắp ngọt" not in veg_names
    assert veg_names == {"Cải bắp", "Rau muống"}
