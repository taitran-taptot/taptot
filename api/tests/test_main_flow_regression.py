"""High-value regression coverage for the event -> COD -> admin -> plan flow."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.v1 import ai as ai_routes
from app.api.v1.ai import WorkoutScheduleRequest
from app.api.v1.shop import TrackOrderIn
from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ConflictError
from app.core.pagination import PaginationParams
from app.models.base import Base
from app.models.entities import (
    ProductRedeemBatch,
    ProductRedeemCode,
    ShopOrder,
    ShopOrderItem,
    ShopProduct,
    User,
    UserDailyPlan,
)
from app.services.pushup_challenge import finish_session, start_session
from app.services.redeem_code_service import RedeemCodeService
from app.services.shop_service import ShopService


USER_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(
        User(
            id=USER_ID,
            email="main-flow@test.local",
            password_hash="x",
            display_name="Main Flow",
            role="user",
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    return db


def _product(
    db: Session,
    *,
    stock: int = 10,
    price: int = 100_005,
    name: str = "Dây kháng lực",
) -> ShopProduct:
    now = datetime.now(UTC)
    row = ShopProduct(
        slug=f"kit-{stock}-{price}-{len(name)}",
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


def _shipping(**overrides) -> dict:
    fields = {
        "recipient_name": "Nguyen Van A",
        "phone": "0901234567",
        "province_code": "01",
        "province_name": "Ha Noi",
        "district_code": "001",
        "district_name": "Ba Dinh",
        "ward_code": "00001",
        "ward_name": "Phuc Xa",
        "address_line": "12 Pho Hue",
        "payment_method": "cod",
    }
    fields.update(overrides)
    return fields


def _request(code: str) -> WorkoutScheduleRequest:
    return WorkoutScheduleRequest(
        age=25,
        height_cm=170,
        weight_kg=65,
        challenge_100_days=True,
        equipment_list=["resistance-band"],
        redeem_code=code,
    )


def _http_request() -> MagicMock:
    request = MagicMock()
    request.headers = {"x-device-id": "11111111-1111-4111-8111-111111111111"}
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    return request


def _plan(db: Session, title: str = "Lịch 14 tuần") -> UserDailyPlan:
    now = datetime.now(UTC)
    row = UserDailyPlan(title_vi=title, source="ai", created_at=now, updated_at=now)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_event_cod_admin_redeem_happy_path(monkeypatch: pytest.MonkeyPatch):
    """One scenario verifies the cross-domain state and money invariants."""
    monkeypatch.setattr(get_settings(), "require_redeem_code_for_generate", True)
    db = _session()
    product = _product(db, stock=3, price=100_005)
    started = datetime.now(UTC)
    session_id = start_session(db, now=started)["session_id"]
    ticket = finish_session(
        db,
        session_id=session_id,
        reps=21,
        now=started + timedelta(seconds=30),
    )["ticket"]

    order = ShopService(db).checkout(
        None,
        items=[{"product_id": product.id, "quantity": 1}],
        pushup_ticket=ticket,
        **_shipping(),
    )
    db.refresh(product)
    assert order["discount_percent"] == 10
    assert order["discount_vnd"] == 10_000
    assert order["total_vnd"] == 90_005
    assert order["payment_status"] == "cod"
    assert product.stock_qty == 2
    assert "gift_codes" not in order

    service = ShopService(db)
    admin_order = service.list_admin_orders(
        PaginationParams(page=1, page_size=20)
    ).items[0]
    assert len(admin_order["gift_codes"]) == 1
    code = admin_order["gift_codes"][0]["code"]
    service.update_order_status(order["id"], "packing")
    service.update_order_status(order["id"], "shipping")
    service.update_order_status(order["id"], "completed")

    plan = _plan(db)
    monkeypatch.setattr(
        ai_routes,
        "generate_workout",
        lambda *_args, **_kwargs: {
            "plan_id": plan.id,
            "share_token": "temporary",
            "plan": {"id": plan.id, "title_vi": plan.title_vi, "source": "ai"},
        },
    )
    result = ai_routes.generate_workout_schedule(
        _request(code), request=_http_request(), db=db, user=None
    )
    db.refresh(plan)
    assert result["code_applied"] is True
    assert result["view_path"] == f"/lich/{code}"
    assert plan.share_token == code
    assert RedeemCodeService(db).lookup(code)["status"] == "redeemed"
    assert db.get(ShopOrder, order["id"]).order_status == "completed"


def test_order_snapshot_survives_product_edits():
    db = _session()
    product = _product(db, stock=2, price=123_456, name="Tên lúc mua")
    service = ShopService(db)
    order = service.checkout(
        None,
        items=[{"product_id": product.id, "quantity": 1}],
        **_shipping(),
    )
    service.update_product(
        product.id, {"name_vi": "Tên sau chỉnh sửa", "price_vnd": 999_999}
    )
    tracked = service.track_order("0901234567", order["public_code"].lower())
    assert tracked["total_vnd"] == 123_456
    assert tracked["items"][0]["name_vi"] == "Tên lúc mua"
    assert tracked["items"][0]["unit_price_vnd"] == 123_456


def test_phone_normalization_is_consistent_for_checkout_and_tracking():
    db = _session()
    product = _product(db)
    service = ShopService(db)
    order = service.checkout(
        None,
        items=[{"product_id": product.id, "quantity": 1}],
        **_shipping(phone="+84 901-234-567"),
    )
    assert order["phone"] == "0901234567"
    assert service.track_order("84.901.234.567", order["public_code"])["id"] == order["id"]


def test_order_tracking_requires_phone_and_public_code():
    with pytest.raises(ValidationError):
        TrackOrderIn(phone="0901234567")
    parsed = TrackOrderIn(phone="0901234567", public_code="taptot-ab123")
    assert parsed.public_code == "TAPTOT-AB123"


def test_201_codes_failure_is_atomic_after_request_rollback():
    db = _session()
    product = _product(db, stock=201)
    with pytest.raises(BadRequestError):
        ShopService(db).checkout(
            None,
            items=[{"product_id": product.id, "quantity": 201}],
            **_shipping(),
        )
    db.rollback()
    db.refresh(product)
    assert product.stock_qty == 201
    assert db.query(ShopOrder).count() == 0
    assert db.query(ShopOrderItem).count() == 0
    assert db.query(ProductRedeemBatch).count() == 0
    assert db.query(ProductRedeemCode).count() == 0


def test_stale_reservation_can_be_reclaimed_but_old_token_cannot_complete():
    db = _session()
    service = RedeemCodeService(db)
    code = service.create_batch(admin_user_id=USER_ID, qty=1)["codes"][0]["code"]
    old_token = service.reserve(code)
    assert old_token
    row = db.query(ProductRedeemCode).filter(ProductRedeemCode.code == code).one()
    row.reserved_at = datetime.now(UTC) - timedelta(minutes=31)
    db.commit()

    new_token = service.reserve(code)
    assert new_token and new_token != old_token
    old_plan = _plan(db, "Old caller")
    new_plan = _plan(db, "New caller")
    assert service.complete(code, old_token, plan_id=old_plan.id, user_id=None) is False
    assert service.complete(code, new_token, plan_id=new_plan.id, user_id=None) is True
    assert service.lookup(code)["status"] == "redeemed"


def test_app_exception_from_generation_releases_code(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(get_settings(), "require_redeem_code_for_generate", True)
    db = _session()
    code = RedeemCodeService(db).create_batch(
        admin_user_id=USER_ID, qty=1
    )["codes"][0]["code"]

    def fail(*_args, **_kwargs):
        raise ConflictError("catalog changed")

    monkeypatch.setattr(ai_routes, "generate_workout", fail)
    with pytest.raises(ConflictError):
        ai_routes.generate_workout_schedule(
            _request(code), request=_http_request(), db=db, user=None
        )
    assert RedeemCodeService(db).lookup(code)["valid"] is True


def test_missing_plan_id_releases_code(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(get_settings(), "require_redeem_code_for_generate", True)
    db = _session()
    code = RedeemCodeService(db).create_batch(
        admin_user_id=USER_ID, qty=1
    )["codes"][0]["code"]
    monkeypatch.setattr(
        ai_routes,
        "generate_workout",
        lambda *_args, **_kwargs: {"share_token": "orphan"},
    )
    with pytest.raises(BadRequestError):
        ai_routes.generate_workout_schedule(
            _request(code), request=_http_request(), db=db, user=None
        )
    assert RedeemCodeService(db).lookup(code)["valid"] is True


def test_duplicate_product_lines_cannot_oversell():
    db = _session()
    product = _product(db, stock=1)
    with pytest.raises(ConflictError):
        ShopService(db).checkout(
            None,
            items=[
                {"product_id": product.id, "quantity": 1},
                {"product_id": product.id, "quantity": 1},
            ],
            **_shipping(),
        )
    db.rollback()
    db.refresh(product)
    assert product.stock_qty == 1
    assert db.query(ShopOrder).count() == 0


def test_duplicate_product_lines_are_aggregated_into_one_order_item():
    db = _session()
    product = _product(db, stock=5)
    order = ShopService(db).checkout(
        None,
        items=[
            {"product_id": product.id, "quantity": 1},
            {"product_id": product.id, "quantity": 2},
        ],
        **_shipping(),
    )
    db.refresh(product)
    rows = db.query(ShopOrderItem).filter(ShopOrderItem.order_id == order["id"]).all()
    assert len(rows) == 1
    assert rows[0].quantity == 3
    assert product.stock_qty == 2


@pytest.mark.xfail(
    strict=True,
    reason="KNOWN-ADM-008: fulfillment transition matrix is not enforced",
)
def test_admin_cannot_skip_or_reverse_fulfillment_states():
    db = _session()
    product = _product(db, stock=2)
    service = ShopService(db)
    order = service.checkout(
        None,
        items=[{"product_id": product.id, "quantity": 1}],
        **_shipping(),
    )
    with pytest.raises(BadRequestError):
        service.update_order_status(order["id"], "completed")
    assert db.get(ShopOrder, order["id"]).order_status == "awaiting_confirm"


def test_retrying_identical_checkout_does_not_duplicate_order():
    db = _session()
    product = _product(db, stock=3)
    payload = {
        "items": [{"product_id": product.id, "quantity": 1}],
        **_shipping(),
    }
    key = "checkout-retry-key-0001"
    first = ShopService(db).checkout(None, idempotency_key=key, **payload)
    second = ShopService(db).checkout(None, idempotency_key=key, **payload)
    db.refresh(product)
    assert second["id"] == first["id"]
    assert product.stock_qty == 2
    assert db.query(ShopOrder).count() == 1


def test_reusing_idempotency_key_for_different_payload_is_rejected():
    db = _session()
    product = _product(db, stock=3)
    key = "checkout-conflict-key-01"
    ShopService(db).checkout(
        None,
        idempotency_key=key,
        items=[{"product_id": product.id, "quantity": 1}],
        **_shipping(),
    )
    with pytest.raises(ConflictError):
        ShopService(db).checkout(
            None,
            idempotency_key=key,
            items=[{"product_id": product.id, "quantity": 2}],
            **_shipping(),
        )
    db.refresh(product)
    assert product.stock_qty == 2
    assert db.query(ShopOrder).count() == 1


def test_account_explicit_items_clear_cart_once_and_replay_order():
    db = _session()
    product = _product(db, stock=3)
    service = ShopService(db)
    service.add_to_cart(USER_ID, product.id, 1)
    payload = {
        "items": [{"product_id": product.id, "quantity": 1}],
        **_shipping(),
    }
    key = "account-checkout-key-0001"
    first = service.checkout(USER_ID, idempotency_key=key, **payload)
    assert service.get_cart(USER_ID)["items"] == []
    replay = service.checkout(USER_ID, idempotency_key=key, **payload)
    assert replay["id"] == first["id"]
    db.refresh(product)
    assert product.stock_qty == 2
    assert db.query(ShopOrder).count() == 1


def test_idempotent_replay_does_not_consume_discount_ticket_twice():
    db = _session()
    product = _product(db, stock=3, price=100_000)
    started = datetime.now(UTC)
    session_id = start_session(db, now=started)["session_id"]
    ticket = finish_session(
        db,
        session_id=session_id,
        reps=21,
        now=started + timedelta(seconds=30),
    )["ticket"]
    payload = {
        "items": [{"product_id": product.id, "quantity": 1}],
        "pushup_ticket": ticket,
        **_shipping(),
    }
    key = "discount-checkout-key-001"
    first = ShopService(db).checkout(None, idempotency_key=key, **payload)
    replay = ShopService(db).checkout(None, idempotency_key=key, **payload)
    assert replay["id"] == first["id"]
    assert first["discount_percent"] == 10
    db.refresh(product)
    assert product.stock_qty == 2
    assert db.query(ShopOrder).count() == 1


def test_failed_code_completion_removes_generated_plan(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(get_settings(), "require_redeem_code_for_generate", True)
    db = _session()
    code = RedeemCodeService(db).create_batch(
        admin_user_id=USER_ID, qty=1
    )["codes"][0]["code"]
    created: dict[str, int] = {}

    def generate(*_args, **_kwargs):
        now = datetime.now(UTC)
        plan = UserDailyPlan(
            title_vi="Must be rolled back",
            source="ai",
            created_at=now,
            updated_at=now,
        )
        db.add(plan)
        db.flush()
        created["plan_id"] = plan.id
        return {
            "plan_id": plan.id,
            "share_token": "temporary",
            "plan": {"id": plan.id, "title_vi": plan.title_vi},
        }

    monkeypatch.setattr(ai_routes, "generate_workout", generate)
    monkeypatch.setattr(RedeemCodeService, "complete", lambda *_args, **_kwargs: False)
    with pytest.raises(ConflictError):
        ai_routes.generate_workout_schedule(
            _request(code), request=_http_request(), db=db, user=None
        )
    assert db.get(UserDailyPlan, created["plan_id"]) is None
