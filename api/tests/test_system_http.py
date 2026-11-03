"""HTTP gaps: password reset, cart merge, media upload, activation covers, public catalog.

Bank transfer, VietQR, and payment-info are intentionally not covered here.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import Role, create_access_token, hash_password
from app.main import create_app
from app.models.base import Base
from app.models.entities import Exercise, Food, MuscleGroup, ProductRedeemCode, ShopProduct, User
from app.services.shop_service import ShopService


def _app_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_db
    return TestClient(app), Session


def _add_user(Session, *, email: str, role: str, password: str = "Secret12") -> str:
    uid = str(uuid4())
    db = Session()
    db.add(
        User(
            id=uid,
            email=email,
            password_hash=hash_password(password),
            display_name=email.split("@")[0],
            role=role,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    db.close()
    return uid


def _bearer(user_id: str, role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id, role)}"}


def _product(Session, *, stock: int, name: str = "Day khang luc") -> int:
    now = datetime.now(UTC)
    db = Session()
    row = ShopProduct(
        slug=f"kit-{stock}-{name}",
        name_vi=name,
        description_vi=None,
        price_vnd=500_000,
        stock_qty=stock,
        image_url=None,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    product_id = row.id
    db.close()
    return product_id


def _console_mail(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.v1 import auth as auth_routes
    from app.services import email_service

    monkeypatch.setattr(auth_routes.settings, "debug", True, raising=False)
    monkeypatch.setattr(auth_routes.settings, "email_provider", "console", raising=False)
    monkeypatch.setattr(email_service.settings, "debug", True, raising=False)
    monkeypatch.setattr(email_service.settings, "email_provider", "console", raising=False)


def test_public_register_is_closed():
    client, _Session = _app_client()
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "new@example.com",
            "password": "Secret12",
            "display_name": "New",
        },
    )
    assert res.status_code == 403, res.text
    assert "đóng" in res.json()["detail"].lower()


def test_forgot_reset_and_login(monkeypatch: pytest.MonkeyPatch):
    _console_mail(monkeypatch)
    client, Session = _app_client()
    email = "hlv-reset@example.com"
    _add_user(Session, email=email, role=Role.HLV.value, password="Secret12")

    forgot = client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert forgot.status_code == 200, forgot.text
    reset_url = forgot.json()["reset_url"]
    assert reset_url
    token = reset_url.rstrip("/").split("token=")[-1]
    assert token and token != reset_url

    unknown = client.post("/api/v1/auth/forgot-password", json={"email": "missing@example.com"})
    assert unknown.status_code == 200, unknown.text
    assert unknown.json().get("reset_url") in (None, "")

    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "Newpass12"},
    )
    assert reset.status_code == 200, reset.text

    old_login = client.post("/api/v1/auth/login", json={"email": email, "password": "Secret12"})
    assert old_login.status_code == 401, old_login.text
    new_login = client.post("/api/v1/auth/login", json={"email": email, "password": "Newpass12"})
    assert new_login.status_code == 200, new_login.text
    assert new_login.json()["role"] == "hlv"

    bad = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "not-a-real-token", "new_password": "Newpass12"},
    )
    assert bad.status_code == 400, bad.text


def test_verify_email_accepts_valid_token_and_rejects_bad(monkeypatch: pytest.MonkeyPatch):
    _console_mail(monkeypatch)
    client, Session = _app_client()
    email = "hlv-verify@example.com"
    user_id = _add_user(Session, email=email, role=Role.HLV.value)

    from app.services.auth_service import AuthService

    db = Session()
    user = db.get(User, user_id)
    token = AuthService(db).resend_verification(user_id)
    db.close()

    ok = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert ok.status_code == 200, ok.text
    assert ok.json()["email_verified"] is True
    assert ok.json()["email"] == email

    again = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert again.status_code == 400, again.text
    bad = client.post("/api/v1/auth/verify-email", json={"token": "nope"})
    assert bad.status_code == 400, bad.text


def test_cart_merge_adds_guest_lines_without_exceeding_stock():
    client, Session = _app_client()
    user_id = _add_user(Session, email="hlv-cart@example.com", role=Role.HLV.value)
    limited = _product(Session, stock=2, name="Gioi han")
    open_item = _product(Session, stock=4, name="Con hang")
    headers = _bearer(user_id, Role.HLV.value)

    seeded = client.post(
        "/api/v1/shop/cart/items",
        json={"product_id": limited, "quantity": 1},
        headers=headers,
    )
    assert seeded.status_code == 200, seeded.text

    merged = client.post(
        "/api/v1/shop/cart/merge",
        json={
            "items": [
                {"product_id": limited, "quantity": 5},
                {"product_id": open_item, "quantity": 2},
                {"product_id": 99999, "quantity": 1},
            ]
        },
        headers=headers,
    )
    assert merged.status_code == 200, merged.text
    by_id = {item["product_id"]: item for item in merged.json()["items"]}
    assert by_id[limited]["quantity"] == 1
    assert by_id[limited]["quantity"] <= by_id[limited]["stock_qty"]
    assert by_id[open_item]["quantity"] == 2
    assert 99999 not in by_id


def test_media_upload_rejects_guest_and_accepts_staff(monkeypatch: pytest.MonkeyPatch):
    async def _fake_save(self, file, subdir="media"):
        content = await file.read()
        return {
            "filename": "a.png",
            "url": "/media/a.png",
            "size_bytes": len(content),
            "content_type": file.content_type,
        }

    monkeypatch.setattr("app.api.v1.media.MediaService.save", _fake_save)
    client, Session = _app_client()
    guest = client.post(
        "/api/v1/media/upload",
        files={"file": ("a.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )
    assert guest.status_code == 401, guest.text

    user_id = _add_user(Session, email="hlv-media@example.com", role=Role.HLV.value)
    ok = client.post(
        "/api/v1/media/upload",
        files={"file": ("a.png", b"\x89PNG\r\n\x1a\n", "image/png")},
        headers=_bearer(user_id, Role.HLV.value),
    )
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["url"] == "/media/a.png"
    assert body["size_bytes"] > 0


def _cod_order(Session) -> tuple[int, int]:
    product_id = _product(Session, stock=3, name="COD cover")
    db = Session()
    order = ShopService(db).checkout(
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
        items=[{"product_id": product_id, "quantity": 1}],
    )
    code = db.query(ProductRedeemCode).filter(ProductRedeemCode.order_id == order["id"]).one()
    order_id = order["id"]
    code_id = code.id
    db.close()
    return order_id, code_id


def test_admin_activation_cover_routes_return_pdf_and_png():
    client, Session = _app_client()
    order_id, code_id = _cod_order(Session)
    admin_id = _add_user(Session, email="admin-cover@example.com", role=Role.ADMIN.value)
    hlv_id = _add_user(Session, email="hlv-cover@example.com", role=Role.HLV.value)
    admin = _bearer(admin_id, Role.ADMIN.value)

    denied = client.get(
        f"/api/v1/admin/shop/orders/{order_id}/activation-covers.pdf",
        headers=_bearer(hlv_id, Role.HLV.value),
    )
    assert denied.status_code == 403, denied.text

    pdf = client.get(f"/api/v1/admin/shop/orders/{order_id}/activation-covers.pdf", headers=admin)
    assert pdf.status_code == 200, pdf.text
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content.startswith(b"%PDF")

    png = client.get(f"/api/v1/admin/shop/redeem-codes/{code_id}/cover.png", headers=admin)
    assert png.status_code == 200, png.text
    assert png.headers["content-type"].startswith("image/png")
    assert png.content.startswith(b"\x89PNG")


def test_public_catalog_is_readable_without_login():
    client, Session = _app_client()
    now = datetime.now(UTC)
    product_id = _product(Session, stock=5, name="Kit cong khai")
    db = Session()
    muscle = MuscleGroup(slug="nguc", name_vi="Nguc", sort_order=1)
    db.add(muscle)
    db.flush()
    db.add(
        Exercise(
            name_vi="Hit dat",
            name_en="Push up",
            muscle_group_id=muscle.id,
            exercise_type="main",
            difficulty=1,
            secondary_muscles=[],
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    db.add(
        Food(
            slug="uc-ga",
            name_vi="Uc ga",
            serving_size="100g",
            calories=110,
            protein_g=23,
            carbs_g=0,
            fat_g=2,
            tags=[],
            macro_roles=[],
            meal_slots=[],
            status="active",
            created_at=now,
        )
    )
    db.commit()
    db.close()

    products = client.get("/api/v1/shop/products")
    assert products.status_code == 200, products.text
    product_body = products.json()
    assert product_body["total"] >= 1
    assert any(item["id"] == product_id for item in product_body["items"])

    exercises = client.get("/api/v1/search/exercises", params={"q": "Hit dat"})
    assert exercises.status_code == 200, exercises.text
    exercise_body = exercises.json()
    assert exercise_body["total"] >= 1
    assert any(item["name_vi"] == "Hit dat" for item in exercise_body["items"])

    foods = client.get("/api/v1/search/foods", params={"q": "Uc ga"})
    assert foods.status_code == 200, foods.text
    food_body = foods.json()
    assert food_body["total"] >= 1
    assert any(item["name_vi"] == "Uc ga" for item in food_body["items"])
