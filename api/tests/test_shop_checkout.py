"""Shop checkout: decrement stock, 409 when short, cancel restores stock."""

from datetime import UTC, date, datetime, timedelta
from urllib.parse import quote

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.exceptions import BadRequestError, ConflictError, UnauthorizedError
from app.core.pagination import PaginationParams
from app.models.base import Base
from app.models.entities import ProductRedeemCode, ShopCartItem, ShopOrder, ShopProduct, User, UserDailyPlan
from app.services.pushup_challenge import finish_session, start_session
from app.services.redeem_code_service import RedeemCodeService
from app.services.shop_service import ShopService, require_sepay_api_key


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
    code = order["public_code"].replace("-", "")
    memo = f"SEVQR {code}"
    assert order["bank_transfer"]["transfer_content"] == memo
    assert f"addInfo={quote(memo)}" in order["bank_transfer"]["qr_image_url"]


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


def test_same_phone_requires_each_order_public_code():
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
    assert service.track_order("0945678901", first["public_code"])["id"] == first["id"]
    assert service.track_order("0945678901", second["public_code"])["id"] == second["id"]


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


def test_bulk_update_order_status():
    db = _session()
    product = _product(db, stock=5)
    service = ShopService(db)
    a = service.checkout(USER_ID, items=[{"product_id": product.id, "quantity": 1}], **_ship())
    b = service.checkout(USER_ID, items=[{"product_id": product.id, "quantity": 1}], **_ship())
    result = service.bulk_update_order_status([a["id"], b["id"], a["id"]], "packing")
    assert result["updated_count"] == 2
    assert result["skipped_count"] == 0
    assert result["error_count"] == 0
    again = service.bulk_update_order_status([a["id"], b["id"]], "packing")
    assert again["skipped_count"] == 2
    assert again["updated_count"] == 0
    shipping = service.bulk_update_order_status([a["id"], 999999], "shipping")
    assert shipping["updated_count"] == 1
    assert shipping["error_count"] == 1
    assert db.get(ShopOrder, a["id"]).order_status == "shipping"
    assert db.get(ShopOrder, b["id"]).order_status == "packing"


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


def test_cancel_while_shipping_restores_stock_but_completed_does_not():
    db = _session()
    product = _product(db, stock=2)
    service = ShopService(db)
    service.add_to_cart(USER_ID, product.id, 1)
    order = service.checkout(USER_ID)
    service.update_order_status(order["id"], "packing")
    service.update_order_status(order["id"], "shipping")
    service.cancel_order(order["id"])
    db.refresh(product)
    assert product.stock_qty == 2
    row = (
        db.query(ProductRedeemCode)
        .filter(ProductRedeemCode.order_id == order["id"])
        .one()
    )
    assert row.status == "void"

    service.add_to_cart(USER_ID, product.id, 1)
    done = service.checkout(USER_ID)
    service.update_order_status(done["id"], "packing")
    service.update_order_status(done["id"], "shipping")
    service.update_order_status(done["id"], "completed")
    with pytest.raises(BadRequestError):
        service.cancel_order(done["id"])
    db.refresh(product)
    assert product.stock_qty == 1


def test_return_from_completed_restocks_and_voids_code():
    db = _session()
    product = _product(db, stock=2)
    service = ShopService(db)
    service.add_to_cart(USER_ID, product.id, 1)
    order = service.checkout(USER_ID)
    with pytest.raises(BadRequestError):
        service.update_order_status(order["id"], "returned")
    db.refresh(product)
    assert product.stock_qty == 1

    service.update_order_status(order["id"], "packing")
    service.update_order_status(order["id"], "shipping")
    service.update_order_status(order["id"], "completed")
    returned = service.update_order_status(order["id"], "returned")
    assert returned["order_status"] == "returned"
    db.refresh(product)
    assert product.stock_qty == 2
    code = (
        db.query(ProductRedeemCode)
        .filter(ProductRedeemCode.order_id == order["id"])
        .one()
    )
    assert code.status == "void"
    with pytest.raises(BadRequestError):
        service.return_order(order["id"])
    db.refresh(product)
    assert product.stock_qty == 2


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
    assert order["discount_percent"] == 5
    assert order["discount_vnd"] == 5000
    assert order["total_vnd"] == 95000
    assert order["bank_transfer"]["amount_vnd"] == 95000

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


def _pdf_page_count(pdf: bytes) -> int:
    import re

    return len(re.findall(br"/Type /Page(?!s)", pdf))


def test_activation_cover_png_and_pdf():
    from app.services.activation_cover import (
        cover_png_bytes,
        covers_pdf_bytes,
        images_pdf_bytes,
        order_address_lines,
        payment_caption,
        postal_lines,
        render_cover,
        render_order_sheet,
        thanks_line,
    )
    from app.services.redeem_code_service import gift_landing_url

    code = "TT-7K3M-P2QX"
    assert "nhap-ma=1" in gift_landing_url(code)
    assert f"code={code}" in gift_landing_url(code)
    assert f"/batdau/{code}" not in gift_landing_url(code)
    assert thanks_line(None) == "CẢM ƠN BẠN ĐÃ TIN TƯỞNG"
    assert thanks_line("  Nguyễn Văn A ") == "CẢM ƠN BẠN ĐÃ TIN TƯỞNG"
    assert postal_lines("12 phố huế", "Phường Huế", "Hà Nội") == ["12 Phố Huế", "Phường Huế, Hà Nội"]
    assert postal_lines("12 PHỐ HUẾ", "Phường Huế", "Hà Nội") == ["12 Phố Huế", "Phường Huế, Hà Nội"]
    assert postal_lines("12/3a P.Huế QL1A", "Phường Huế", "Hà Nội") == [
        "12/3A P.Huế QL1A",
        "Phường Huế, Hà Nội",
    ]
    assert order_address_lines("12 phố huế", "Phường Huế", "Quận Hai Bà Trưng", "Hà Nội") == [
        "12 Phố Huế",
        "Phường Huế, Quận Hai Bà Trưng, Hà Nội",
    ]
    assert payment_caption("cod", "unpaid") == "COD · Chưa thanh toán"
    img = render_cover(code)
    assert img.size == (1800, 2400)
    slip = render_order_sheet(
        {
            "public_code": "TAPTOT-ABCDE",
            "created_at": "05/11/2026 09:00",
            "recipient_name": "Nguyễn Văn A",
            "phone": "0901234567",
            "address_lines": order_address_lines("12 phố huế", "Phường Huế", "Quận Hai Bà Trưng", "Hà Nội"),
            "items": [{"name": "Dây kháng lực", "quantity": 2, "unit_price_vnd": 150000}],
            "shipping_fee_vnd": 30000,
            "discount_vnd": 0,
            "promo_code": "CTV10",
            "promo_discount_vnd": 15000,
            "total_vnd": 315000,
            "payment": payment_caption("bank_transfer", "awaiting_transfer"),
            "note": "Giao giờ hành chính",
        }
    )
    assert slip.size == (1800, 2400)
    png = cover_png_bytes(code)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    pdf = covers_pdf_bytes([{"code": code}, "TT-ABCD-2345"])
    assert pdf[:4] == b"%PDF"
    one_code = images_pdf_bytes([slip, render_cover(code)])
    two_codes = images_pdf_bytes([slip, render_cover(code), render_cover("TT-ABCD-2345")])
    assert one_code[:4] == b"%PDF"
    assert _pdf_page_count(one_code) == 2
    assert _pdf_page_count(two_codes) == 3


def test_order_sheet_draws_product_thumbnail(tmp_path):
    from PIL import Image

    from app.services.activation_cover import local_media_file, render_order_sheet

    photo = tmp_path / "equipment" / "band" / "01.png"
    photo.parent.mkdir(parents=True)
    Image.new("RGB", (40, 24), (220, 8, 8)).save(photo)
    assert local_media_file("equipment/band/01.png?v=1", tmp_path) == photo.resolve()
    assert local_media_file("/media/equipment/band/01.png", tmp_path) == photo.resolve()
    assert local_media_file("https://cdn.example.com/other.png", tmp_path) is None
    assert local_media_file("../secret.png", tmp_path) is None
    assert local_media_file(None, tmp_path) is None

    slip = render_order_sheet(
        {
            "public_code": "TAPTOT-ABCDE",
            "recipient_name": "Nguyễn Văn A",
            "phone": "0901234567",
            "address_lines": ["12 Phố Huế"],
            "items": [
                {
                    "name": "Dây kháng lực",
                    "quantity": 1,
                    "unit_price_vnd": 150000,
                    "image_path": str(photo),
                }
            ],
            "total_vnd": 150000,
            "payment": "COD",
        }
    )
    assert slip.size == (1800, 2400)
    pixels = slip.load()
    found = False
    for y in range(0, slip.height, 3):
        for x in range(90, 180):
            red, green, blue = pixels[x, y][:3]
            if red > 180 and green < 40 and blue < 40:
                found = True
                break
        if found:
            break
    assert found


def test_list_admin_orders_filters_payment_method():
    db = _session()
    product = _product(db, stock=5)
    service = ShopService(db)
    cod = service.checkout(USER_ID, items=[{"product_id": product.id, "quantity": 1}], **_ship())
    bank = service.checkout(
        USER_ID,
        items=[{"product_id": product.id, "quantity": 1}],
        **_ship(payment_method="bank_transfer", phone="0901234568"),
    )
    bank_only = service.list_admin_orders(PaginationParams(), payment_method="bank_transfer")
    assert [o["id"] for o in bank_only.items] == [bank["id"]]
    cod_only = service.list_admin_orders(PaginationParams(), payment_method="cod")
    assert cod["id"] in [o["id"] for o in cod_only.items]
    assert bank["id"] not in [o["id"] for o in cod_only.items]
    with pytest.raises(BadRequestError):
        service.list_admin_orders(PaginationParams(), payment_method="cash")


def test_list_admin_orders_filters_product():
    db = _session()
    band = _product(db, stock=5, name="Dây", price=100000)
    bell = _product(db, stock=5, name="Tạ", price=200000)
    service = ShopService(db)
    band_order = service.checkout(USER_ID, items=[{"product_id": band.id, "quantity": 1}], **_ship())
    bell_order = service.checkout(
        USER_ID,
        items=[{"product_id": bell.id, "quantity": 1}],
        **_ship(phone="0901234568"),
    )
    both = service.checkout(
        USER_ID,
        items=[{"product_id": band.id, "quantity": 1}, {"product_id": bell.id, "quantity": 1}],
        **_ship(phone="0901234569"),
    )
    only_band = service.list_admin_orders(PaginationParams(), product_id=band.id)
    ids = [o["id"] for o in only_band.items]
    assert band_order["id"] in ids
    assert both["id"] in ids
    assert bell_order["id"] not in ids
    only_bell = service.list_admin_orders(PaginationParams(), product_id=bell.id)
    bell_ids = [o["id"] for o in only_bell.items]
    assert bell_order["id"] in bell_ids
    assert both["id"] in bell_ids
    assert band_order["id"] not in bell_ids
    with pytest.raises(BadRequestError):
        service.list_admin_orders(PaginationParams(), product_id=0)


def test_list_admin_orders_filters_created_date():
    db = _session()
    product = _product(db, stock=5)
    service = ShopService(db)
    first = service.checkout(USER_ID, items=[{"product_id": product.id, "quantity": 1}], **_ship())
    second = service.checkout(USER_ID, items=[{"product_id": product.id, "quantity": 1}], **_ship())
    db.get(ShopOrder, first["id"]).created_at = datetime(2026, 1, 10, 12, 0, tzinfo=UTC)
    db.get(ShopOrder, second["id"]).created_at = datetime(2026, 10, 12, 5, 0, tzinfo=UTC)
    db.commit()
    listed = service.list_admin_orders(
        PaginationParams(),
        created_from=date(2026, 10, 12),
        created_to=date(2026, 10, 12),
    )
    ids = [o["id"] for o in listed.items]
    assert second["id"] in ids
    assert first["id"] not in ids
    jan = service.list_admin_orders(
        PaginationParams(),
        created_from=date(2026, 1, 10),
        created_to=date(2026, 1, 10),
    )
    jan_ids = [o["id"] for o in jan.items]
    assert first["id"] in jan_ids
    assert second["id"] not in jan_ids
    newest_first = [
        o["id"]
        for o in service.list_admin_orders(PaginationParams(), sort="desc").items
        if o["id"] in {first["id"], second["id"]}
    ]
    oldest_first = [
        o["id"]
        for o in service.list_admin_orders(PaginationParams(), sort="asc").items
        if o["id"] in {first["id"], second["id"]}
    ]
    assert newest_first == [second["id"], first["id"]]
    assert oldest_first == [first["id"], second["id"]]


def test_list_codes_for_orders_keeps_selection_order():
    db = _session()
    product = _product(db, stock=5)
    service = ShopService(db)
    a = service.checkout(USER_ID, items=[{"product_id": product.id, "quantity": 1}], **_ship())
    b = service.checkout(USER_ID, items=[{"product_id": product.id, "quantity": 2}], **_ship())
    codes = RedeemCodeService(db).list_for_orders([b["id"], a["id"]])
    assert [c["order_id"] for c in codes] == [b["id"], b["id"], a["id"]]
    assert len(codes) == 3


def _bank_order(db):
    product = _product(db, stock=2, price=95000)
    return ShopService(db).checkout(
        None,
        items=[{"product_id": product.id, "quantity": 1}],
        **_ship(payment_method="bank_transfer"),
    )


def test_sepay_matches_memo_without_hyphen():
    db = _session()
    order = _bank_order(db)
    memo = order["bank_transfer"]["transfer_content"]
    result = ShopService(db).apply_sepay_transfer(
        {
            "id": 9010,
            "transferType": "in",
            "transferAmount": order["total_vnd"],
            "content": f"CK {memo} FT123456",
        }
    )
    assert result["reason"] == "paid"
    row = db.get(ShopOrder, order["id"])
    assert row.payment_status == "paid"
    assert row.public_code == order["public_code"]


def test_sepay_marks_paid_and_ignores_same_id():
    db = _session()
    order = _bank_order(db)
    payload = {
        "id": 9001,
        "transferType": "in",
        "transferAmount": order["total_vnd"],
        "content": f"MBVCB {order['public_code']} tai khoan",
    }
    result = ShopService(db).apply_sepay_transfer(payload)
    assert result["reason"] == "paid"
    row = db.get(ShopOrder, order["id"])
    assert row.payment_status == "paid"
    assert row.sepay_transaction_id == "9001"
    again = ShopService(db).apply_sepay_transfer(payload)
    assert again["reason"] == "already_paid"
    db.refresh(row)
    assert row.payment_status == "paid"
    assert row.sepay_transaction_id == "9001"


def test_sepay_uses_code_field_before_content():
    db = _session()
    order = _bank_order(db)
    result = ShopService(db).apply_sepay_transfer(
        {
            "id": 9002,
            "transferType": "in",
            "transferAmount": order["total_vnd"],
            "code": order["public_code"].lower(),
            "content": "TAPTOT-ZZZZZ",
        }
    )
    assert result["reason"] == "paid"
    row = db.get(ShopOrder, order["id"])
    assert row.sepay_transaction_id == "9002"


def test_sepay_rejects_wrong_amount_missing_code_and_outgoing():
    db = _session()
    order = _bank_order(db)
    service = ShopService(db)
    wrong = service.apply_sepay_transfer(
        {
            "id": 9003,
            "transferType": "in",
            "transferAmount": order["total_vnd"] - 1,
            "content": order["public_code"],
        }
    )
    assert wrong["reason"] == "amount_mismatch"
    missing = service.apply_sepay_transfer(
        {"id": 9004, "transferType": "in", "transferAmount": order["total_vnd"], "content": "chuyen tien"}
    )
    assert missing["reason"] == "no_code"
    outgoing = service.apply_sepay_transfer(
        {
            "id": 9005,
            "transferType": "out",
            "transferAmount": order["total_vnd"],
            "content": order["public_code"],
        }
    )
    assert outgoing["reason"] == "ignored_direction"
    row = db.get(ShopOrder, order["id"])
    assert row.payment_status == "awaiting_transfer"
    assert row.sepay_transaction_id is None


def test_sepay_api_key(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(
        "app.services.shop_service.get_settings",
        lambda: SimpleNamespace(sepay_webhook_api_key="secret-key"),
    )
    require_sepay_api_key("Apikey secret-key")
    with pytest.raises(UnauthorizedError) as bad:
        require_sepay_api_key("Apikey wrong-key")
    assert bad.value.status_code == 401
    with pytest.raises(UnauthorizedError) as missing:
        require_sepay_api_key(None)
    assert missing.value.status_code == 401
    monkeypatch.setattr(
        "app.services.shop_service.get_settings",
        lambda: SimpleNamespace(sepay_webhook_api_key=""),
    )
    with pytest.raises(UnauthorizedError) as unset:
        require_sepay_api_key("Apikey secret-key")
    assert unset.value.status_code == 401


def test_same_product_is_one_cart_line():
    db = _session()
    now = datetime.now(UTC)
    product = ShopProduct(
        slug="xa-don-va-vong-treo",
        name_vi="Xà đơn treo tường và Vòng treo",
        description_vi=None,
        price_vnd=500000,
        stock_qty=3,
        image_url=None,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(product)
    db.commit()
    service = ShopService(db)
    service.add_to_cart(USER_ID, product.id, 1)
    cart = service.add_to_cart(USER_ID, product.id, 1)
    assert len(cart["items"]) == 1
    assert cart["items"][0]["quantity"] == 2
    assert cart["total_vnd"] == 1_000_000
    with pytest.raises(ConflictError):
        service.add_to_cart(USER_ID, product.id, 2)
    order = service.checkout(USER_ID)
    assert [item["name_vi"] for item in order["items"]] == ["Xà đơn treo tường và Vòng treo"]
    assert order["items"][0]["quantity"] == 2
    db.refresh(product)
    assert product.stock_qty == 1
    assert service.get_cart(USER_ID)["items"] == []
