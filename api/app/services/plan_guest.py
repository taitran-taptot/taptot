"""Plan TTL helpers — every workout plan expires 4 calendar months after creation."""

from __future__ import annotations

import calendar
import math
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import UserDailyPlan

PLAN_TTL_MONTHS = 4
PLAN_EXPIRED_MESSAGE = "Lịch đã hết hạn và đã bị xóa."


def aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def add_months(dt: datetime, months: int) -> datetime:
    """Shift a datetime by calendar months, clamping the day to the target month."""
    dt = aware(dt)
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def plan_ttl_days(plan: Any = None) -> int:
    created = getattr(plan, "created_at", None)
    if created is None:
        created = datetime.now(UTC)
    created = aware(created)
    return (add_months(created, PLAN_TTL_MONTHS) - created).days


def plan_expires_at(plan: Any) -> datetime | None:
    created = getattr(plan, "created_at", None)
    if created is None:
        return None
    return add_months(created, PLAN_TTL_MONTHS)


def plan_days_left(plan: Any) -> int | None:
    expires = plan_expires_at(plan)
    if expires is None:
        return None
    seconds = (expires - datetime.now(UTC)).total_seconds()
    if seconds <= 0:
        return 0
    return max(1, math.ceil(seconds / 86400))


def is_plan_expired(plan: Any) -> bool:
    expires = plan_expires_at(plan)
    return expires is not None and datetime.now(UTC) >= expires


def purge_expired_plans(db: Session) -> int:
    """Delete plans past 4 calendar months. Returns number deleted."""
    cutoff = add_months(datetime.now(UTC), -PLAN_TTL_MONTHS).replace(tzinfo=None)
    rows = (
        db.query(UserDailyPlan)
        .filter(UserDailyPlan.created_at <= cutoff)
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
