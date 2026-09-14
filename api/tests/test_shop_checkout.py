"""Shop checkout: decrement stock, 409 when short, cancel restores stock."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.exceptions import BadRequestError, ConflictError
from app.models.base import Base
from app.models.entities import ShopCartItem, ShopProduct, User
from app.services.shop_service import ShopService


USER_ID = "11111111-1111-1111-1111-111111111111"


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(
        User(
            id=USER_ID,
            email="u@test.com",
            password_hash="x",
            display_name="U",
            role="user",
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    return db


def _product(db: Session, *, stock: int, name: str = "Tạ tay", price: int = 100000) -> ShopProduct:
    now = datetime.now(UTC)
    row = ShopProduct(
        slug=f"ta-tay-{stock}-{price}",
        name_vi=name,
        description_vi=None,
        price_vnd=price,
        stock_qty=stock,
        image_url=None,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_checkout_decrements_stock_and_clears_cart():
    db = _session()
    product = _product(db, stock=5)
    service = ShopService(db)
    service.add_to_cart(USER_ID, product.id, 2)
    order = service.checkout(USER_ID)
    db.refresh(product)
    assert order["order_status"] == "placed"
    assert order["total_vnd"] == 200000
    assert product.stock_qty == 3
    assert service.get_cart(USER_ID)["items"] == []
    assert len(order["items"]) == 1
    assert order["items"][0]["quantity"] == 2


def test_checkout_409_when_stock_insufficient():
    db = _session()
    product = _product(db, stock=1)
    db.add(ShopCartItem(user_id=USER_ID, product_id=product.id, quantity=3))
    db.commit()
    with pytest.raises(ConflictError):
        ShopService(db).checkout(USER_ID)
    db.refresh(product)
    assert product.stock_qty == 1


def test_cancel_order_restores_stock():
    db = _session()
    product = _product(db, stock=4)
    service = ShopService(db)
    service.add_to_cart(USER_ID, product.id, 3)
    order = service.checkout(USER_ID)
    db.refresh(product)
    assert product.stock_qty == 1
    cancelled = service.cancel_order(order["id"])
    db.refresh(product)
    assert cancelled["order_status"] == "cancelled"
    assert product.stock_qty == 4


def test_cancel_twice_is_rejected():
    db = _session()
    product = _product(db, stock=2)
    service = ShopService(db)
    service.add_to_cart(USER_ID, product.id, 1)
    order = service.checkout(USER_ID)
    service.cancel_order(order["id"])
    with pytest.raises(BadRequestError):
        service.cancel_order(order["id"])


def test_add_to_cart_rejects_more_than_stock():
    db = _session()
    product = _product(db, stock=1)
    service = ShopService(db)
    service.add_to_cart(USER_ID, product.id, 1)
    with pytest.raises(ConflictError):
        service.add_to_cart(USER_ID, product.id, 1)
