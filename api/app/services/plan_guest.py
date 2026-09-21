"""Guest plan TTL helpers."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import UserDailyPlan

GUEST_TTL_DAYS = 100
GUEST_CHALLENGE_TTL_DAYS = 110
GUEST_EXPIRED_MESSAGE = (
    "Lịch đã hết hạn và đã bị xóa. Tạo lịch mới, hoặc lần sau hãy đăng nhập để lưu vào tài khoản."
)


def aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def guest_ttl_days(plan: Any) -> int | None:
    if getattr(plan, "user_id", None) is not None:
        return None
    if bool(getattr(plan, "challenge_100_days", False)):
        return GUEST_CHALLENGE_TTL_DAYS
    return GUEST_TTL_DAYS


def guest_expires_at(plan: Any) -> datetime | None:
    ttl = guest_ttl_days(plan)
    if ttl is None:
        return None
    created = getattr(plan, "created_at", None)
    if created is None:
        return None
    return aware(created) + timedelta(days=ttl)


def guest_days_left(plan: Any) -> int | None:
    expires = guest_expires_at(plan)
    if expires is None:
        return None
    seconds = (expires - datetime.now(UTC)).total_seconds()
    if seconds <= 0:
        return 0
    return max(1, math.ceil(seconds / 86400))


def is_guest_expired(plan: Any) -> bool:
    expires = guest_expires_at(plan)
    return expires is not None and datetime.now(UTC) >= expires


def purge_expired_guest_plans(db: Session) -> int:
    """Delete guest plans past 100/110 days. Returns number deleted."""
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=GUEST_TTL_DAYS)
    guests = (
        db.query(UserDailyPlan)
        .filter(
            UserDailyPlan.user_id.is_(None),
            UserDailyPlan.created_at <= cutoff.replace(tzinfo=None)
            if cutoff.tzinfo
            else cutoff,
        )
        .all()
    )
    deleted = 0
    for plan in guests:
        if is_guest_expired(plan):
            db.delete(plan)
            deleted += 1
    if deleted:
        db.commit()
    return deleted
