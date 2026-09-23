from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import AppException
from app.models.base import Base
from app.models.entities import User, UserDailyPlan
from app.services.plan_guest import (
    PLAN_EXPIRED_MESSAGE,
    PLAN_TTL_DAYS,
    is_plan_expired,
    plan_days_left,
    plan_expires_at,
    plan_ttl_days,
    purge_expired_plans,
)
from app.services.plan_service import PlanService

USER_ID = "11111111-1111-1111-1111-111111111111"


def _plan(*, user_id=None, challenge=False, created_at=None):
    return SimpleNamespace(
        user_id=user_id,
        challenge_100_days=challenge,
        created_at=created_at or datetime.now(UTC),
    )


def test_all_plans_have_110_day_ttl():
    created = datetime(2026, 1, 1, tzinfo=UTC)
    guest = _plan(created_at=created)
    owned = _plan(user_id="u1", created_at=created)
    challenge = _plan(user_id="u1", challenge=True, created_at=created)
    assert plan_ttl_days(guest) == PLAN_TTL_DAYS
    assert plan_ttl_days(owned) == PLAN_TTL_DAYS
    assert plan_expires_at(guest) == created + timedelta(days=110)
    assert plan_expires_at(owned) == created + timedelta(days=110)
    assert plan_expires_at(challenge) == created + timedelta(days=110)


def test_not_expired_at_109_days():
    plan = _plan(user_id="u1", created_at=datetime.now(UTC) - timedelta(days=109))
    assert is_plan_expired(plan) is False
    assert plan_days_left(plan) and plan_days_left(plan) >= 1


def test_expired_at_111_days_for_guest_and_owned():
    created = datetime.now(UTC) - timedelta(days=111)
    guest = _plan(created_at=created)
    owned = _plan(user_id="u1", created_at=created)
    assert is_plan_expired(guest) is True
    assert is_plan_expired(owned) is True
    assert plan_days_left(guest) == 0
    assert plan_days_left(owned) == 0


def test_still_valid_at_101_days():
    plan = _plan(created_at=datetime.now(UTC) - timedelta(days=101))
    assert is_plan_expired(plan) is False


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _insert_user(db):
    user = User(
        id=USER_ID,
        email="u@test.com",
        password_hash="x",
        display_name="U",
        role="user",
        created_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    return user


def _insert_plan(db, *, title: str, share_token: str, created_at: datetime, user_id=None):
    plan = UserDailyPlan(
        user_id=user_id,
        title_vi=title,
        source="ai",
        share_token=share_token,
        created_at=created_at.replace(tzinfo=None) if created_at.tzinfo else created_at,
        updated_at=(created_at.replace(tzinfo=None) if created_at.tzinfo else created_at),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def test_purge_deletes_all_plans_past_110_days():
    db = _db()
    user = _insert_user(db)
    now = datetime.now(UTC)
    old = now - timedelta(days=111)
    fresh = now - timedelta(days=10)
    _insert_plan(db, title="Guest cũ", share_token="g-old", created_at=old)
    _insert_plan(db, title="Owned cũ", share_token="o-old", created_at=old, user_id=user.id)
    keep_guest = _insert_plan(db, title="Guest mới", share_token="g-new", created_at=fresh)
    keep_owned = _insert_plan(
        db, title="Owned mới", share_token="o-new", created_at=fresh, user_id=user.id
    )

    deleted = purge_expired_plans(db)
    assert deleted == 2
    ids = {p.id for p in db.query(UserDailyPlan).all()}
    assert ids == {keep_guest.id, keep_owned.id}


def test_share_and_owned_get_delete_expired_plan():
    db = _db()
    user = _insert_user(db)
    old = datetime.now(UTC) - timedelta(days=111)
    plan = _insert_plan(
        db, title="Hết hạn", share_token="expired-token", created_at=old, user_id=user.id
    )
    plans = PlanService(db)
    with pytest.raises(AppException) as share_err:
        plans.get_by_share_token("expired-token")
    assert share_err.value.status_code == 404
    assert PLAN_EXPIRED_MESSAGE in str(share_err.value)
    assert db.get(UserDailyPlan, plan.id) is None

    plan2 = _insert_plan(
        db, title="Hết hạn 2", share_token="expired-owned", created_at=old, user_id=user.id
    )
    with pytest.raises(AppException) as owned_err:
        plans.get_plan(user.id, plan2.id)
    assert owned_err.value.status_code == 404
    assert db.get(UserDailyPlan, plan2.id) is None
    assert plans.list_plans(user.id) == []
