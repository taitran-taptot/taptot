from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import Role, create_access_token, hash_password
from app.main import create_app
from app.models.base import Base
from app.models.entities import User

DOC = {
    "updated_label": "Cập nhật lần cuối: Ngày 14 tháng 11 năm 2026.",
    "intro": "Đoạn mở đầu đã sửa.",
    "agreement": "Bạn đồng ý bản này.",
    "sections": [
        {
            "id": "1",
            "title": "Mục một",
            "paragraphs": ["  ", "Nội dung một."],
            "bullets": ["Gạch một"],
        }
    ],
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


def _user(Session, role: str) -> str:
    uid = str(uuid4())
    db = Session()
    db.add(
        User(
            id=uid,
            email=f"{role}-{uid[:8]}@legal.test",
            password_hash=hash_password("Secret12"),
            display_name=role,
            role=role,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    db.close()
    return uid


def _bearer(user_id: str, role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id, role)}"}


def test_legal_defaults_and_unknown_slug():
    client, _Session = _app_client()
    res = client.get("/api/v1/site/legal/dieu-khoan")
    assert res.status_code == 200, res.text
    assert res.json() == {"slug": "dieu-khoan", "source": "default", "document": None}
    missing = client.get("/api/v1/site/legal/khong-co")
    assert missing.status_code == 404


def test_admin_saves_and_reset_restores_default():
    client, Session = _app_client()
    admin_id = _user(Session, Role.ADMIN.value)
    headers = _bearer(admin_id, Role.ADMIN.value)
    denied = client.put("/api/v1/admin/site/legal/khieu-nai", json=DOC)
    assert denied.status_code in {401, 403}
    staff_id = _user(Session, Role.HLV.value)
    forbidden = client.put(
        "/api/v1/admin/site/legal/khieu-nai",
        headers=_bearer(staff_id, Role.HLV.value),
        json=DOC,
    )
    assert forbidden.status_code == 403
    unknown = client.put("/api/v1/admin/site/legal/khong-co", headers=headers, json=DOC)
    assert unknown.status_code == 404
    blank = client.put(
        "/api/v1/admin/site/legal/khieu-nai",
        headers=headers,
        json={**DOC, "sections": [{"id": "1", "title": "  ", "paragraphs": ["Có chữ"], "bullets": []}]},
    )
    assert blank.status_code == 400
    saved = client.put("/api/v1/admin/site/legal/khieu-nai", headers=headers, json=DOC)
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["source"] == "saved"
    assert body["document"]["intro"] == "Đoạn mở đầu đã sửa."
    assert body["document"]["sections"][0]["paragraphs"] == ["Nội dung một."]
    assert body["document"]["sections"][0]["bullets"] == ["Gạch một"]
    public = client.get("/api/v1/site/legal/khieu-nai").json()
    assert public["document"]["agreement"] == "Bạn đồng ý bản này."
    other = client.get("/api/v1/site/legal/dieu-khoan").json()
    assert other["source"] == "default"
    reset = client.delete("/api/v1/admin/site/legal/khieu-nai", headers=headers)
    assert reset.status_code == 200, reset.text
    assert reset.json()["source"] == "default"
    again = client.get("/api/v1/site/legal/khieu-nai").json()
    assert again == {"slug": "khieu-nai", "source": "default", "document": None}
