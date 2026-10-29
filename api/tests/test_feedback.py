from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.feedback import prepare_feedback
from app.core.database import get_db
from app.core.exceptions import BadRequestError
from app.main import create_app
from app.models.base import Base
from app.services.feedback_sheets import append_feedback_row


def test_prepare_other_ok():
    out = prepare_feedback("other", "Nội dung góp ý đủ dài")
    assert out["category"] == "other"
    assert out["title"] == "Khác"
    assert out["plan_url"] is None


def test_prepare_trainer_ok():
    out = prepare_feedback("trainer", "Nội dung góp ý đủ dài")
    assert out["category"] == "trainer"
    assert out["title"] == "Huấn luyện viên"
    assert out["plan_url"] is None


def test_prepare_rejects_unknown_category():
    with pytest.raises(BadRequestError, match="không hợp lệ"):
        prepare_feedback("xlsx", "Nội dung góp ý đủ dài")


def test_prepare_workout_plan_requires_link():
    with pytest.raises(BadRequestError, match="link lịch"):
        prepare_feedback("workout_plan", "Nội dung góp ý đủ dài")


def test_prepare_meal_plan_with_link():
    out = prepare_feedback(
        "meal_plan",
        "Nội dung góp ý đủ dài",
        plan_url="https://taptot.vn/lich/abc",
    )
    assert out["category"] == "meal_plan"
    assert out["title"] == "Lịch ăn"
    assert out["plan_url"] == "https://taptot.vn/lich/abc"


@patch("app.services.feedback_sheets.get_settings")
@patch("app.services.feedback_sheets.httpx.post")
def test_append_feedback_row_posts_webhook(mock_post, mock_settings):
    mock_settings.return_value = SimpleNamespace(
        feedback_sheets_webhook_url="https://script.google.com/macros/s/test/exec",
        feedback_sheets_secret="16102002",
    )
    mock_post.return_value = SimpleNamespace(status_code=200)
    append_feedback_row(
        email="a@b.c",
        category_label="Khác",
        content="hello world",
        plan_url=None,
        time_iso="2026-09-23T00:00:00+00:00",
    )
    mock_post.assert_called_once()
    kwargs = mock_post.call_args.kwargs
    assert kwargs["json"]["secret"] == "16102002"
    assert kwargs["json"]["email"] == "a@b.c"
    assert kwargs["json"]["category"] == "Khác"
    assert kwargs["follow_redirects"] is True


@patch("app.services.feedback_sheets.get_settings")
@patch("app.services.feedback_sheets.httpx.post")
def test_append_feedback_row_guest_empty_email(mock_post, mock_settings):
    mock_settings.return_value = SimpleNamespace(
        feedback_sheets_webhook_url="https://script.google.com/macros/s/test/exec",
        feedback_sheets_secret="16102002",
    )
    mock_post.return_value = SimpleNamespace(status_code=200)
    append_feedback_row(
        email="",
        category_label="Khác",
        content="góp ý khách",
        plan_url=None,
        time_iso="2026-09-23T00:00:00+00:00",
    )
    assert mock_post.call_args.kwargs["json"]["email"] == ""


@patch("app.services.feedback_sheets.get_settings")
@patch("app.services.feedback_sheets.httpx.post")
def test_append_feedback_row_skips_when_unconfigured(mock_post, mock_settings):
    mock_settings.return_value = SimpleNamespace(
        feedback_sheets_webhook_url="",
        feedback_sheets_secret="",
    )
    append_feedback_row(
        email="a@b.c",
        category_label="Khác",
        content="hello world",
        plan_url=None,
        time_iso="2026-09-23T00:00:00+00:00",
    )
    mock_post.assert_not_called()


def _feedback_client():
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
    return TestClient(app)


@patch("app.api.v1.feedback.append_feedback_row")
def test_http_guest_feedback_other_201(mock_append):
    client = _feedback_client()
    res = client.post(
        "/api/v1/feedback",
        json={"category": "other", "content": "Nội dung góp ý đủ dài"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["category"] == "other"
    assert body["title"] == "Khác"
    mock_append.assert_called_once()
    kwargs = mock_append.call_args.kwargs
    assert kwargs["email"] == ""
    assert kwargs["category_label"] == "Khác"
    assert kwargs["plan_url"] is None


def test_http_workout_plan_without_link_400():
    client = _feedback_client()
    res = client.post(
        "/api/v1/feedback",
        json={"category": "workout_plan", "content": "Nội dung góp ý đủ dài"},
    )
    assert res.status_code == 400, res.text
    assert "link lịch" in res.json()["detail"]
