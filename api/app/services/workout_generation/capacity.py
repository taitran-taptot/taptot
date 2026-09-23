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

_PUSHUP_CUTS_F = (3, 10)
_KNEE_CUTS = (8, 20)
_KNEE_CUTS_F = (6, 16)
_PULLUP_CUTS_F = (1, 5)
_ROW_CUTS = (6, 15)
_ROW_CUTS_F = (4, 12)
_PULLDOWN_CUTS = (8, 20)
_DB_REPS_CUTS = (8, 16)
_DB_REPS_CUTS_F = (6, 14)

_TIER_WEAK_MAX = 0.75
_TIER_STRONG_MIN = 1.5

_BAND_LEVEL_MULT = {"light": 0.75, "medium": 1.0, "heavy": 1.15}


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


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if n < 0:
        return None
    return n


def _score_cuts(value: int | None, low: int, high: int) -> int | None:
    if value is None:
        return None
    if value < low:
        return 0
    if value < high:
        return 1
    return 2


def _score_cuts_float(value: float | None, low: float, high: float) -> int | None:
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


def _female(gender: str | None) -> bool:
    return str(gender or "").strip().lower() == "female"


def kit_for_capacity(base: dict[str, Any]) -> str | None:
    """Return a challenge kit only when tests are kit-shaped; else None (legacy BW keys)."""
    raw = str(base.get("test_kit") or "").strip().lower()
    if raw in {"dumbbell", "db", "ta"}:
        return "dumbbell"
    if raw in {"band", "resistance-band", "resistance_band"}:
        return "band"
    if raw in {"bar_rings", "bar-rings", "bar-and-rings", "bodyweight"}:
        return "bar_rings"
    if (
        base.get("db_press_reps") is not None
        or base.get("db_row_reps") is not None
        or base.get("goblet_reps") is not None
    ):
        return "dumbbell"
    variant = str(base.get("pull_test_variant") or "").strip().lower()
    if base.get("band_level") or variant == "band_pulldown":
        return "band"
    if base.get("inverted_rows_max") is not None or variant.startswith("inverted"):
        return "bar_rings"
    return None


def _score_push(base: dict[str, Any], *, female: bool) -> int | None:
    reps = _as_int(base.get("pushups_max"))
    if reps is None:
        return None
    variant = str(base.get("pushup_variant") or "standard").strip().lower()
    if variant == "knee":
        return _score_cuts(reps, *(_KNEE_CUTS_F if female else _KNEE_CUTS))
    return _score_cuts(reps, *(_PUSHUP_CUTS_F if female else _PUSHUP_CUTS))


def _score_pull_bar(base: dict[str, Any], *, female: bool) -> int | None:
    variant = str(base.get("pull_test_variant") or "").strip().lower()
    if variant.startswith("inverted") or (
        _as_int(base.get("inverted_rows_max")) is not None
        and _as_int(base.get("pullups_max")) is None
    ):
        return _score_cuts(
            _as_int(base.get("inverted_rows_max")),
            *(_ROW_CUTS_F if female else _ROW_CUTS),
        )
    return _score_cuts(
        _as_int(base.get("pullups_max")),
        *(_PULLUP_CUTS_F if female else _PULLUP_CUTS),
    )


def _score_pulldown(base: dict[str, Any]) -> int | None:
    reps = _as_int(base.get("pullups_max"))
    if reps is None:
        return None
    mult = _BAND_LEVEL_MULT.get(str(base.get("band_level") or "").strip().lower(), 1.0)
    adjusted = int(round(reps * mult))
    return _score_cuts(adjusted, *_PULLDOWN_CUTS)


def _score_db_lift(
    reps: int | None,
    kg: float | None,
    bw: float | None,
    *,
    female: bool,
    relative_cuts: tuple[float, float],
) -> int | None:
    if reps is None:
        return None
    if kg and bw and bw > 0:
        one_rm = float(kg) * (1.0 + reps / 30.0)
        return _score_cuts_float(one_rm / bw, *relative_cuts)
    return _score_cuts(reps, *(_DB_REPS_CUTS_F if female else _DB_REPS_CUTS))


def capacity_test_scores(
    baseline: dict[str, Any],
    *,
    kit: str,
    gender: str | None = None,
    weight_kg: Any = None,
) -> list[int]:
    """Kit-aware 0–2 scores. Never writes fake pullups_max onto the baseline."""
    female = _female(gender)
    bw = _as_float(weight_kg)
    scores: list[int] = []

    def _add(scored: int | None) -> None:
        if scored is not None:
            scores.append(scored)

    if kit == "dumbbell":
        _add(
            _score_db_lift(
                _as_int(baseline.get("db_press_reps")),
                _as_float(baseline.get("db_press_kg")),
                bw,
                female=female,
                relative_cuts=(0.10, 0.22) if female else (0.12, 0.28),
            )
        )
        _add(
            _score_db_lift(
                _as_int(baseline.get("db_row_reps")),
                _as_float(baseline.get("db_row_kg")),
                bw,
                female=female,
                relative_cuts=(0.10, 0.22) if female else (0.12, 0.28),
            )
        )
        gob_r = _as_int(baseline.get("goblet_reps"))
        if gob_r is None:
            gob_r = _as_int(baseline.get("squats_max"))
        _add(
            _score_db_lift(
                gob_r,
                _as_float(baseline.get("goblet_kg")),
                bw,
                female=female,
                relative_cuts=(0.18, 0.36) if female else (0.22, 0.42),
            )
        )
        _add(_score_cuts(_as_int(baseline.get("plank_seconds")), *_PLANK_CUTS))
        return scores

    _add(_score_push(baseline, female=female))
    if kit == "band":
        _add(_score_pulldown(baseline))
    else:
        _add(_score_pull_bar(baseline, female=female))
    _add(_score_cuts(_as_int(baseline.get("squats_max")), *_SQUAT_CUTS))
    _add(_score_cuts(_as_int(baseline.get("plank_seconds")), *_PLANK_CUTS))
    return scores


def resolve_capacity(
    experience_level: int | None,
    fitness_baseline: Any = None,
    *,
    sessions_per_week: int | None = None,  # noqa: ARG001 — reserved for split scoring
    gender: str | None = None,
    weight_kg: Any = None,
) -> TrainingCapacity:
    claimed = clamp_experience_level(experience_level)
    base = _baseline_dict(fitness_baseline)

    kit = kit_for_capacity(base)
    if kit:
        scores = capacity_test_scores(base, kit=kit, gender=gender, weight_kg=weight_kg)
    else:
        scores = []
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
