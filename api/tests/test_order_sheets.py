"""Shop orders upsert to Google Sheets without blocking checkout."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.entities import ShopOrder, ShopOrderItem, ShopProduct
from app.services.order_sheets import sync_order_row
from app.services.shop_service import ShopService


def _order() -> tuple[ShopOrder, list[ShopOrderItem]]:
    now = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
    order = ShopOrder(
        order_status="awaiting_confirm",
        total_vnd=450_000,
        shipping_fee_vnd=0,
        discount_percent=0,
        discount_vnd=10_000,
        note="Giao giờ hành chính",
        created_at=now,
        public_code="TAPTOT-ABCDE",
        recipient_name="Nguyễn An",
        phone="0901000001",
        province_name="Hà Nội",
        district_name="Ba Đình",
        ward_name="Phúc Xá",
        address_line="12 phố Nguyễn Thái Học",
        payment_method="cod",
        payment_status="cod",
        promo_code="TAITRAN",
        promo_percent=10,
        promo_discount_vnd=50_000,
    )
    items = [
        ShopOrderItem(
            order_id=1,
            product_id=1,
            name_vi="Tạ đơn",
            unit_price_vnd=500_000,
            quantity=1,
        )
    ]
    return order, items


@patch("app.services.order_sheets.get_settings")
@patch("app.services.order_sheets.httpx.post")
def test_sync_posts_order_payload(mock_post, mock_settings):
    mock_settings.return_value = SimpleNamespace(
        order_sheets_webhook_url="https://script.google.com/macros/s/test/exec",
        order_sheets_secret="16102002",
    )
    mock_post.return_value = SimpleNamespace(status_code=200)
    order, items = _order()
    sync_order_row(order, items)
    body = mock_post.call_args.kwargs["json"]
    assert mock_post.call_args.kwargs["follow_redirects"] is True
    assert body["kind"] == "order"
    assert body["secret"] == "16102002"
    assert body["public_code"] == "TAPTOT-ABCDE"
    assert body["status"] == "Chờ xác nhận"
    assert body["recipient_name"] == "Nguyễn An"
    assert body["phone"] == "0901000001"
    assert body["address"] == "12 phố Nguyễn Thái Học, Phúc Xá, Ba Đình, Hà Nội"
    assert body["products"] == "Tạ đơn × 1"
    assert body["total_vnd"] == 450_000
    assert body["promo_code"] == "TAITRAN"
    assert body["promo_discount_vnd"] == 50_000
    assert body["payment"] == "COD · COD"


@patch("app.services.order_sheets.get_settings")
@patch("app.services.order_sheets.httpx.post")
def test_sync_skips_when_unconfigured(mock_post, mock_settings):
    mock_settings.return_value = SimpleNamespace(order_sheets_webhook_url="", order_sheets_secret="")
    order, items = _order()
    sync_order_row(order, items)
    mock_post.assert_not_called()


@patch("app.services.order_sheets.get_settings")
@patch("app.services.order_sheets.httpx.post")
def test_sync_swallows_http_errors(mock_post, mock_settings):
    mock_settings.return_value = SimpleNamespace(
        order_sheets_webhook_url="https://script.google.com/macros/s/test/exec",
        order_sheets_secret="x",
    )
    mock_post.side_effect = httpx.ConnectError("down")
    order, items = _order()
    sync_order_row(order, items)
    order.order_status = "packing"
    mock_post.side_effect = None
    mock_post.return_value = SimpleNamespace(status_code=500)
    sync_order_row(order, items)
    assert mock_post.call_args.kwargs["json"]["status"] == "Đang đóng gói"


def _shop_db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    now = datetime.now(UTC)
    db.add(
        ShopProduct(
            slug="ta-don",
            name_vi="Tạ đơn",
            description_vi=None,
            price_vnd=100_000,
            stock_qty=5,
            image_url=None,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()
    return db


def test_checkout_and_status_change_sync_the_sheet():
    db = _shop_db()
    service = ShopService(db)
    seen: list[str] = []

    def capture(order, items):
        seen.append(order.order_status)
        assert items

    with patch("app.services.order_sheets.sync_order_row", side_effect=capture):
        created = service.checkout(
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
            items=[{"product_id": 1, "quantity": 1}],
        )
        service.update_order_status(created["id"], "packing")
        cancelled = service.checkout(
            None,
            recipient_name="Nguyen Van B",
            phone="0901234568",
            province_code="01",
            province_name="Ha Noi",
            district_code="001",
            district_name="Ba Dinh",
            ward_code="0001",
            ward_name="Phuc Xa",
            address_line="13 Pho Hue",
            payment_method="cod",
            items=[{"product_id": 1, "quantity": 1}],
        )
        service.update_order_status(cancelled["id"], "cancelled")
    assert seen == ["awaiting_confirm", "packing", "awaiting_confirm", "cancelled"]
    assert created["public_code"].startswith("TAPTOT-")
