"""Gift codes on product stickers: lookup, reservation and required generation access."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.v1 import ai as ai_routes
from app.api.v1.ai import WorkoutScheduleRequest
from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.models.base import Base
from app.models.entities import ShopProduct, User, UserDailyPlan
from app.services.momo import IPN_SIGN_KEYS, sign_create, sign_ipn, signature_matches
from app.services.payment_service import PaymentService
from app.services.plan_service import PlanService
from app.services.redeem_code_service import (
    RedeemCodeService,
    gift_landing_url,
    is_test_code,
    normalize_code,
    new_code,
)


ADMIN_ID = "11111111-1111-1111-1111-111111111111"


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(
        User(
            id=ADMIN_ID,
            email="admin@test.com",
            password_hash="x",
            display_name="Admin",
            role="admin",
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    return db


def _product(db: Session) -> ShopProduct:
    now = datetime.now(UTC)
    row = ShopProduct(
        slug="day-khang-luc",
        name_vi="Dây kháng lực",
        description_vi=None,
        price_vnd=99000,
        stock_qty=10,
        image_url=None,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_normalize_code_formats():
    assert normalize_code("tt-7k3m-p2qx") == "TT-7K3M-P2QX"
    assert normalize_code("tt7k3mp2qx") == "TT-7K3M-P2QX"
    assert normalize_code("nope") is None
    assert normalize_code("TT-0000-IIII") is None
    assert normalize_code("1") is None
    assert is_test_code("1") is True
    assert is_test_code("01") is False


def test_normalize_generated_roundtrip():
    for _ in range(20):
        code = new_code()
        assert normalize_code(code) == code
        assert normalize_code(code.replace("-", "").lower()) == code


def test_lookup_unused_and_invalid():
    db = _session()
    product = _product(db)
    service = RedeemCodeService(db)
    batch = service.create_batch(admin_user_id=ADMIN_ID, qty=2, product_id=product.id, note="Lô T9")
    code = batch["codes"][0]["code"]
    hit = service.lookup(code)
    assert hit["valid"] is True
    assert hit["status"] == "unused"
    assert hit["product_name_vi"] == "Dây kháng lực"
    miss = service.lookup("TT-AAAA-AAAA")
    assert miss["valid"] is False
    assert miss["status"] == "invalid"


def test_redeem_burns_once():
    db = _session()
    service = RedeemCodeService(db)
    batch = service.create_batch(admin_user_id=ADMIN_ID, qty=1, note="1 tem")
    code = batch["codes"][0]["code"]
    assert service.try_redeem(code, plan_id=101, user_id=None) is True
    assert service.try_redeem(code, plan_id=102, user_id=None) is False
    again = service.lookup(code)
    assert again["valid"] is False
    assert again["status"] == "redeemed"


def test_race_unused_only_one_wins():
    db = _session()
    service = RedeemCodeService(db)
    batch = service.create_batch(admin_user_id=ADMIN_ID, qty=1)
    code = batch["codes"][0]["code"]
    first = service.try_redeem(code, plan_id=1, user_id=ADMIN_ID)
    second = service.try_redeem(code, plan_id=2, user_id=ADMIN_ID)
    assert first is True
    assert second is False
    row_status = service.lookup(code)["status"]
    assert row_status == "redeemed"


def test_reservation_blocks_second_request_and_can_be_released():
    db = _session()
    service = RedeemCodeService(db)
    batch = service.create_batch(admin_user_id=ADMIN_ID, qty=1)
    code = batch["codes"][0]["code"]

    first_token = service.reserve(code)
    assert first_token
    assert service.reserve(code) is None
    processing = service.lookup(code)
    assert processing["valid"] is False
    assert processing["status"] == "processing"

    assert service.release(code, first_token) is True
    assert service.lookup(code)["valid"] is True


def test_invalid_code_does_not_redeem():
    db = _session()
    service = RedeemCodeService(db)
    assert service.try_redeem("not-a-code", plan_id=9, user_id=None) is False
    assert service.try_redeem("TT-ZZZZ-ZZZZ", plan_id=9, user_id=None) is False


def test_print_html_includes_code_and_qr():
    db = _session()
    service = RedeemCodeService(db)
    batch = service.create_batch(admin_user_id=ADMIN_ID, qty=1, note="In thử")
    code = batch["codes"][0]["code"]
    html = service.print_html(batch["id"])
    assert code in html
    assert "data:image/png;base64," in html
    assert "dùng 1 lần" in html
    assert f"/batdau/{code}" in gift_landing_url(code)


def test_void_unused_only():
    db = _session()
    service = RedeemCodeService(db)
    batch = service.create_batch(admin_user_id=ADMIN_ID, qty=1)
    code_id = batch["codes"][0]["id"]
    code = batch["codes"][0]["code"]
    voided = service.void_code(code_id)
    assert voided["status"] == "void"
    assert service.lookup(code)["valid"] is False
    assert service.try_redeem(code, plan_id=1, user_id=None) is False


def _generation_request(code: str | None) -> WorkoutScheduleRequest:
    return WorkoutScheduleRequest(
        age=25,
        height_cm=170,
        weight_kg=65,
        redeem_code=code,
    )


def test_generation_requires_valid_code(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(get_settings(), "require_redeem_code_for_generate", True)
    db = _session()
    called = False

    def fake_generate(*_args, **_kwargs):
        nonlocal called
        called = True
        return {"plan_id": 1, "plan": {"id": 1}}

    monkeypatch.setattr(ai_routes, "generate_workout", fake_generate)
    with pytest.raises(ForbiddenError):
        ai_routes.generate_workout_schedule(_generation_request(None), db=db, user=None)
    with pytest.raises(ForbiddenError):
        ai_routes.generate_workout_schedule(
            _generation_request("TT-ZZZZ-ZZZZ"),
            db=db,
            user=None,
        )
    assert called is False


def test_free_home_generation_skips_redeem_gate(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(get_settings(), "require_redeem_code_for_generate", True)
    db = _session()
    called = {"n": 0}

    def fake_generate(_db, _user_id, payload):
        called["n"] += 1
        assert payload.get("generation_mode") == "free_home"
        return {"plan_id": 99, "plan": {"id": 99, "title_vi": "Free home", "source": "ai"}}

    monkeypatch.setattr(ai_routes, "generate_workout", fake_generate)
    result = ai_routes.generate_workout_schedule(
        WorkoutScheduleRequest(
            age=25,
            height_cm=170,
            weight_kg=65,
            generation_mode="free_home",
            redeem_code=None,
        ),
        db=db,
        user=None,
    )
    assert called["n"] == 1
    assert result.get("plan_id") == 99
    assert result.get("code_applied") is False


def test_generation_consumes_valid_code(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(get_settings(), "require_redeem_code_for_generate", True)
    db = _session()
    service = RedeemCodeService(db)
    batch = service.create_batch(admin_user_id=ADMIN_ID, qty=1)
    code = batch["codes"][0]["code"]
    monkeypatch.setattr(
        ai_routes,
        "generate_workout",
        lambda *_args, **_kwargs: {
            "plan_id": 101,
            "share_token": "share",
            "plan": {"id": 101, "title_vi": "Lịch", "share_token": "share"},
        },
    )

    result = ai_routes.generate_workout_schedule(
        _generation_request(code),
        db=db,
        user=None,
    )

    assert result["code_applied"] is True
    assert result["view_path"] == f"/lich/{code}"
    assert result["share_token"] == code
    assert result["plan"]["share_token"] == code
    assert service.lookup(code)["status"] == "redeemed"


def test_generation_failure_releases_code(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(get_settings(), "require_redeem_code_for_generate", True)
    db = _session()
    service = RedeemCodeService(db)
    batch = service.create_batch(admin_user_id=ADMIN_ID, qty=1)
    code = batch["codes"][0]["code"]

    def fail_generate(*_args, **_kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(ai_routes, "generate_workout", fail_generate)
    with pytest.raises(BadRequestError):
        ai_routes.generate_workout_schedule(
            _generation_request(code),
            db=db,
            user=None,
        )
    assert service.lookup(code)["valid"] is True


def test_lookup_test_code_is_always_valid():
    db = _session()
    service = RedeemCodeService(db)
    hit = service.lookup("1")
    assert hit["valid"] is True
    assert hit["status"] == "test"
    assert hit["code"] == "1"
    assert service.reserve("1") is None


def test_generation_allows_reusable_test_code(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(get_settings(), "require_redeem_code_for_generate", True)
    db = _session()
    monkeypatch.setattr(
        ai_routes,
        "generate_workout",
        lambda *_args, **_kwargs: {
            "plan_id": 77,
            "share_token": "guest-share",
            "plan": {"id": 77, "title_vi": "Lịch", "share_token": "guest-share"},
        },
    )
    result = ai_routes.generate_workout_schedule(
        _generation_request("1"),
        db=db,
        user=None,
    )
    assert result["code_applied"] is False
    assert result["view_path"] == "/lich/guest-share"
    assert RedeemCodeService(db).lookup("1")["valid"] is True


def test_share_lookup_prefers_redeem_code():
    db = _session()
    service = RedeemCodeService(db)
    batch = service.create_batch(admin_user_id=ADMIN_ID, qty=1)
    code = batch["codes"][0]["code"]
    now = datetime.now(UTC)
    plan = UserDailyPlan(
        title_vi="Lịch tem",
        source="ai",
        share_token="randomShareToken",
        created_at=now,
        updated_at=now,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    assert service.try_redeem(code, plan_id=plan.id, user_id=None) is True
    db.refresh(plan)
    assert plan.share_token == code
    plans = PlanService(db)
    by_code = plans.get_by_share_token(code)
    assert by_code["id"] == plan.id
    assert by_code["share_url_path"] == f"/lich/{code}"
    assert by_code["redeem_code"] == code
    assert by_code["share_token"] == code
    with pytest.raises(NotFoundError):
        plans.get_by_share_token("randomShareToken")


def test_momo_create_signature_is_stable():
    fields = {
        "accessKey": "access",
        "amount": "49000",
        "extraData": "",
        "ipnUrl": "https://api.example/payments/webhook/momo",
        "orderId": "TT-ABC",
        "orderInfo": "Lo trinh 100 ngay TAPTOT",
        "partnerCode": "MOMOIQA420180417",
        "redirectUrl": "https://taptot.vn/batdau",
        "requestId": "TT-ABC-1",
        "requestType": "captureWallet",
    }
    first = sign_create("secret", fields)
    assert first == sign_create("secret", fields)
    assert len(first) == 64
    assert sign_create("secret", {**fields, "amount": "1"}) != first


def test_momo_ipn_signature_roundtrip():
    fields = {
        "accessKey": "access",
        "amount": "49000",
        "extraData": "",
        "message": "Success",
        "orderId": "TT-ABC",
        "orderInfo": "Lo trinh",
        "orderType": "momo_wallet",
        "partnerCode": "MOMOIQA420180417",
        "payType": "qr",
        "requestId": "req",
        "responseTime": "1710000000000",
        "resultCode": 0,
        "transId": "123",
    }
    signature = sign_ipn("secret", fields)
    assert signature_matches("secret", IPN_SIGN_KEYS, fields, signature)
    assert not signature_matches("secret", IPN_SIGN_KEYS, fields, "deadbeef")


def test_stub_checkout_and_generate(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(get_settings(), "require_redeem_code_for_generate", True)
    monkeypatch.setattr(get_settings(), "debug", True)
    monkeypatch.setattr(get_settings(), "app_env", "development")
    monkeypatch.setattr(get_settings(), "momo_partner_code", "")
    monkeypatch.setattr(get_settings(), "momo_access_key", "")
    monkeypatch.setattr(get_settings(), "momo_secret_key", "")
    db = _session()
    payments = PaymentService(db)
    checkout = payments.create_challenge_checkout(None)
    assert checkout["stub"] is True
    assert checkout["pay_url"].endswith(f"/batdau?paid={checkout['external_id']}&stub=1")

    status = payments.simulate_challenge_success(checkout["external_id"])
    assert status["status"] == "completed"
    token = status["entitlement_token"]
    assert token

    monkeypatch.setattr(
        ai_routes,
        "generate_workout",
        lambda *_args, **_kwargs: {
            "plan_id": 9,
            "share_token": "paid-share",
            "plan": {"id": 9, "title_vi": "Lịch", "share_token": "paid-share"},
        },
    )
    result = ai_routes.generate_workout_schedule(
        WorkoutScheduleRequest(
            age=25,
            height_cm=170,
            weight_kg=65,
            payment_entitlement=token,
        ),
        db=db,
        user=None,
    )
    assert result["code_applied"] is False
    assert result["view_path"] == "/lich/paid-share"

    with pytest.raises(ForbiddenError):
        ai_routes.generate_workout_schedule(
            WorkoutScheduleRequest(
                age=25,
                height_cm=170,
                weight_kg=65,
                payment_entitlement=token,
            ),
            db=db,
            user=None,
        )
