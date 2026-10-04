"""Shop checkout: decrement stock, 409 when short, cancel restores stock."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.exceptions import BadRequestError, ConflictError
from app.core.pagination import PaginationParams
from app.models.base import Base
from app.models.entities import ProductRedeemCode, ShopCartItem, ShopOrder, ShopProduct, User, UserDailyPlan
from app.services.pushup_challenge import finish_session, start_session
from app.services.redeem_code_service import RedeemCodeService
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
    assert order["order_status"] == "awaiting_confirm"
    assert order["total_vnd"] == 200000
    assert product.stock_qty == 3
    assert service.get_cart(USER_ID)["items"] == []
    assert len(order["items"]) == 1
    assert order["items"][0]["quantity"] == 2
    assert order["public_code"].startswith("TAPTOT-")


def test_guest_checkout_cod():
    db = _session()
    product = _product(db, stock=3)
    service = ShopService(db)
    order = service.checkout(
        None,
        recipient_name="Nguyen Van A",
        phone="0901234567",
        province_code="01",
        province_name="Ha Noi",
        district_code="001",
        district_name="Ba Dinh",
        ward_code="0001",
        ward_name="Phuc Xa",
        address_line="12 Pho Hue",
        payment_method="cod",
        items=[{"product_id": product.id, "quantity": 1}],
    )
    db.refresh(product)
    assert order["user_id"] is None
    assert order["payment_method"] == "cod"
    assert order["payment_status"] == "cod"
    assert order["phone"] == "0901234567"
    assert product.stock_qty == 2


def test_guest_checkout_bank_transfer():
    db = _session()
    product = _product(db, stock=2)
    service = ShopService(db)
    order = service.checkout(
        None,
        recipient_name="Tran B",
        phone="0912345678",
        province_code="79",
        province_name="HCM",
        district_code="760",
        district_name="Q1",
        ward_code="26734",
        ward_name="Ben Nghe",
        address_line="1 Nguyen Hue",
        payment_method="bank_transfer",
        items=[{"product_id": product.id, "quantity": 1}],
    )
    assert order["payment_status"] == "awaiting_transfer"
    assert order["bank_transfer"]["transfer_content"] == order["public_code"]


def test_track_requires_phone_and_code():
    db = _session()
    product = _product(db, stock=2)
    service = ShopService(db)
    order = service.checkout(
        None,
        recipient_name="Nguyen A",
        phone="0923456789",
        province_code="01",
        province_name="HN",
        district_code="1",
        district_name="D",
        ward_code="1",
        ward_name="W",
        address_line="1 Street",
        payment_method="cod",
        items=[{"product_id": product.id, "quantity": 1}],
    )
    tracked = service.track_order("0923456789", order["public_code"])
    assert tracked["id"] == order["id"]
    from app.core.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        service.track_order("0923456789", "TAPTOT-XXXXX")


def test_track_by_phone_lists_orders_newest_first():
    db = _session()
    product_a = _product(db, stock=3, price=100000)
    product_b = _product(db, stock=3, price=200000)
    service = ShopService(db)
    first = service.checkout(
        None,
        recipient_name="Nguyen A",
        phone="0945678901",
        province_code="01",
        province_name="HN",
        district_code="1",
        district_name="D",
        ward_code="1",
        ward_name="W",
        address_line="1 Street",
        payment_method="cod",
        items=[{"product_id": product_a.id, "quantity": 1}],
    )
    second = service.checkout(
        None,
        recipient_name="Nguyen A",
        phone="0945678901",
        province_code="01",
        province_name="HN",
        district_code="1",
        district_name="D",
        ward_code="1",
        ward_name="W",
        address_line="1 Street",
        payment_method="cod",
        items=[{"product_id": product_b.id, "quantity": 1}],
    )
    listed = service.list_orders_by_phone("0945678901")
    assert [row["id"] for row in listed] == [second["id"], first["id"]]
    assert service.list_orders_by_phone("0956789012") == []


def test_invalid_phone_rejected():
    db = _session()
    product = _product(db, stock=1)
    with pytest.raises(BadRequestError):
        ShopService(db).checkout(
            None,
            recipient_name="A",
            phone="123",
            province_code="01",
            province_name="HN",
            district_code="1",
            district_name="D",
            ward_code="1",
            ward_name="W",
            address_line="1 Street",
            payment_method="cod",
            items=[{"product_id": product.id, "quantity": 1}],
        )


def test_admin_update_order_status():
    db = _session()
    product = _product(db, stock=2)
    service = ShopService(db)
    order = service.checkout(
        None,
        recipient_name="Nguyen A",
        phone="0934567890",
        province_code="01",
        province_name="HN",
        district_code="1",
        district_name="D",
        ward_code="1",
        ward_name="W",
        address_line="1 Street",
        payment_method="bank_transfer",
        items=[{"product_id": product.id, "quantity": 1}],
    )
    assert order["payment_status"] == "awaiting_transfer"
    packing = service.update_order_status(order["id"], "packing")
    assert packing["order_status"] == "packing"


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


def test_checkout_issues_one_code_per_unit():
    db = _session()
    one = _product(db, stock=5, name="Day", price=99000)
    two = _product(db, stock=5, name="Vong", price=199000)
    service = ShopService(db)
    service.add_to_cart(USER_ID, one.id, 1)
    service.add_to_cart(USER_ID, two.id, 2)
    order = service.checkout(USER_ID)
    rows = (
        db.query(ProductRedeemCode)
        .filter(ProductRedeemCode.order_id == order["id"])
        .all()
    )
    assert len(rows) == 3
    assert all(r.status == "unused" for r in rows)
    assert all(r.code.startswith("TT-") for r in rows)
    assert len({r.code for r in rows}) == 3
    listed = service.list_admin_orders(PaginationParams())
    admin_order = next(o for o in listed.items if o["id"] == order["id"])
    assert len(admin_order["gift_codes"]) == 3
    assert "gift_codes" not in order


def test_cancel_voids_unused_order_codes():
    db = _session()
    product = _product(db, stock=4)
    service = ShopService(db)
    service.add_to_cart(USER_ID, product.id, 2)
    order = service.checkout(USER_ID)
    cancelled = service.cancel_order(order["id"])
    assert cancelled["order_status"] == "cancelled"
    assert all(c["status"] == "void" for c in cancelled["gift_codes"])
    leftover = (
        db.query(ProductRedeemCode)
        .filter(ProductRedeemCode.order_id == order["id"])
        .all()
    )
    assert leftover and all(r.status == "void" for r in leftover)


def test_cancel_deletes_plan_from_redeemed_code_and_voids_all():
    db = _session()
    product = _product(db, stock=5)
    service = ShopService(db)
    service.add_to_cart(USER_ID, product.id, 2)
    order = service.checkout(USER_ID)
    codes = (
        db.query(ProductRedeemCode)
        .filter(ProductRedeemCode.order_id == order["id"])
        .order_by(ProductRedeemCode.id.asc())
        .all()
    )
    assert len(codes) == 2
    now = datetime.now(UTC)
    plan = UserDailyPlan(
        title_vi="Lịch từ mã đơn",
        source="ai",
        created_at=now,
        updated_at=now,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    redeem = RedeemCodeService(db)
    assert redeem.try_redeem(codes[0].code, plan_id=plan.id, user_id=USER_ID) is True
    plan_id = plan.id

    cancelled = service.cancel_order(order["id"])
    assert cancelled["order_status"] == "cancelled"
    assert product.stock_qty == 5
    leftover = (
        db.query(ProductRedeemCode)
        .filter(ProductRedeemCode.order_id == order["id"])
        .all()
    )
    assert len(leftover) == 2
    assert all(r.status == "void" for r in leftover)
    assert all(r.plan_id is None for r in leftover)
    assert db.get(UserDailyPlan, plan_id) is None


def test_cancel_mixed_unused_and_redeemed_voids_both_deletes_only_redeemed_plan():
    """Đơn 2 mã: 1 unused + 1 redeemed(+plan) → hủy void cả hai, chỉ xóa plan redeemed."""
    db = _session()
    product = _product(db, stock=4)
    service = ShopService(db)
    service.add_to_cart(USER_ID, product.id, 2)
    order = service.checkout(USER_ID)
    codes = (
        db.query(ProductRedeemCode)
        .filter(ProductRedeemCode.order_id == order["id"])
        .order_by(ProductRedeemCode.id.asc())
        .all()
    )
    unused_code, to_redeem = codes[0], codes[1]
    now = datetime.now(UTC)
    plan = UserDailyPlan(
        title_vi="Plan redeemed only",
        source="ai",
        created_at=now,
        updated_at=now,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    redeem = RedeemCodeService(db)
    assert redeem.try_redeem(to_redeem.code, plan_id=plan.id, user_id=USER_ID) is True
    assert redeem.lookup(unused_code.code)["status"] == "unused"
    plan_id = plan.id

    service.cancel_order(order["id"])
    db.refresh(unused_code)
    db.refresh(to_redeem)
    assert unused_code.status == "void"
    assert unused_code.plan_id is None
    assert to_redeem.status == "void"
    assert to_redeem.plan_id is None
    assert db.get(UserDailyPlan, plan_id) is None


def test_cancel_voids_reserved_processing_code():
    db = _session()
    product = _product(db, stock=2)
    service = ShopService(db)
    service.add_to_cart(USER_ID, product.id, 1)
    order = service.checkout(USER_ID)
    row = (
        db.query(ProductRedeemCode)
        .filter(ProductRedeemCode.order_id == order["id"])
        .one()
    )
    redeem = RedeemCodeService(db)
    token = redeem.reserve(row.code)
    assert token
    assert redeem.lookup(row.code)["status"] == "processing"

    service.cancel_order(order["id"])
    db.refresh(row)
    assert row.status == "void"
    assert row.reservation_token is None
    assert row.reserved_at is None
    assert product.stock_qty == 2


def test_redeem_after_cancel_fails():
    db = _session()
    product = _product(db, stock=2)
    service = ShopService(db)
    service.add_to_cart(USER_ID, product.id, 1)
    order = service.checkout(USER_ID)
    code = (
        db.query(ProductRedeemCode)
        .filter(ProductRedeemCode.order_id == order["id"])
        .one()
        .code
    )
    service.cancel_order(order["id"])
    redeem = RedeemCodeService(db)
    looked = redeem.lookup(code)
    assert looked["valid"] is False
    assert looked["status"] == "void"
    now = datetime.now(UTC)
    plan = UserDailyPlan(
        title_vi="Should not attach",
        source="ai",
        created_at=now,
        updated_at=now,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    assert redeem.try_redeem(code, plan_id=plan.id, user_id=USER_ID) is False
    assert db.get(UserDailyPlan, plan.id) is not None


def test_cancel_order_a_does_not_touch_order_b_codes_or_plan():
    db = _session()
    product = _product(db, stock=10)
    service = ShopService(db)
    service.add_to_cart(USER_ID, product.id, 1)
    order_a = service.checkout(USER_ID)
    service.add_to_cart(USER_ID, product.id, 1)
    order_b = service.checkout(USER_ID)
    code_a = (
        db.query(ProductRedeemCode)
        .filter(ProductRedeemCode.order_id == order_a["id"])
        .one()
    )
    code_b = (
        db.query(ProductRedeemCode)
        .filter(ProductRedeemCode.order_id == order_b["id"])
        .one()
    )
    now = datetime.now(UTC)
    plan_a = UserDailyPlan(
        title_vi="Plan A",
        source="ai",
        created_at=now,
        updated_at=now,
    )
    plan_b = UserDailyPlan(
        title_vi="Plan B",
        source="ai",
        created_at=now,
        updated_at=now,
    )
    db.add_all([plan_a, plan_b])
    db.commit()
    db.refresh(plan_a)
    db.refresh(plan_b)
    redeem = RedeemCodeService(db)
    assert redeem.try_redeem(code_a.code, plan_id=plan_a.id, user_id=USER_ID) is True
    assert redeem.try_redeem(code_b.code, plan_id=plan_b.id, user_id=USER_ID) is True
    plan_a_id, plan_b_id = plan_a.id, plan_b.id

    service.cancel_order(order_a["id"])
    db.refresh(code_a)
    db.refresh(code_b)
    assert code_a.status == "void"
    assert db.get(UserDailyPlan, plan_a_id) is None
    assert code_b.status == "redeemed"
    assert code_b.plan_id == plan_b_id
    assert db.get(UserDailyPlan, plan_b_id) is not None


def test_cancel_rejected_when_order_shipped():
    db = _session()
    product = _product(db, stock=2)
    service = ShopService(db)
    service.add_to_cart(USER_ID, product.id, 1)
    order = service.checkout(USER_ID)
    service.update_order_status(order["id"], "packing")
    service.update_order_status(order["id"], "shipping")
    with pytest.raises(BadRequestError):
        service.cancel_order(order["id"])
    assert product.stock_qty == 1
    row = (
        db.query(ProductRedeemCode)
        .filter(ProductRedeemCode.order_id == order["id"])
        .one()
    )
    assert row.status == "unused"


def _pushup_ticket(db: Session, *, reps: int = 25) -> str:
    started = datetime.now(UTC)
    elapsed = 50 if reps > 36 else 30
    sid = start_session(db, now=started)["session_id"]
    return finish_session(
        db, session_id=sid, reps=reps, now=started + timedelta(seconds=elapsed)
    )["ticket"]


def _ship(**overrides):
    fields = dict(
        recipient_name="Nguyen Van A",
        phone="0901234567",
        province_code="01",
        province_name="Ha Noi",
        district_code="001",
        district_name="Ba Dinh",
        ward_code="0001",
        ward_name="Phuc Xa",
        address_line="12 Pho Hue",
        payment_method="cod",
    )
    fields.update(overrides)
    return fields


def test_checkout_applies_pushup_ticket_once():
    db = _session()
    product = _product(db, stock=5)
    ticket = _pushup_ticket(db, reps=25)
    service = ShopService(db)
    service.add_to_cart(USER_ID, product.id, 1)
    order = service.checkout(USER_ID, pushup_ticket=ticket, **_ship(payment_method="bank_transfer"))
    assert order["discount_percent"] == 10
    assert order["discount_vnd"] == 10000
    assert order["total_vnd"] == 90000
    assert order["bank_transfer"]["amount_vnd"] == 90000

    service.add_to_cart(USER_ID, product.id, 1)
    with pytest.raises(BadRequestError):
        service.checkout(USER_ID, pushup_ticket=ticket, **_ship())
    db.refresh(product)
    assert product.stock_qty == 4
    assert db.query(ShopOrder).count() == 1


def test_checkout_without_ticket_full_price():
    db = _session()
    product = _product(db, stock=3)
    service = ShopService(db)
    service.add_to_cart(USER_ID, product.id, 1)
    order = service.checkout(USER_ID, **_ship())
    assert order["discount_percent"] == 0
    assert order["discount_vnd"] == 0
    assert order["total_vnd"] == 100000


def test_checkout_rejects_invalid_pushup_ticket():
    db = _session()
    product = _product(db, stock=2)
    service = ShopService(db)
    with pytest.raises(BadRequestError):
        service.checkout(
            None,
            items=[{"product_id": product.id, "quantity": 1}],
            pushup_ticket="not-a-real-ticket",
            **_ship(),
        )
    db.refresh(product)
    assert product.stock_qty == 2
    assert db.query(ShopOrder).count() == 0


def test_activation_cover_png_and_pdf():
    from app.services.activation_cover import cover_png_bytes, covers_pdf_bytes, render_cover
    from app.services.redeem_code_service import gift_landing_url

    code = "TT-7K3M-P2QX"
    assert gift_landing_url(code).endswith(f"/batdau/{code}")
    img = render_cover(code)
    assert img.size == (1800, 2400)
    png = cover_png_bytes(code)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    pdf = covers_pdf_bytes([code, "TT-ABCD-2345"])
    assert pdf[:4] == b"%PDF"
