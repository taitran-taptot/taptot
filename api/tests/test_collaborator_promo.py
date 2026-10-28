"""Collaborator promo codes: stacking, snapshots, and redacted order views."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import pytest

from app.core.database import get_db
from app.core.exceptions import BadRequestError, ConflictError
from app.core.pagination import PaginationParams
from app.core.security import Role, create_access_token, hash_password
from app.main import create_app
from app.models.base import Base
from app.models.entities import CollaboratorPromo, ShopOrder, ShopProduct, User, UserProfile
from app.services.collaborator_promo_service import CollaboratorPromoService, merchandise_discounts
from app.services.pushup_challenge import finish_session, start_session
from app.services.shop_service import ShopService


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _user(db: Session, *, email: str, role: str) -> User:
    now = datetime.now(UTC)
    user = User(
        id=str(uuid4()),
        email=email,
        password_hash="x",
        display_name=email.split("@")[0],
        role=role,
        created_at=now,
    )
    db.add(user)
    db.add(UserProfile(user_id=user.id, experience_level="beginner", updated_at=now))
    db.commit()
    db.refresh(user)
    return user


def _promo(db: Session, user: User, *, percent: int = 10, code: str | None = "CTV-ABC234") -> CollaboratorPromo:
    row = CollaboratorPromo(
        user_id=user.id,
        code=code,
        discount_percent=percent,
        created_at=datetime.now(UTC),
        code_created_at=datetime.now(UTC) if code else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _product(db: Session, *, price: int = 100_000) -> ShopProduct:
    now = datetime.now(UTC)
    row = ShopProduct(
        slug=f"promo-{price}-{uuid4().hex[:6]}",
        name_vi="Tạ tay",
        description_vi=None,
        price_vnd=price,
        stock_qty=5,
        image_url=None,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


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


def _pushup_ticket(db: Session) -> str:
    started = datetime.now(UTC)
    sid = start_session(db, now=started)["session_id"]
    return finish_session(db, session_id=sid, reps=25, now=started + timedelta(seconds=30))["ticket"]


def test_discounts_stack_on_merchandise_and_do_not_go_below_zero():
    assert merchandise_discounts(100_000, 10, 10) == (10_000, 10_000)
    assert merchandise_discounts(100_000, 15, 100) == (15_000, 85_000)


def test_checkout_stacks_event_and_promo_and_snapshots_percent():
    db = _session()
    buyer = _user(db, email="buyer@test.com", role="user")
    ctv = _user(db, email="ctv@test.com", role="ctv")
    promo = _promo(db, ctv, percent=10)
    product = _product(db)
    ticket = _pushup_ticket(db)
    service = ShopService(db)
    service.add_to_cart(buyer.id, product.id, 1)
    order = service.checkout(buyer.id, pushup_ticket=ticket, promo_code="ctv-abc234", **_ship())
    assert order["discount_percent"] == 10
    assert order["discount_vnd"] == 10_000
    assert order["promo_code"] == "CTV-ABC234"
    assert order["promo_percent"] == 10
    assert order["promo_discount_vnd"] == 10_000
    assert order["total_vnd"] == 80_000

    CollaboratorPromoService(db).update_account(ctv.id, discount_percent=25)
    service.add_to_cart(buyer.id, product.id, 1)
    later = service.checkout(buyer.id, promo_code=promo.code, **_ship(phone="0912345678"))
    assert later["promo_percent"] == 25
    assert later["promo_discount_vnd"] == 25_000
    assert later["discount_vnd"] == 0
    assert later["total_vnd"] == 75_000

    db.refresh(db.get(ShopOrder, order["id"]))
    first = db.get(ShopOrder, order["id"])
    assert first.promo_percent == 10
    assert first.promo_discount_vnd == 10_000


def test_unknown_promo_is_rejected_without_touching_stock():
    db = _session()
    product = _product(db)
    service = ShopService(db)
    with pytest.raises(BadRequestError, match="Mã giảm giá không hợp lệ"):
        service.checkout(
            None,
            promo_code="CTV-NOPE12",
            items=[{"product_id": product.id, "quantity": 1}],
            **_ship(),
        )
    db.refresh(product)
    assert product.stock_qty == 5
    assert db.query(ShopOrder).count() == 0


def test_cancelled_orders_stay_visible_but_leave_the_totals():
    db = _session()
    ctv = _user(db, email="ctv@test.com", role="ctv")
    _promo(db, ctv, code="CTV-KEEP22")
    product = _product(db)
    service = ShopService(db)
    order = service.checkout(
        None,
        promo_code="CTV-KEEP22",
        items=[{"product_id": product.id, "quantity": 1}],
        **_ship(),
    )
    service.update_order_status(order["id"], "cancelled")
    stats = CollaboratorPromoService(db).list_accounts()["items"][0]
    assert stats["order_count"] == 0
    assert stats["discount_vnd"] == 0
    listed = CollaboratorPromoService(db).orders_for(
        ctv.id, PaginationParams(page=1, page_size=20), full=False
    )
    assert listed["total"] == 1
    assert listed["items"][0]["order_status"] == "cancelled"
    assert "phone" not in listed["items"][0]
    assert "ward_name" not in listed["items"][0]
    assert "address_line" not in listed["items"][0]
    assert listed["items"][0]["province_name"] == "Ha Noi"
    assert listed["items"][0]["recipient_name"] == "Nguyen Van A"


def test_period_stats_follow_vietnam_time_and_skip_cancelled():
    db = _session()
    ctv = _user(db, email="ctv@test.com", role="ctv")
    _promo(db, ctv, code="CTV-STAT10")
    product = _product(db)
    shop = ShopService(db)
    kept = shop.checkout(None, promo_code="CTV-STAT10", items=[{"product_id": product.id, "quantity": 1}], **_ship())
    cancelled = shop.checkout(
        None, promo_code="CTV-STAT10", items=[{"product_id": product.id, "quantity": 1}], **_ship(phone="0911111111")
    )
    earlier = shop.checkout(
        None, promo_code="CTV-STAT10", items=[{"product_id": product.id, "quantity": 1}], **_ship(phone="0922222222")
    )
    shop.update_order_status(cancelled["id"], "cancelled")
    shop.update_order_status(kept["id"], "completed")
    open_order = shop.checkout(
        None, promo_code="CTV-STAT10", items=[{"product_id": product.id, "quantity": 1}], **_ship(phone="0933333333")
    )
    for order_id, when in (
        (kept["id"], datetime(2026, 10, 28, 4, 0, tzinfo=UTC)),
        (cancelled["id"], datetime(2026, 10, 28, 5, 0, tzinfo=UTC)),
        (open_order["id"], datetime(2026, 10, 28, 6, 0, tzinfo=UTC)),
        (earlier["id"], datetime(2025, 12, 31, 16, 0, tzinfo=UTC)),
    ):
        row = db.get(ShopOrder, order_id)
        assert row is not None
        row.created_at = when
    db.commit()

    service = CollaboratorPromoService(db)
    page = PaginationParams(page=1, page_size=10)
    day = service.period_stats(ctv.id, "day", "2026-10-28", page)
    assert day["order_count"] == 2
    assert day["discount_vnd"] == 10_000
    assert day["total_vnd"] == 90_000
    assert day["orders"]["total"] == 3
    newest_first = [item["id"] for item in day["orders"]["items"]]
    oldest_first = [
        item["id"] for item in service.period_stats(ctv.id, "day", "2026-10-28", page, sort="asc")["orders"]["items"]
    ]
    assert oldest_first == list(reversed(newest_first))
    kept_code = db.get(ShopOrder, kept["id"]).public_code
    found = service.period_stats(ctv.id, "day", "2026-10-28", page, code=kept_code)
    assert found["orders"]["total"] == 1
    completed = service.period_stats(ctv.id, "day", "2026-10-28", page, status="completed")
    assert completed["orders"]["total"] == 1
    assert completed["orders"]["items"][0]["order_status"] == "completed"
    assert completed["order_count"] == 2
    assert found["orders"]["items"][0]["public_code"] == kept_code
    assert found["order_count"] == 2
    assert service.period_stats(ctv.id, "month", "2026-10", page)["order_count"] == 2
    assert service.period_stats(ctv.id, "year", "2025", page)["order_count"] == 1
    assert service.period_stats(ctv.id, "year", "2026", page)["total_vnd"] == 90_000


def test_assign_code_once_and_reject_duplicates():
    db = _session()
    ctv = _user(db, email="ctv@test.com", role="ctv")
    other = _user(db, email="other@test.com", role="ctv")
    _promo(db, ctv, code=None)
    _promo(db, other, code=None)
    service = CollaboratorPromoService(db)
    created = service.assign_code(ctv.id, " magiamgia ")
    assert created["code"] == "MAGIAMGIA"
    with pytest.raises(ConflictError, match="đã có mã giảm giá"):
        service.assign_code(ctv.id, "KHAC1234")
    with pytest.raises(ConflictError, match="đã được dùng"):
        service.assign_code(other.id, "magiamgia")
    with pytest.raises(BadRequestError, match="không hợp lệ"):
        service.assign_code(other.id, "MÃ")


def _app_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    def override_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_db
    return TestClient(app), SessionLocal


def _bearer(user_id: str, role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id, role)}"}


def test_ctv_login_and_order_redaction():
    client, SessionLocal = _app_client()
    db = SessionLocal()
    now = datetime.now(UTC)
    admin = User(
        id=str(uuid4()),
        email="admin@example.com",
        password_hash=hash_password("Secret12"),
        display_name="Admin",
        role=Role.ADMIN.value,
        created_at=now,
        email_verified_at=now,
    )
    db.add(admin)
    db.commit()
    admin_id = admin.id
    db.close()

    created = client.post(
        "/api/v1/admin/collaborators",
        headers=_bearer(admin_id, Role.ADMIN.value),
        json={
            "email": "lan@example.com",
            "password": "Secret12",
            "display_name": "Lan",
            "discount_percent": 10,
        },
    )
    assert created.status_code == 201, created.text
    ctv_id = created.json()["id"]

    login = client.post("/api/v1/auth/login", json={"email": "lan@example.com", "password": "Secret12"})
    assert login.status_code == 200, login.text
    assert login.json()["role"] == "ctv"
    client.cookies.clear()

    blocked = client.get("/api/v1/admin/collaborators", headers=_bearer(ctv_id, Role.CTV.value))
    assert blocked.status_code == 403

    denied = client.post("/api/v1/collaborator/promo/code", headers=_bearer(ctv_id, Role.CTV.value))
    assert denied.status_code == 404
    generated = client.post(
        f"/api/v1/admin/collaborators/{ctv_id}/code",
        headers=_bearer(admin_id, Role.ADMIN.value),
        json={"code": "lan10"},
    )
    assert generated.status_code == 201, generated.text
    code = generated.json()["code"]
    assert code == "LAN10"
    again = client.post(
        f"/api/v1/admin/collaborators/{ctv_id}/code",
        headers=_bearer(admin_id, Role.ADMIN.value),
        json={"code": "LAN11"},
    )
    assert again.status_code == 409

    preview = client.get(f"/api/v1/shop/promo-codes/{code}")
    assert preview.status_code == 200
    assert preview.json()["discount_percent"] == 10

    db = SessionLocal()
    product = _product(db)
    ShopService(db).checkout(
        None,
        promo_code=code,
        items=[{"product_id": product.id, "quantity": 1}],
        **_ship(),
    )
    db.close()

    own = client.get("/api/v1/collaborator/promo", headers=_bearer(ctv_id, Role.CTV.value))
    assert own.status_code == 200, own.text
    body = own.json()
    assert body["order_count"] == 1
    assert body["discount_vnd"] == 0
    order = body["orders"]["items"][0]
    assert order["recipient_name"] == "Nguyen Van A"
    assert order["province_name"] == "Ha Noi"
    assert order["district_name"] == "Ba Dinh"
    assert order["items"][0]["name_vi"] == "Tạ tay"
    assert "phone" not in order
    assert "ward_name" not in order
    assert "address_line" not in order
    raw = own.text
    assert "0901234567" not in raw
    assert "Phuc Xa" not in raw
    assert "12 Pho Hue" not in raw

    admin_orders = client.get(
        f"/api/v1/admin/collaborators/{ctv_id}/orders",
        headers=_bearer(admin_id, Role.ADMIN.value),
    )
    assert admin_orders.status_code == 200, admin_orders.text
    full = admin_orders.json()["items"][0]
    assert full["phone"] == "0901234567"
    assert full["ward_name"] == "Phuc Xa"
    assert full["address_line"] == "12 Pho Hue"

    other = client.post(
        "/api/v1/admin/collaborators",
        headers=_bearer(admin_id, Role.ADMIN.value),
        json={
            "email": "minh@example.com",
            "password": "Secret12",
            "display_name": "Minh",
            "discount_percent": 10,
        },
    )
    assert other.status_code == 201, other.text
    other_orders = client.get(
        f"/api/v1/admin/collaborators/{other.json()['id']}/orders",
        headers=_bearer(ctv_id, Role.CTV.value),
    )
    assert other_orders.status_code == 403
    own_again = client.get("/api/v1/collaborator/promo", headers=_bearer(ctv_id, Role.CTV.value))
    assert own_again.json()["code"] == code
    assert own_again.json()["email"] == "lan@example.com"


def test_admin_updates_and_deletes_collaborator():
    client, SessionLocal = _app_client()
    db = SessionLocal()
    now = datetime.now(UTC)
    admin = User(
        id=str(uuid4()),
        email="admin@example.com",
        password_hash=hash_password("Secret12"),
        display_name="Admin",
        role=Role.ADMIN.value,
        created_at=now,
        email_verified_at=now,
    )
    db.add(admin)
    db.commit()
    admin_id = admin.id
    db.close()
    headers = _bearer(admin_id, Role.ADMIN.value)

    created = client.post(
        "/api/v1/admin/collaborators",
        headers=headers,
        json={
            "email": "lan@example.com",
            "password": "Secret12",
            "display_name": "Lan",
            "discount_percent": 10,
        },
    )
    assert created.status_code == 201, created.text
    ctv_id = created.json()["id"]

    updated = client.patch(
        f"/api/v1/admin/collaborators/{ctv_id}",
        headers=headers,
        json={
            "display_name": "Lan Mới",
            "email": "lan.moi@example.com",
            "password": "MatKhau99",
            "discount_percent": 15,
        },
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["display_name"] == "Lan Mới"
    assert body["email"] == "lan.moi@example.com"
    assert body["discount_percent"] == 15

    client.cookies.clear()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "lan.moi@example.com", "password": "MatKhau99"},
    )
    assert login.status_code == 200, login.text
    client.cookies.clear()
    old = client.post(
        "/api/v1/auth/login",
        json={"email": "lan@example.com", "password": "Secret12"},
    )
    assert old.status_code == 401

    clash = client.patch(
        f"/api/v1/admin/collaborators/{ctv_id}",
        headers=headers,
        json={"email": "admin@example.com"},
    )
    assert clash.status_code == 409

    forbidden = client.delete(
        f"/api/v1/admin/collaborators/{ctv_id}",
        headers=_bearer(ctv_id, Role.CTV.value),
    )
    assert forbidden.status_code == 403

    generated = client.post(
        f"/api/v1/admin/collaborators/{ctv_id}/code",
        headers=headers,
        json={"code": "LANMOI"},
    )
    assert generated.status_code == 201, generated.text
    code = generated.json()["code"]

    deleted = client.delete(f"/api/v1/admin/collaborators/{ctv_id}", headers=headers)
    assert deleted.status_code == 204, deleted.text

    listed = client.get("/api/v1/admin/collaborators", headers=headers)
    assert listed.status_code == 200
    assert all(item["id"] != ctv_id for item in listed.json()["items"])
    preview = client.get(f"/api/v1/shop/promo-codes/{code}")
    assert preview.status_code == 400
    missing = client.delete(f"/api/v1/admin/collaborators/{ctv_id}", headers=headers)
    assert missing.status_code == 404


def _staff_user(db: Session, *, email: str, role: str, password: str = "Secret12") -> User:
    now = datetime.now(UTC)
    user = User(
        id=str(uuid4()),
        email=email,
        password_hash=hash_password(password),
        display_name=email.split("@")[0],
        role=role,
        created_at=now,
        email_verified_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_http_promo_stats_preview_and_role_gates():
    client, SessionLocal = _app_client()
    db = SessionLocal()
    admin = _staff_user(db, email="admin@example.com", role=Role.ADMIN.value)
    hlv = _staff_user(db, email="hlv@example.com", role=Role.HLV.value)
    admin_id, hlv_id = admin.id, hlv.id
    db.close()

    created = client.post(
        "/api/v1/admin/collaborators",
        headers=_bearer(admin_id, Role.ADMIN.value),
        json={
            "email": "ctv-http@example.com",
            "password": "Secret12",
            "display_name": "CtvHttp",
            "discount_percent": 10,
        },
    )
    assert created.status_code == 201, created.text
    ctv_id = created.json()["id"]
    assigned = client.post(
        f"/api/v1/admin/collaborators/{ctv_id}/code",
        headers=_bearer(admin_id, Role.ADMIN.value),
        json={"code": "http10"},
    )
    assert assigned.status_code == 201, assigned.text
    code = assigned.json()["code"]
    assert code == "HTTP10"

    preview = client.get(f"/api/v1/shop/promo-codes/{code}")
    assert preview.status_code == 200
    assert preview.json() == {"code": "HTTP10", "discount_percent": 10}
    missing = client.get("/api/v1/shop/promo-codes/NOPE12")
    assert missing.status_code == 400

    db = SessionLocal()
    product = _product(db, price=100_000)
    product_id = product.id
    db.close()

    guest_order = client.post(
        "/api/v1/shop/orders",
        headers={"Idempotency-Key": "guest-no-promo-key-01"},
        json={
            "items": [{"product_id": product_id, "quantity": 1}],
            **_ship(),
        },
    )
    assert guest_order.status_code == 201, guest_order.text
    body = guest_order.json()
    assert body.get("promo_code") in (None, "")
    assert body["promo_percent"] in (None, 0)
    assert body["promo_discount_vnd"] in (None, 0)
    assert body["total_vnd"] == 100_000

    with_promo = client.post(
        "/api/v1/shop/orders",
        headers={"Idempotency-Key": "guest-with-promo-key-1"},
        json={
            "items": [{"product_id": product_id, "quantity": 1}],
            "promo_code": "http10",
            **_ship(phone="0912345678"),
        },
    )
    assert with_promo.status_code == 201, with_promo.text
    assert with_promo.json()["promo_code"] == "HTTP10"
    assert with_promo.json()["promo_percent"] == 10
    assert with_promo.json()["promo_discount_vnd"] == 10_000
    assert with_promo.json()["total_vnd"] == 90_000

    ctv_h = _bearer(ctv_id, Role.CTV.value)
    hlv_h = _bearer(hlv_id, Role.HLV.value)
    stats = client.get(
        "/api/v1/collaborator/promo/stats",
        headers=ctv_h,
        params={"period": "day", "on": "2026-10-28"},
    )
    assert stats.status_code == 200, stats.text
    hlv_stats = client.get(
        "/api/v1/collaborator/promo/stats",
        headers=hlv_h,
        params={"period": "day", "on": "2026-10-28"},
    )
    assert hlv_stats.status_code == 403
    assert client.get("/api/v1/my-plans", headers=ctv_h).status_code == 403
    assert client.get("/api/v1/admin/collaborators", headers=ctv_h).status_code == 403
    assert client.get("/api/v1/admin/shop/orders", headers=ctv_h).status_code == 403
    assert client.get("/api/v1/admin/stats", headers=ctv_h).status_code == 403
    staff_create = client.post(
        "/api/v1/admin/staff",
        headers=_bearer(admin_id, Role.ADMIN.value),
        json={
            "email": "newhlv@example.com",
            "password": "Secret12",
            "display_name": "HlvMoi",
            "role": "ctv",
        },
    )
    assert staff_create.status_code in (400, 403, 422)
