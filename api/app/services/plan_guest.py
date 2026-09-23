"""Plan TTL helpers — every workout plan expires 110 days after creation."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import UserDailyPlan

PLAN_TTL_DAYS = 110
PLAN_EXPIRED_MESSAGE = "Lịch đã hết hạn và đã bị xóa."

# Back-compat aliases used by older imports/tests.
GUEST_TTL_DAYS = PLAN_TTL_DAYS
GUEST_CHALLENGE_TTL_DAYS = PLAN_TTL_DAYS
GUEST_EXPIRED_MESSAGE = PLAN_EXPIRED_MESSAGE


def aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def plan_ttl_days(_plan: Any = None) -> int:
    return PLAN_TTL_DAYS


def guest_ttl_days(_plan: Any = None) -> int:
    return plan_ttl_days(_plan)


def plan_expires_at(plan: Any) -> datetime | None:
    created = getattr(plan, "created_at", None)
    if created is None:
        return None
    return aware(created) + timedelta(days=PLAN_TTL_DAYS)


def guest_expires_at(plan: Any) -> datetime | None:
    return plan_expires_at(plan)


def plan_days_left(plan: Any) -> int | None:
    expires = plan_expires_at(plan)
    if expires is None:
        return None
    seconds = (expires - datetime.now(UTC)).total_seconds()
    if seconds <= 0:
        return 0
    return max(1, math.ceil(seconds / 86400))


def guest_days_left(plan: Any) -> int | None:
    return plan_days_left(plan)


def is_plan_expired(plan: Any) -> bool:
    expires = plan_expires_at(plan)
    return expires is not None and datetime.now(UTC) >= expires


def is_guest_expired(plan: Any) -> bool:
    return is_plan_expired(plan)


def purge_expired_plans(db: Session) -> int:
    """Delete plans past 110 days. Returns number deleted."""
    cutoff = datetime.now(UTC) - timedelta(days=PLAN_TTL_DAYS)
    cutoff_naive = cutoff.replace(tzinfo=None)
    rows = (
        db.query(UserDailyPlan)
        .filter(UserDailyPlan.created_at <= cutoff_naive)
        .all()
    )
    deleted = 0
    for plan in rows:
        if is_plan_expired(plan):
            db.delete(plan)
            deleted += 1
    if deleted:
        db.commit()
    return deleted


def purge_expired_guest_plans(db: Session) -> int:
    return purge_expired_plans(db)
