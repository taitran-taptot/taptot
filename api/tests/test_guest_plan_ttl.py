from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.entities import User, UserDailyPlan
from app.services.plan_guest import (
    is_plan_expired,
    plan_days_left,
    plan_expires_at,
    purge_expired_plans,
)
from app.services.plan_service import PlanService

USER_ID = "11111111-1111-1111-1111-111111111111"


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


def test_old_plans_do_not_expire():
    created = datetime(2020, 1, 1, tzinfo=UTC)
    plan = UserDailyPlan(title_vi="Cũ", source="ai", share_token="old", created_at=created)
    assert is_plan_expired(plan) is False
    assert plan_expires_at(plan) is None
    assert plan_days_left(plan) is None


def test_purge_keeps_plans_older_than_four_months():
    db = _db()
    user = _insert_user(db)
    old = datetime.now(UTC) - timedelta(days=200)
    guest = _insert_plan(db, title="Guest cũ", share_token="g-old", created_at=old)
    owned = _insert_plan(db, title="Owned cũ", share_token="o-old", created_at=old, user_id=user.id)

    assert purge_expired_plans(db) == 0
    ids = {p.id for p in db.query(UserDailyPlan).all()}
    assert ids == {guest.id, owned.id}


def test_share_and_owned_get_keep_old_plan():
    db = _db()
    user = _insert_user(db)
    old = datetime.now(UTC) - timedelta(days=200)
    plan = _insert_plan(
        db, title="Cũ", share_token="old-token", created_at=old, user_id=user.id
    )
    plans = PlanService(db)
    shared = plans.get_by_share_token("old-token")
    owned = plans.get_plan(user.id, plan.id)
    listed = plans.list_plans(user.id)

    assert shared["id"] == plan.id
    assert owned["id"] == plan.id
    assert shared["expires_at"] is None
    assert shared["days_left"] is None
    assert [row["id"] for row in listed] == [plan.id]
    assert db.get(UserDailyPlan, plan.id) is not None
