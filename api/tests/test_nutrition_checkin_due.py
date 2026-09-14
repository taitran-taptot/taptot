"""Nutrition check-in due dates for challenge vs regular plans."""

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

from app.services.plan_service import _nutrition_checkin_due


def _plan(*, start=None, created_at=None):
    return SimpleNamespace(
        start_date=start,
        created_at=created_at or datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_challenge_first_checkin_due_plus_28():
    plan = _plan(start=date(2026, 1, 1))
    due = _nutrition_checkin_due(plan, {"challenge_100_days": True})
    assert due == date(2026, 1, 29)


def test_curriculum_insight_also_uses_28():
    plan = _plan(start=date(2026, 1, 1))
    due = _nutrition_checkin_due(plan, {"curriculum": {"deload_weeks": [4, 8, 14]}})
    assert due == date(2026, 1, 29)


def test_regular_first_checkin_due_plus_14():
    plan = _plan(start=date(2026, 1, 1))
    due = _nutrition_checkin_due(plan, {"nutrition_block_size": 2})
    assert due == date(2026, 1, 15)


def test_challenge_after_one_checkin_due_plus_56():
    plan = _plan(start=date(2026, 1, 1))
    due = _nutrition_checkin_due(
        plan,
        {
            "challenge_100_days": True,
            "nutrition_checkins": [{"at": "2026-01-29", "weight_kg": 69}],
        },
    )
    assert due == date(2026, 2, 26)  # start + 28 * 2


def test_explicit_interval_overrides_default():
    plan = _plan(start=date(2026, 1, 1))
    due = _nutrition_checkin_due(
        plan,
        {"challenge_100_days": True, "nutrition_checkin_interval_days": 21},
    )
    assert due == date(2026, 1, 22)
