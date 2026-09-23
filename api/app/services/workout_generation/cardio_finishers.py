"""100-day challenge cardio allowlist and dose kinds (interval vs leftover minutes)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.services.workout_generation.weekly_volume import fold_lift_name

_INTERVAL_NEEDLES = (
    ("shadow boxing", "dam bong", "boxing tuong"),
    ("jumping jack", "nhay dang", "nhay jacks"),
    ("jump rope", "nhay day"),
    ("running interval", "chay ngat", "interval run"),
)

_CONTINUOUS_NEEDLES = (
    ("hiking", "di bo duong dai"),
    ("trail run", "chay ben", "chay dia hinh"),
)


def _blob(name_vi: str | None, name_en: str | None) -> str:
    return fold_lift_name(f"{name_vi or ''} {name_en or ''}")


def _matches(blob: str, groups: tuple[tuple[str, ...], ...]) -> bool:
    if not blob:
        return False
    return any(any(needle in blob for needle in group) for group in groups)


def is_interval_finisher_name(
    name_vi: str | None = None, name_en: str | None = None
) -> bool:
    """Shadow Boxing, Jumping Jack, Jump Rope, Running Intervals."""
    return _matches(_blob(name_vi, name_en), _INTERVAL_NEEDLES)


def is_continuous_finisher_name(
    name_vi: str | None = None, name_en: str | None = None
) -> bool:
    """Hiking / Trail Run: 1 set leftover minutes."""
    return _matches(_blob(name_vi, name_en), _CONTINUOUS_NEEDLES)


def is_challenge_cardio_name(
    name_vi: str | None = None, name_en: str | None = None
) -> bool:
    return is_interval_finisher_name(name_vi, name_en) or is_continuous_finisher_name(
        name_vi, name_en
    )


def filter_challenge_cardio_items(items: Iterable[Any]) -> list[Any]:
    """Keep only the 6 allowed challenge cardio names."""
    kept: list[Any] = []
    for item in items:
        vi = getattr(item, "name_vi", None)
        en = getattr(item, "name_en", None)
        if isinstance(item, dict):
            vi = item.get("name_vi")
            en = item.get("name_en")
        if is_challenge_cardio_name(vi, en):
            kept.append(item)
    return kept
