from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.models.entities import Food, FoodCategory
from app.services.food_catalog_perfect_import import PerfectFoodRow, apply_perfect_catalog


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _row(**kwargs) -> PerfectFoodRow:
    base = dict(
        id=None,
        slug="bi-ngoi-xanh-zucchini",
        name_vi="Bí ngòi xanh",
        name_en="Zucchini",
        group_name="Rau - Củ - Quả",
        food_kind="ingredient",
        prep_state="raw",
        serving_size="100g",
        serving_grams=100,
        calories=17,
        protein_g=1.2,
        carbs_g=3.1,
        fat_g=0.3,
        kcal_100g=17,
        protein_100g=1.2,
        carbs_100g=3.1,
        fat_100g=0.3,
        yield_factor=None,
        is_verified=True,
        ai_eligible=True,
        default_for_ai=False,
        aliases=["zucchini"],
        source_ref="test",
    )
    base.update(kwargs)
    return PerfectFoodRow(**base)


def test_apply_perfect_catalog_inserts_missing_ingredient():
    db = _session()
    cat = FoodCategory(slug="rau-cu-qua", name_vi="Rau - Củ - Quả", sort_order=1)
    db.add(cat)
    db.commit()
    stats = apply_perfect_catalog(db, [_row()])
    assert stats.created == 1
    food = db.query(Food).filter(Food.slug == "bi-ngoi-xanh-zucchini").one()
    assert food.name_vi == "Bí ngòi xanh"
    assert food.kcal_100g == 17
    assert food.status == "active"
    assert food.category_id == cat.id
    assert food.macro_roles == ["produce"]
