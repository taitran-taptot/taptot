from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.exceptions import BadRequestError
from app.core.security import Role, create_access_token, hash_password
from app.main import create_app
from app.models.base import Base
from app.models.entities import User
from app.services.site_page_media import DEFAULT_YOUTUBE_ID, parse_youtube_id


def test_parse_youtube_id():
    assert parse_youtube_id("EngW7tLk6R8") == "EngW7tLk6R8"
    assert parse_youtube_id("https://www.youtube.com/watch?v=EngW7tLk6R8") == "EngW7tLk6R8"
    assert parse_youtube_id("https://youtu.be/EngW7tLk6R8") == "EngW7tLk6R8"
    assert parse_youtube_id("https://www.youtube.com/embed/EngW7tLk6R8") == "EngW7tLk6R8"
    assert parse_youtube_id("https://www.youtube.com/shorts/EngW7tLk6R8") == "EngW7tLk6R8"
    with pytest.raises(BadRequestError):
        parse_youtube_id("https://example.com/watch")


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


def _admin(Session) -> str:
    uid = str(uuid4())
    db = Session()
    db.add(
        User(
            id=uid,
            email="admin@media.test",
            password_hash=hash_password("Secret12"),
            display_name="Admin",
            role=Role.ADMIN.value,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    db.close()
    return uid


def _bearer(user_id: str, role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id, role)}"}


def test_get_page_media_defaults():
    client, _Session = _app_client()
    res = client.get("/api/v1/site/page-media")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["home_challenge_youtube_id"] == DEFAULT_YOUTUBE_ID
    assert body["shop_guide_youtube_id"] == DEFAULT_YOUTUBE_ID
    assert body["service_lo_trinh_image_url"] == "/home-lo-trinh.png"
    assert body["about_hero_image_url"] == "/hero-gym.jpg"
    assert body["about_founder_image_url"] == "/tran-tai.jpg"
    assert body["contact_trainer_image_url"] == "/hlv-nguyen-van-tien.jpg"


def test_admin_patch_page_media():
    client, Session = _app_client()
    admin_id = _admin(Session)
    denied = client.patch(
        "/api/v1/admin/site/page-media",
        json={"home_challenge_youtube": "https://youtu.be/dQw4w9WgXcQ"},
    )
    assert denied.status_code in {401, 403}
    res = client.patch(
        "/api/v1/admin/site/page-media",
        headers=_bearer(admin_id, Role.ADMIN.value),
        json={
            "home_challenge_youtube": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "shop_guide_youtube_id": "aaaaaaaaaaa",
            "service_hlv_image_url": "/media/hlv-new.jpg",
            "about_hero_image_url": "/media/about-hero.jpg",
            "contact_trainer_image_url": "/media/contact-hlv.jpg",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["home_challenge_youtube_id"] == "dQw4w9WgXcQ"
    assert body["shop_guide_youtube_id"] == "aaaaaaaaaaa"
    assert body["service_hlv_image_url"] == "/media/hlv-new.jpg"
    assert body["about_hero_image_url"] == "/media/about-hero.jpg"
    assert body["contact_trainer_image_url"] == "/media/contact-hlv.jpg"
    public = client.get("/api/v1/site/page-media").json()
    assert public["home_challenge_youtube_id"] == "dQw4w9WgXcQ"
    assert public["about_hero_image_url"] == "/media/about-hero.jpg"
