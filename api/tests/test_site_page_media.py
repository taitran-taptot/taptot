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
from app.services.site_page_media import (
    DEFAULT_YOUTUBE_ID,
    normalize_footer_href,
    normalize_trade_notice_url,
    parse_youtube_id,
)


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


def test_normalize_trade_notice_url():
    assert normalize_trade_notice_url("  ") == ""
    assert (
        normalize_trade_notice_url("http://online.gov.vn/Home/WebDetails/12")
        == "https://online.gov.vn/Home/WebDetails/12"
    )
    assert (
        normalize_trade_notice_url("https://www.online.gov.vn/Home/WebDetails/12")
        == "https://online.gov.vn/Home/WebDetails/12"
    )
    with pytest.raises(BadRequestError):
        normalize_trade_notice_url("https://example.com/Home/WebDetails/12")


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
    assert len(body["success_stories"]) == 7
    assert body["success_stories"][0]["image_url"] == "/brand/taptot-bia-vuong.png"
    assert body["success_stories"][0]["logo_url"] == "/brand/taptot-logo-vuong.png"
    assert body["success_stories"][0]["name"] == "Lan Phương"
    assert body["success_stories"][0]["occupation"] == "Nhân viên văn phòng"
    assert body["success_stories_visible"] is True
    assert body["bo_cong_thuong_url"] == ""
    assert body["footer_phone_href"] == "tel:+817091335675"
    assert body["footer_email_href"] == "mailto:tai.tran@taptot.vn"
    assert body["footer_facebook_href"].startswith("https://www.facebook.com/")
    assert body["footer_tiktok_href"] == "https://www.tiktok.com/@taptot.vn"


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
            "success_stories": [
                {
                    "image_url": "/media/success-1.jpg",
                    "logo_url": "/media/logo-1.png",
                    "name": "Lan",
                    "quote": "Lịch vừa sức nên tôi đi hết 100 ngày.",
                }
            ],
            "success_stories_visible": False,
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["home_challenge_youtube_id"] == "dQw4w9WgXcQ"
    assert body["shop_guide_youtube_id"] == "aaaaaaaaaaa"
    assert body["service_hlv_image_url"] == "/media/hlv-new.jpg"
    assert body["about_hero_image_url"] == "/media/about-hero.jpg"
    assert body["contact_trainer_image_url"] == "/media/contact-hlv.jpg"
    assert len(body["success_stories"]) == 7
    assert body["success_stories"][0]["name"] == "Lan"
    assert body["success_stories"][0]["quote"] == "Lịch vừa sức nên tôi đi hết 100 ngày."
    assert body["success_stories"][1]["name"] == ""
    assert body["success_stories_visible"] is False
    public = client.get("/api/v1/site/page-media").json()
    assert public["home_challenge_youtube_id"] == "dQw4w9WgXcQ"
    assert public["about_hero_image_url"] == "/media/about-hero.jpg"


def test_trade_notice_url_saves_https_and_rejects_other_hosts():
    client, Session = _app_client()
    admin_id = _admin(Session)
    headers = _bearer(admin_id, Role.ADMIN.value)
    saved = client.patch(
        "/api/v1/admin/site/page-media",
        headers=headers,
        json={
            "home_challenge_youtube": "https://youtu.be/dQw4w9WgXcQ",
            "bo_cong_thuong_url": "http://online.gov.vn/Home/WebDetails/99",
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["bo_cong_thuong_url"] == "https://online.gov.vn/Home/WebDetails/99"
    rejected = client.patch(
        "/api/v1/admin/site/page-media",
        headers=headers,
        json={
            "home_challenge_youtube": "https://youtu.be/aaaaaaaaaaa",
            "service_hlv_image_url": "/media/should-not-save.jpg",
            "bo_cong_thuong_url": "https://example.com/fake",
        },
    )
    assert rejected.status_code == 400, rejected.text
    public = client.get("/api/v1/site/page-media").json()
    assert public["home_challenge_youtube_id"] == "dQw4w9WgXcQ"
    assert public["service_hlv_image_url"] == "/home-hlv.png"
    assert public["bo_cong_thuong_url"] == "https://online.gov.vn/Home/WebDetails/99"
    cleared = client.patch(
        "/api/v1/admin/site/page-media",
        headers=headers,
        json={"bo_cong_thuong_url": "   "},
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["bo_cong_thuong_url"] == ""


def test_footer_contact_links_save_and_reject_bad_schemes():
    assert normalize_footer_href("  ") == ""
    assert normalize_footer_href("mailto:a@b.c") == "mailto:a@b.c"
    assert normalize_footer_href("tel:+84901234567") == "tel:+84901234567"
    with pytest.raises(BadRequestError):
        normalize_footer_href("javascript:alert(1)")

    client, Session = _app_client()
    admin_id = _admin(Session)
    headers = _bearer(admin_id, Role.ADMIN.value)
    saved = client.patch(
        "/api/v1/admin/site/page-media",
        headers=headers,
        json={
            "footer_phone_href": "https://zalo.me/84901234567",
            "footer_email_href": "mailto:hello@taptot.vn",
            "footer_facebook_href": "https://facebook.com/taptot",
            "footer_tiktok_href": "https://www.tiktok.com/@taptot",
        },
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["footer_phone_href"] == "https://zalo.me/84901234567"
    assert body["footer_email_href"] == "mailto:hello@taptot.vn"
    assert body["footer_facebook_href"] == "https://facebook.com/taptot"
    assert body["footer_tiktok_href"] == "https://www.tiktok.com/@taptot"
    rejected = client.patch(
        "/api/v1/admin/site/page-media",
        headers=headers,
        json={"footer_phone_href": "javascript:alert(1)"},
    )
    assert rejected.status_code == 400
    public = client.get("/api/v1/site/page-media").json()
    assert public["footer_phone_href"] == "https://zalo.me/84901234567"
    cleared = client.patch(
        "/api/v1/admin/site/page-media",
        headers=headers,
        json={"footer_facebook_href": "   "},
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["footer_facebook_href"].startswith("https://www.facebook.com/")
