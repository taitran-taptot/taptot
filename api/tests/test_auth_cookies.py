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
    assert [r.value for r in Role] == ["user", "admin"]
    assert not hasattr(Role, "TRAINER")
    assert "role" not in RegisterRequest.model_fields


def test_register_ignores_trainer_role_and_sets_cookies():
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
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["role"] == "user"
    assert "access_token" not in body
    assert "refresh_token" not in body
    cookies = _cookies(res)
    assert "taptot_access=" in cookies
    assert "taptot_refresh=" in cookies
    assert "httponly" in cookies.lower()

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "newuser@example.com"
    assert me.json()["role"] == "user"


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
            role=Role.USER.value,
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
    client, _ = _app_client()
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "csrf@example.com",
            "password": "Secret12",
            "display_name": "CSRF",
        },
    )
    res = client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "https://evil.example"},
    )
    assert res.status_code == 403
    assert res.json().get("code") == "csrf"


def test_user_cannot_write_admin_foods():
    client, _ = _app_client()
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "plain@example.com",
            "password": "Secret12",
            "display_name": "User",
        },
    )
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


def test_former_trainer_roles_become_user():
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
    assert role == "user"
