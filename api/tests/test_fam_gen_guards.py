"""Turnstile + daily IP/device caps for free workout generation."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import pytest

from app.api.v1 import ai as ai_routes
from app.api.v1.ai import WorkoutScheduleRequest
from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ForbiddenError, TooManyRequestsError
from app.services import fam_gen_cap
from app.services.fam_gen_cap import MSG_DEVICE_DAILY, MSG_DEVICE_INVALID, MSG_IP_DAILY
from app.services.turnstile import (
    MSG_CAPTCHA_FAILED,
    MSG_CAPTCHA_REQUIRED,
    MSG_CAPTCHA_UNAVAILABLE,
    verify_turnstile,
)


DEVICE_A = "11111111-1111-4111-8111-111111111111"
DEVICE_B = "22222222-2222-4222-8222-222222222222"


def _request(*, device_id: str | None = DEVICE_A, ip: str = "203.0.113.10") -> MagicMock:
    req = MagicMock()
    headers = {}
    if device_id is not None:
        headers["x-device-id"] = device_id
    req.headers = headers
    req.client = MagicMock()
    req.client.host = ip
    return req


def _free_body(**kwargs) -> WorkoutScheduleRequest:
    base = dict(
        age=25,
        height_cm=170,
        weight_kg=65,
        generation_mode="familiarization",
        familiarization_path="first_push_pull",
        captcha_token="tok-ok",
    )
    base.update(kwargs)
    return WorkoutScheduleRequest(**base)


def _challenge_body(**kwargs) -> WorkoutScheduleRequest:
    base = dict(
        age=25,
        height_cm=170,
        weight_kg=65,
        challenge_100_days=True,
        redeem_code="TT-AAAA-AAAA",
        captcha_token=None,
    )
    base.update(kwargs)
    return WorkoutScheduleRequest(**base)


@pytest.fixture(autouse=True)
def _reset_caps(monkeypatch: pytest.MonkeyPatch):
    fam_gen_cap.reset_memory_for_tests()
    monkeypatch.setattr(get_settings(), "turnstile_secret_key", "")
    monkeypatch.setattr(get_settings(), "fam_gen_daily_cap_enabled", True)
    monkeypatch.setattr(get_settings(), "fam_gen_daily_device_limit", 3)
    monkeypatch.setattr(get_settings(), "fam_gen_daily_ip_limit", 5)
    monkeypatch.setattr(get_settings(), "require_redeem_code_for_generate", True)
    yield
    fam_gen_cap.reset_memory_for_tests()


def test_verify_turnstile_noop_without_secret():
    verify_turnstile(None)
    verify_turnstile("")


def test_verify_turnstile_requires_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(get_settings(), "turnstile_secret_key", "secret")
    with pytest.raises(ForbiddenError) as exc:
        verify_turnstile(None)
    assert exc.value.code == "captcha_required"
    assert exc.value.message == MSG_CAPTCHA_REQUIRED


def test_verify_turnstile_failed(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(get_settings(), "turnstile_secret_key", "secret")

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"success": False, "error-codes": ["invalid-input-response"]}).encode()

    with patch("app.services.turnstile.urllib.request.urlopen", return_value=_Resp()):
        with pytest.raises(ForbiddenError) as exc:
            verify_turnstile("bad")
    assert exc.value.code == "captcha_failed"
    assert exc.value.message == MSG_CAPTCHA_FAILED


def test_verify_turnstile_unavailable(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(get_settings(), "turnstile_secret_key", "secret")
    with patch(
        "app.services.turnstile.urllib.request.urlopen",
        side_effect=URLError("down"),
    ):
        with pytest.raises(ForbiddenError) as exc:
            verify_turnstile("tok")
    assert exc.value.code == "captcha_unavailable"
    assert exc.value.message == MSG_CAPTCHA_UNAVAILABLE


def test_missing_device_id_rejected(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        ai_routes,
        "generate_workout",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("should not gen")),
    )
    with pytest.raises(BadRequestError) as exc:
        ai_routes.generate_workout_schedule(
            _free_body(),
            request=_request(device_id=None),
            db=MagicMock(),
            user=None,
        )
    assert exc.value.code == "device_id_invalid"
    assert exc.value.message == MSG_DEVICE_INVALID


def test_free_gen_captcha_required_when_secret_set(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(get_settings(), "turnstile_secret_key", "secret")
    monkeypatch.setattr(
        ai_routes,
        "generate_workout",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("should not gen")),
    )
    with pytest.raises(ForbiddenError) as exc:
        ai_routes.generate_workout_schedule(
            _free_body(captcha_token=None),
            request=_request(),
            db=MagicMock(),
            user=None,
        )
    assert exc.value.code == "captcha_required"


def test_free_gen_success_records_daily_cap(monkeypatch: pytest.MonkeyPatch):
    called = {"n": 0}

    def fake_generate(_db, _user_id, payload):
        called["n"] += 1
        assert "captcha_token" not in payload
        return {
            "plan_id": 7,
            "share_token": "abc",
            "plan": {"id": 7, "title_vi": "Nhập môn", "share_token": "abc"},
        }

    monkeypatch.setattr(ai_routes, "generate_workout", fake_generate)
    result = ai_routes.generate_workout_schedule(
        _free_body(),
        request=_request(),
        db=MagicMock(),
        user=None,
    )
    assert called["n"] == 1
    assert result["plan_id"] == 7

    # 2 more successes then device cap
    for i in range(2):
        ai_routes.generate_workout_schedule(
            _free_body(),
            request=_request(),
            db=MagicMock(),
            user=None,
        )
    with pytest.raises(TooManyRequestsError) as exc:
        ai_routes.generate_workout_schedule(
            _free_body(),
            request=_request(),
            db=MagicMock(),
            user=None,
        )
    assert exc.value.code == "fam_gen_device_daily"
    assert exc.value.message == MSG_DEVICE_DAILY
    assert exc.value.status_code == 429


def test_free_gen_ip_daily_cap(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(get_settings(), "fam_gen_daily_device_limit", 99)
    monkeypatch.setattr(get_settings(), "fam_gen_daily_ip_limit", 5)
    monkeypatch.setattr(
        ai_routes,
        "generate_workout",
        lambda *_a, **_k: {
            "plan_id": 1,
            "share_token": "s",
            "plan": {"id": 1, "title_vi": "x", "share_token": "s"},
        },
    )
    for i in range(5):
        device = f"{i:08d}-1111-4111-8111-111111111111"
        ai_routes.generate_workout_schedule(
            _free_body(),
            request=_request(device_id=device, ip="198.51.100.9"),
            db=MagicMock(),
            user=None,
        )
    with pytest.raises(TooManyRequestsError) as exc:
        ai_routes.generate_workout_schedule(
            _free_body(),
            request=_request(device_id=DEVICE_B, ip="198.51.100.9"),
            db=MagicMock(),
            user=None,
        )
    assert exc.value.code == "fam_gen_ip_daily"
    assert exc.value.message == MSG_IP_DAILY


def test_challenge_skips_turnstile_and_cap(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(get_settings(), "turnstile_secret_key", "secret")
    verify_calls = {"n": 0}
    check_calls = {"n": 0}

    def boom_verify(*_a, **_k):
        verify_calls["n"] += 1
        raise AssertionError("turnstile should not run for challenge")

    def boom_check(*_a, **_k):
        check_calls["n"] += 1
        raise AssertionError("daily cap should not run for challenge")

    monkeypatch.setattr(ai_routes, "verify_turnstile", boom_verify)
    monkeypatch.setattr(ai_routes, "fam_cap_check", boom_check)

    reserved = {"tok": "res-1"}

    class FakeRedeem:
        def reserve(self, _code):
            return reserved["tok"]

        def complete(self, *_a, **_k):
            return True

        def release(self, *_a, **_k):
            return None

    monkeypatch.setattr(ai_routes, "RedeemCodeService", lambda _db: FakeRedeem())
    monkeypatch.setattr(
        ai_routes,
        "generate_workout",
        lambda *_a, **_k: {
            "plan_id": 55,
            "share_token": "share",
            "plan": {"id": 55, "title_vi": "Challenge", "share_token": "share"},
        },
    )
    # No device header — would fail if free_mode guards ran
    result = ai_routes.generate_workout_schedule(
        _challenge_body(redeem_code="TT-7K3M-P2QX"),
        request=_request(device_id=None),
        db=MagicMock(),
        user=None,
    )
    assert verify_calls["n"] == 0
    assert check_calls["n"] == 0
    assert result["plan_id"] == 55


def test_free_home_still_skips_redeem(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        ai_routes,
        "generate_workout",
        lambda *_a, **_k: {
            "plan_id": 99,
            "plan": {"id": 99, "title_vi": "Free home", "source": "ai"},
        },
    )
    result = ai_routes.generate_workout_schedule(
        WorkoutScheduleRequest(
            age=25,
            height_cm=170,
            weight_kg=65,
            generation_mode="free_home",
            redeem_code=None,
        ),
        request=_request(),
        db=MagicMock(),
        user=None,
    )
    assert result["plan_id"] == 99
    assert result.get("code_applied") is False
