from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.services.plan_service import (
    GUEST_CHALLENGE_TTL_DAYS,
    GUEST_TTL_DAYS,
    guest_days_left,
    guest_expires_at,
    guest_ttl_days,
    is_guest_expired,
)


def _plan(*, user_id=None, challenge=False, created_at=None):
    return SimpleNamespace(
        user_id=user_id,
        challenge_100_days=challenge,
        created_at=created_at or datetime.now(UTC),
    )


def test_owned_plan_has_no_ttl():
    plan = _plan(user_id="u1")
    assert guest_ttl_days(plan) is None
    assert guest_expires_at(plan) is None
    assert guest_days_left(plan) is None
    assert is_guest_expired(plan) is False


def test_guest_regular_ttl_100():
    created = datetime(2026, 1, 1, tzinfo=UTC)
    plan = _plan(created_at=created)
    assert guest_ttl_days(plan) == GUEST_TTL_DAYS
    assert guest_expires_at(plan) == created + timedelta(days=100)


def test_guest_challenge_ttl_110():
    created = datetime(2026, 1, 1, tzinfo=UTC)
    plan = _plan(challenge=True, created_at=created)
    assert guest_ttl_days(plan) == GUEST_CHALLENGE_TTL_DAYS
    assert guest_expires_at(plan) == created + timedelta(days=110)


def test_guest_expired_after_ttl():
    plan = _plan(created_at=datetime.now(UTC) - timedelta(days=101))
    assert is_guest_expired(plan) is True
    assert guest_days_left(plan) == 0


def test_guest_challenge_not_expired_at_101():
    plan = _plan(challenge=True, created_at=datetime.now(UTC) - timedelta(days=101))
    assert is_guest_expired(plan) is False
    assert guest_days_left(plan) and guest_days_left(plan) >= 1


def test_guest_challenge_not_expired_at_109():
    plan = _plan(challenge=True, created_at=datetime.now(UTC) - timedelta(days=109))
    assert is_guest_expired(plan) is False


def test_guest_challenge_expired_at_111():
    plan = _plan(challenge=True, created_at=datetime.now(UTC) - timedelta(days=111))
    assert is_guest_expired(plan) is True
    assert guest_days_left(plan) == 0
