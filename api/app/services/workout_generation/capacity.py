"""Map fitness tests + claimed experience → training capacity (MVP rules)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.exercise_prescription import clamp_experience_level

# Per-test score 0–2. Missing tests are skipped (not treated as 0).
_PUSHUP_CUTS = (5, 15)
_SQUAT_CUTS = (10, 25)
_PLANK_CUTS = (20, 60)
_PULLUP_CUTS = (1, 8)

_TIER_WEAK_MAX = 0.75
_TIER_STRONG_MIN = 1.5


@dataclass(frozen=True)
class TrainingCapacity:
    claimed_level: int
    effective_level: int
    strength_tier: str  # weak | ok | strong
    tests_used: int
    reason_vi: str | None
    conservative_volume: bool = False


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return max(0, n)


def _score_cuts(value: int | None, low: int, high: int) -> int | None:
    if value is None:
        return None
    if value < low:
        return 0
    if value < high:
        return 1
    return 2


def _baseline_dict(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if hasattr(raw, "model_dump"):
        return dict(raw.model_dump())
    if isinstance(raw, dict):
        return raw
    return {}


def resolve_capacity(
    experience_level: int | None,
    fitness_baseline: Any = None,
    *,
    sessions_per_week: int | None = None,  # noqa: ARG001 — reserved for split scoring
) -> TrainingCapacity:
    claimed = clamp_experience_level(experience_level)
    base = _baseline_dict(fitness_baseline)

    scores: list[int] = []
    for key, cuts in (
        ("pushups_max", _PUSHUP_CUTS),
        ("squats_max", _SQUAT_CUTS),
        ("plank_seconds", _PLANK_CUTS),
        ("pullups_max", _PULLUP_CUTS),
    ):
        scored = _score_cuts(_as_int(base.get(key)), *cuts)
        if scored is not None:
            scores.append(scored)

    if not scores:
        if claimed >= 3:
            return TrainingCapacity(
                claimed_level=claimed,
                effective_level=claimed,
                strength_tier="ok",
                tests_used=0,
                reason_vi=(
                    "Chưa đủ 2 bài test thể lực — giữ khung 6–12 tháng, giảm volume cho an toàn."
                ),
                conservative_volume=True,
            )
        return TrainingCapacity(
            claimed_level=claimed,
            effective_level=claimed,
            strength_tier="ok",
            tests_used=0,
            reason_vi=None,
        )

    avg = sum(scores) / len(scores)
    if avg <= _TIER_WEAK_MAX:
        tier = "weak"
    elif avg >= _TIER_STRONG_MIN:
        tier = "strong"
    else:
        tier = "ok"

    effective = claimed
    reason: str | None = None
    conservative = False
    if tier == "weak":
        effective = max(1, claimed - 1)
        if claimed > effective:
            reason = (
                "Test thể lực thấp hơn mức kinh nghiệm khai báo — hạ độ khó / volume một bậc."
            )
        else:
            reason = "Test thể lực yếu — giữ lịch ở mức người mới."
    # strong never auto-promotes above claimed level
    tests_used = len(scores)
    if claimed >= 3 and tests_used < 2:
        conservative = True
        if reason is None:
            reason = (
                "Chưa đủ 2 bài test thể lực — giữ khung 6–12 tháng, giảm volume cho an toàn."
            )

    return TrainingCapacity(
        claimed_level=claimed,
        effective_level=effective,
        strength_tier=tier,
        tests_used=tests_used,
        reason_vi=reason,
        conservative_volume=conservative,
    )
