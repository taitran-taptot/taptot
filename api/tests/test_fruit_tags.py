from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.migrations.ensures import ensure_fruit_tags
from app.models.base import Base
from app.models.entities import Food
from app.services.food_picker_roles import (
    food_has_fruit_tag,
    fruit_slugs_from_catalog_v2,
    fruit_slugs_from_items,
    with_fruit_tag,
)


def test_food_has_fruit_tag_needles():
    assert food_has_fruit_tag(["trai-cay", "an-vat"])
    assert food_has_fruit_tag(["nhom:qua"])
    assert food_has_fruit_tag(["nhom:qua-thap-duong"])
    assert food_has_fruit_tag(["nhom:trai-cay"])
    assert not food_has_fruit_tag(["rau"])
    assert not food_has_fruit_tag([])


def test_with_fruit_tag_is_idempotent():
    assert with_fruit_tag(["rau"]) == ["rau", "trai-cay"]
    assert with_fruit_tag(["trai-cay", "an-vat"]) == ["trai-cay", "an-vat"]


def test_fruit_slugs_from_catalog_items():
    slugs = fruit_slugs_from_items(
        [
            {"slug": "chuoi", "tags": ["trai-cay"]},
            {"slug": "rau-muong", "tags": ["rau"]},
            {"slug": "xoai", "tags": ["nhom:qua"]},
        ]
    )
    assert slugs == {"chuoi", "xoai"}


def test_catalog_v2_includes_banana():
    slugs = fruit_slugs_from_catalog_v2()
    assert "chuoi" in slugs


def test_ensure_fruit_tags_adds_canonical_tag():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as db:
        db.add(
            Food(
                slug="chuoi",
                name_vi="Chuối tiêu",
                serving_size="100g",
                calories=93,
                protein_g=1,
                carbs_g=20,
                fat_g=0.3,
                tags=[],
                vitamins_json={},
                food_kind="ingredient",
                status="active",
                confidence="reference",
                created_at=datetime.now(UTC),
            )
        )
        db.add(
            Food(
                slug="rau-muong",
                name_vi="Rau muống",
                serving_size="100g",
                calories=20,
                protein_g=2,
                carbs_g=3,
                fat_g=0.2,
                tags=["rau"],
                vitamins_json={},
                food_kind="ingredient",
                status="active",
                confidence="reference",
                created_at=datetime.now(UTC),
            )
        )
        db.commit()

    ensure_fruit_tags(engine)

    with SessionLocal() as db:
        banana = db.query(Food).filter(Food.slug == "chuoi").one()
        veg = db.query(Food).filter(Food.slug == "rau-muong").one()
        assert "trai-cay" in [str(t).lower() for t in (banana.tags or [])]
        assert "trai-cay" not in [str(t).lower() for t in (veg.tags or [])]
