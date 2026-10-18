from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.migrations.ensures import ensure_fruit_tags
from app.models.base import Base
from app.models.entities import Food
from app.services.food_picker_roles import (
    food_has_fruit_tag,
    food_looks_like_fruit,
    fruit_slugs_from_catalog_v2,
    fruit_slugs_from_items,
    strip_fruit_place_name,
    with_fruit_tag,
)


def test_food_has_fruit_tag_needles():
    assert food_has_fruit_tag(["trai-cay", "an-vat"])
    assert food_has_fruit_tag(["nhom:qua"])
    assert food_has_fruit_tag(["nhom:qua-thap-duong"])
    assert food_has_fruit_tag(["nhom:trai-cay"])
    assert not food_has_fruit_tag(["rau"])
    assert not food_has_fruit_tag([])


def test_food_looks_like_fruit_from_excel_slugs():
    assert food_looks_like_fruit(slug="chuoi-tieu-chuoi-tay", tags=[])
    assert food_looks_like_fruit(slug="xoai-chin-cat-hoa-loc", tags=[])
    assert food_looks_like_fruit(slug="bo-sap", tags=[])
    assert not food_looks_like_fruit(slug="rau-muong", tags=["rau"])
    assert not food_looks_like_fruit(slug="ca-chua-thuong", tags=[])
    assert not food_looks_like_fruit(slug="dua-chuot-ta-dua-leo", tags=[])
    assert not food_looks_like_fruit(slug="ca-chua-bi-cherry", tags=[])


def test_strip_fruit_place_name():
    assert strip_fruit_place_name("Nho đỏ Ninh Thuận") == "Nho đỏ"
    assert strip_fruit_place_name("Vải thiều Lục Ngạn") == "Vải thiều"
    assert strip_fruit_place_name("Xoài chín (Cát Hòa Lộc)") == "Xoài chín"
    assert strip_fruit_place_name("Roi / Mận đỏ An Phước") == "Roi / Mận đỏ"
    assert strip_fruit_place_name("Vú sữa Lò Rèn") == "Vú sữa"
    assert strip_fruit_place_name("Bưởi da xanh / Năm Roi") == "Bưởi da xanh"
    assert strip_fruit_place_name("Chuối tiêu / Chuối tây") == "Chuối tiêu / Chuối tây"
    assert strip_fruit_place_name("Bơ sáp") == "Bơ sáp"


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
                name_vi="Chuối tiêu Lục Ngạn",
                serving_size="100g",
                calories=93,
                protein_g=1,
                carbs_g=20,
                fat_g=0.3,
                tags=[],
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
        assert banana.name_vi == "Chuối tiêu"
        assert "trai-cay" not in [str(t).lower() for t in (veg.tags or [])]
