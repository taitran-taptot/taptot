"""Plan helpers. Workout plans are kept until someone deletes them."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

PINNED_SHARE_TOKENS = frozenset({"nhapmon"})


def is_pinned_public_plan(plan: Any) -> bool:
    token = str(getattr(plan, "share_token", "") or "").strip().lower()
    return token in PINNED_SHARE_TOKENS


def aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def plan_expires_at(plan: Any) -> datetime | None:
    return None


def plan_days_left(plan: Any) -> int | None:
    return None


def is_plan_expired(plan: Any) -> bool:
    return False


def purge_expired_plans(db: Session) -> int:
    """Plans are no longer deleted by age. Kept so older callers stay safe."""
    return 0


def purge_expired_guest_plans(db: Session) -> int:
    return purge_expired_plans(db)
