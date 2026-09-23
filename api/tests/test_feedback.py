from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.api.v1.feedback import prepare_feedback
from app.core.exceptions import BadRequestError
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
