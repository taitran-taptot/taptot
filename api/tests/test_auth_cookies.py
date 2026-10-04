"""Cookie sessions, CSRF origin check, and admin step-up."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.migrations.ensures import ensure_user_roles_normalized
from app.core.security import Role, create_access_token, hash_password
from app.main import create_app
from app.models.base import Base
from app.models.entities import User
from app.schemas.auth import RegisterRequest

_FOOD_BODY = {
    "name_vi": "Bánh test cookie",
    "kcal_100g": 100,
    "protein_100g": 2,
    "carbs_100g": 20,
    "fat_100g": 1,
}


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


def _cookies(response) -> str:
    values = response.headers.get_list("set-cookie")
    return "\n".join(values)


def test_role_enum_has_no_trainer():
    assert Role.HLV.value == "hlv"
    assert Role.ADMIN.value == "admin"
    assert [r.value for r in Role] == ["user", "admin", "hlv"]
    assert not hasattr(Role, "TRAINER")
    assert "role" not in RegisterRequest.model_fields


def test_register_public_is_forbidden():
    client, _ = _app_client()
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "Secret12",
            "display_name": "Người tập",
            "role": "trainer",
        },
    )
    assert res.status_code == 403, res.text
    assert "access_token" not in res.json()
    assert "taptot_access=" not in _cookies(res)


def test_me_without_cookie_is_401():
    client, _ = _app_client()
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_login_sets_cookies_not_jwt_body():
    client, Session = _app_client()
    db = Session()
    db.add(
        User(
            id=str(uuid4()),
            email="login@example.com",
            password_hash=hash_password("Secret12"),
            display_name="Login",
            role=Role.HLV.value,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    db.close()

    res = client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "Secret12"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["email"] == "login@example.com"
    assert "access_token" not in body
    assert "taptot_access=" in _cookies(res)
    assert client.get("/api/v1/auth/me").status_code == 200


def test_csrf_rejects_foreign_origin_with_cookie():
    client, Session = _app_client()
    db = Session()
    db.add(
        User(
            id=str(uuid4()),
            email="csrf@example.com",
            password_hash=hash_password("Secret12"),
            display_name="CSRF",
            role=Role.HLV.value,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    db.close()
    client.post(
        "/api/v1/auth/login",
        json={"email": "csrf@example.com", "password": "Secret12"},
    )
    res = client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "https://evil.example"},
    )
    assert res.status_code == 403
    assert res.json().get("code") == "csrf"


def test_hlv_cannot_write_admin_foods():
    client, Session = _app_client()
    db = Session()
    db.add(
        User(
            id=str(uuid4()),
            email="hlv@example.com",
            password_hash=hash_password("Secret12"),
            display_name="HLV",
            role=Role.HLV.value,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    db.close()
    client.post("/api/v1/auth/login", json={"email": "hlv@example.com", "password": "Secret12"})
    res = client.post("/api/v1/admin/foods", json=_FOOD_BODY)
    assert res.status_code == 403


def test_admin_cookie_write_requires_step_up_then_succeeds():
    client, Session = _app_client()
    db = Session()
    db.add(
        User(
            id=str(uuid4()),
            email="admin@example.com",
            password_hash=hash_password("Secret12"),
            display_name="Admin",
            role=Role.ADMIN.value,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    db.close()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Secret12"},
    )
    assert login.status_code == 200, login.text

    denied = client.post("/api/v1/admin/foods", json=_FOOD_BODY)
    assert denied.status_code == 403
    assert denied.json().get("code") == "admin_step_up"

    confirm = client.post("/api/v1/auth/confirm-password", json={"password": "Secret12"})
    assert confirm.status_code == 200, confirm.text
    assert "taptot_admin=" in _cookies(confirm)

    created = client.post("/api/v1/admin/foods", json=_FOOD_BODY)
    assert created.status_code == 201, created.text
    assert created.json()["name_vi"] == "Bánh test cookie"


def test_admin_bearer_skips_step_up():
    client, Session = _app_client()
    admin_id = str(uuid4())
    db = Session()
    db.add(
        User(
            id=admin_id,
            email="bearer-admin@example.com",
            password_hash=hash_password("Secret12"),
            display_name="Bearer Admin",
            role=Role.ADMIN.value,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    db.close()

    token = create_access_token(admin_id, Role.ADMIN.value)
    bare = TestClient(client.app)
    res = bare.post(
        "/api/v1/admin/foods",
        json=_FOOD_BODY,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text


def test_former_trainer_roles_become_hlv():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    uid = str(uuid4())
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, email, role, created_at) "
                "VALUES (:id, :email, 'trainer', :created)"
            ),
            {"id": uid, "email": "ex-hlv@example.com", "created": datetime.now(UTC)},
        )
    ensure_user_roles_normalized(engine)
    with engine.begin() as conn:
        role = conn.execute(text("SELECT role FROM users WHERE id = :id"), {"id": uid}).scalar_one()
    assert role == "hlv"
