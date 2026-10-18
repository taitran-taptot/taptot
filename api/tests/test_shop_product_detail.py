"""Public product detail by slug + admin usage/gallery fields."""

from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.base import Base
from app.models.entities import ShopProduct
from app.services.shop_service import ShopService


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _kit(db: Session) -> ShopProduct:
    now = datetime.now(UTC)
    row = ShopProduct(
        slug="dumbbell",
        name_vi="Tạ đơn",
        description_vi="Mô tả",
        usage_vi=None,
        gallery_json=None,
        price_vnd=500000,
        stock_qty=5,
        image_url="equipment/dumbbell/tadon.png",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_get_product_by_slug_includes_usage_and_gallery():
    db = _db()
    row = _kit(db)
    service = ShopService(db)
    service.update_product(
        row.id,
        {
            "usage_vi": "Chọn tạ vừa sức.",
            "gallery_urls": ["equipment/dumbbell/2.png", "equipment/dumbbell/2.png"],
            "youtube_url": "https://www.youtube.com/watch?v=EngW7tLk6R8",
        },
    )
    got = service.get_product_by_slug("ta-don")
    assert got["usage_vi"] == "Chọn tạ vừa sức."
    assert got["gallery_urls"] == ["equipment/dumbbell/2.png"]
    assert got["youtube_url"] == "https://www.youtube.com/watch?v=EngW7tLk6R8"
    assert got["description_vi"] == "Mô tả"
    assert service.get_product_by_slug("dumbbell")["id"] == row.id


def test_inactive_hidden_unless_admin_flag():
    db = _db()
    row = _kit(db)
    ShopService(db).update_product(row.id, {"is_active": False})
    try:
        ShopService(db).get_product_by_slug("dumbbell")
        assert False, "expected 404"
    except NotFoundError:
        pass
    got = ShopService(db).get_product_by_slug("dumbbell", include_inactive=True)
    assert got["id"] == row.id


def test_product_crud_then_delete_non_canonical():
    db = _db()
    service = ShopService(db)
    created = service.create_product(
        {
            "name_vi": "SP test CRUD",
            "slug": "sp-test-crud",
            "description_vi": "Mô tả test",
            "usage_vi": "Cách dùng test",
            "price_vnd": 1000,
            "stock_qty": 2,
        }
    )
    pid = created["id"]
    assert service.get_product_by_slug("sp-test-crud")["name_vi"] == "SP test CRUD"
    updated = service.update_product(pid, {"description_vi": "Mô tả đã sửa", "stock_qty": 9})
    assert updated["description_vi"] == "Mô tả đã sửa"
    assert updated["stock_qty"] == 9
    service.delete_product(pid)
    try:
        service.get_product_by_slug("sp-test-crud")
        assert False, "expected 404 after delete"
    except NotFoundError:
        pass
    kit = _kit(db)
    service.update_product(kit.id, {"slug": "ta-don"})
    try:
        service.delete_product(kit.id)
        assert False, "canonical kit must not delete"
    except BadRequestError:
        pass
