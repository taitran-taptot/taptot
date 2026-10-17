"""Public /lien-he leads + admin CRM list/patch."""

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import Role, create_access_token
from app.main import create_app
from app.models.base import Base
from app.models.entities import User

ADMIN_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
USER_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"
JAN = datetime(2026, 1, 15, 10, 0, 0)


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


def _bearer(user_id: str, role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id, role)}"}


def _user(db, *, uid: str, email: str, role: str) -> User:
    row = User(
        id=uid,
        email=email,
        password_hash="x",
        display_name=email.split("@")[0],
        role=role,
        created_at=JAN,
    )
    db.add(row)
    return row


def test_public_create_and_admin_list_patch():
    client, Session = _app_client()
    db = Session()
    _user(db, uid=ADMIN_ID, email="admin@test.com", role="admin")
    _user(db, uid=USER_ID, email="u@test.com", role="user")
    db.commit()
    db.close()

    created = client.post(
        "/api/v1/contact/trainer",
        json={
            "full_name": "Nguyễn Văn A",
            "phone_zalo": "0901111111",
            "email": "a@example.com",
            "message": "Mục tiêu: Giảm cân\nNơi tập: Tập tại nhà",
        },
    )
    assert created.status_code == 201, created.text
    lead_id = created.json()["id"]

    forbidden = client.get("/api/v1/admin/trainer-contacts", headers=_bearer(USER_ID, Role.USER.value))
    assert forbidden.status_code == 403

    listed = client.get(
        "/api/v1/admin/trainer-contacts",
        headers=_bearer(ADMIN_ID, Role.ADMIN.value),
    )
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id"] == lead_id
    assert item["full_name"] == "Nguyễn Văn A"
    assert item["status"] == "new"
    assert item["phone_zalo"] == "0901111111"

    search = client.get(
        "/api/v1/admin/trainer-contacts?q=090111",
        headers=_bearer(ADMIN_ID, Role.ADMIN.value),
    )
    assert search.json()["total"] == 1

    patched = client.patch(
        f"/api/v1/admin/trainer-contacts/{lead_id}",
        headers=_bearer(ADMIN_ID, Role.ADMIN.value),
        json={"status": "contacted", "admin_note": "Đã Zalo"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["status"] == "contacted"
    assert patched.json()["admin_note"] == "Đã Zalo"

    filtered = client.get(
        "/api/v1/admin/trainer-contacts?status=contacted",
        headers=_bearer(ADMIN_ID, Role.ADMIN.value),
    )
    assert filtered.json()["total"] == 1

    bad = client.patch(
        f"/api/v1/admin/trainer-contacts/{lead_id}",
        headers=_bearer(ADMIN_ID, Role.ADMIN.value),
        json={"status": "nope"},
    )
    assert bad.status_code == 400
