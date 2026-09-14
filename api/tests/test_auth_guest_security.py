"""Auth guest-gen security: optional JWT, rate buckets, reset URLs, share tokens."""

from unittest.mock import MagicMock

import pytest
from jose import jwt

from app.core.config import get_settings
from app.core.deps import get_current_user_optional
from app.core.exceptions import UnauthorizedError
from app.core.rate_limit import classify_rate_limit
from app.core.security import create_access_token, create_refresh_token
from app.services.auth_service import AuthService
from app.services.plan_service import _new_share_token


def test_classify_rate_limit_ai_generate_stricter_than_generic():
    bucket, limit = classify_rate_limit("/api/v1/ai/generate-workout-schedule", "POST")
    assert bucket == "ai-gen"
    assert limit <= 8
    generic_bucket, generic_limit = classify_rate_limit("/api/v1/exercises", "GET")
    assert generic_bucket == "ip"
    assert generic_limit >= limit


def test_classify_rate_limit_auth_and_public_plan_create():
    assert classify_rate_limit("/api/v1/auth/login", "POST")[0] == "auth"
    assert classify_rate_limit("/api/v1/auth/forgot-password", "POST")[0] == "auth"
    bucket, limit = classify_rate_limit("/api/v1/plans", "POST")
    assert bucket == "plan-create"
    assert limit <= 12
    # Authenticated create uses /my-plans — not the guest bucket
    assert classify_rate_limit("/api/v1/my-plans", "POST")[0] == "ip"


def test_reset_and_verify_urls_match_frontend_routes():
    service = AuthService(MagicMock())
    reset = service.build_reset_url("tok123")
    verify = service.build_verify_url("tok123")
    assert "/dat-lai-mat-khau?token=tok123" in reset
    assert "/xac-thuc-email?token=tok123" in verify
    assert "/reset-password" not in reset
    assert "/verify-email" not in verify


def test_optional_user_no_header_is_guest():
    assert get_current_user_optional(authorization=None, db=MagicMock()) is None
    assert get_current_user_optional(authorization="Basic abc", db=MagicMock()) is None


def test_optional_user_rejects_invalid_bearer():
    with pytest.raises(UnauthorizedError):
        get_current_user_optional(authorization="Bearer not-a-jwt", db=MagicMock())
    with pytest.raises(UnauthorizedError):
        get_current_user_optional(authorization="Bearer ", db=MagicMock())


def test_optional_user_rejects_refresh_token_as_access():
    refresh = create_refresh_token("user-1")
    with pytest.raises(UnauthorizedError):
        get_current_user_optional(authorization=f"Bearer {refresh}", db=MagicMock())


def test_optional_user_rejects_unknown_subject():
    access = create_access_token("missing-user", "user")
    db = MagicMock()
    db.get.return_value = None
    with pytest.raises(UnauthorizedError):
        get_current_user_optional(authorization=f"Bearer {access}", db=db)


def test_optional_user_accepts_valid_access():
    access = create_access_token("user-1", "user")
    db = MagicMock()
    user = MagicMock()
    user.id = "user-1"
    user.role = "user"
    user.email = "a@b.c"
    db.get.return_value = user
    current = get_current_user_optional(authorization=f"Bearer {access}", db=db)
    assert current is not None
    assert current.id == "user-1"


def test_share_token_entropy():
    token = _new_share_token()
    assert len(token) >= 20


def test_forgot_password_schema_does_not_require_token_fields():
    from app.schemas.auth import ForgotPasswordResponse

    body = ForgotPasswordResponse(message="If the email exists, a password reset link has been sent.")
    dumped = body.model_dump()
    assert dumped.get("reset_token") is None


def test_jwt_secret_used_for_access_tokens():
    token = create_access_token("u1", "user")
    payload = jwt.decode(token, get_settings().secret_key, algorithms=[get_settings().algorithm])
    assert payload["type"] == "access"
    assert payload["sub"] == "u1"


_GEN_BODY = {
    "goal": "maintain",
    "gender": "male",
    "age": 28,
    "height_cm": 170,
    "weight_kg": 70,
    "activity": "moderate",
    "sessions_per_week": 3,
    "session_minutes": 45,
    "location": "gym",
    "experience_level": 1,
    "duration_weeks": 4,
}


def test_generate_schedule_requires_code_for_guest(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import create_app

    monkeypatch.setattr(get_settings(), "require_redeem_code_for_generate", True)

    def fake_gen(*_args, **_kwargs):
        raise AssertionError("must not generate without a code")

    monkeypatch.setattr("app.api.v1.ai.generate_workout", fake_gen)
    client = TestClient(create_app())
    res = client.post("/api/v1/ai/generate-workout-schedule", json=_GEN_BODY)
    assert res.status_code == 403
    assert "mã TAPTOT" in res.json()["detail"]


def test_generate_schedule_rejects_bad_bearer(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import create_app

    monkeypatch.setattr(get_settings(), "require_redeem_code_for_generate", True)
    monkeypatch.setattr(
        "app.api.v1.ai.generate_workout",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not generate")),
    )
    client = TestClient(create_app())
    res = client.post(
        "/api/v1/ai/generate-workout-schedule",
        json=_GEN_BODY,
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert res.status_code == 401


def test_generate_challenge_without_code_is_rejected(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import create_app

    monkeypatch.setattr(get_settings(), "require_redeem_code_for_generate", True)
    called = {"n": 0}

    def fake_gen(*_a, **_k):
        called["n"] += 1
        raise AssertionError("must not generate")

    monkeypatch.setattr("app.api.v1.ai.generate_workout", fake_gen)
    client = TestClient(create_app())
    res = client.post(
        "/api/v1/ai/generate-workout-schedule",
        json={**_GEN_BODY, "challenge_100_days": True},
    )
    assert res.status_code == 403
    assert "mã TAPTOT" in res.json()["detail"]
    assert called["n"] == 0


def test_generate_curriculum_alias_without_code_is_rejected(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import create_app

    monkeypatch.setattr(get_settings(), "require_redeem_code_for_generate", True)
    monkeypatch.setattr(
        "app.api.v1.ai.generate_workout",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not generate")),
    )
    client = TestClient(create_app())
    res = client.post(
        "/api/v1/ai/generate-workout-schedule",
        json={**_GEN_BODY, "curriculum_12_weeks": True},
    )
    assert res.status_code == 403
    assert "mã TAPTOT" in res.json()["detail"]


def test_public_create_challenge_requires_login(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import create_app

    monkeypatch.setattr(
        "app.api.v1.plans.PlanService.create_plan",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not create")),
    )
    client = TestClient(create_app())
    res = client.post(
        "/api/v1/plans",
        json={"title_vi": "Thử thách guest", "challenge_100_days": True},
    )
    assert res.status_code == 401
    assert "Đăng nhập" in res.json()["detail"]

