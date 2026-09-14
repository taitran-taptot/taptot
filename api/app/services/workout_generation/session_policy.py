"""Cap sessions, weeks, and heavy splits by training capacity.

Longest session option is 90 minutes. Weekly volume + deny lists keep dose safe.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.workout_generation.capacity import TrainingCapacity

_GAIN = frozenset({"gain_weight", "gain_muscle"})
_LOSS = frozenset({"lose_weight"})


# Thử thách 100 ngày ≈ 14 tuần (3 pha: 4 + 4 + 6, deload 4/8/14).
CHALLENGE_WEEKS = 14
MIN_WEEKS = 4
MAX_WEEKS = 8
# Alias tương thích (request cũ curriculum_12_weeks).
CURRICULUM_WEEKS = CHALLENGE_WEEKS

# Phase week ranges for the 100-day challenge (1-indexed inclusive).
CHALLENGE_PHASE_RANGES: tuple[tuple[int, int], ...] = ((1, 4), (5, 8), (9, 14))
CHALLENGE_DELOAD_WEEKS: tuple[int, ...] = (4, 8, 14)


@dataclass(frozen=True)
class SessionPolicy:
    max_sessions: int
    max_minutes: int
    max_weeks: int
    allow_pplul: bool
    allow_ppl_x2: bool
    cardio_on_lift_days: bool
    easy_cardio: bool
    liss_finisher: bool = False
    reason_vi: str | None = None

    def clamp_sessions(self, requested: int) -> int:
        n = max(2, min(6, int(requested or 3)))
        return min(n, self.max_sessions)

    def clamp_minutes(self, requested: int) -> int:
        n = max(30, int(requested or 45))
        return min(n, self.max_minutes)

    def clamp_weeks(
        self,
        requested: int,
        *,
        challenge: bool = False,
        curriculum: bool = False,
    ) -> int:
        if curriculum or challenge:
            return CHALLENGE_WEEKS
        n = max(MIN_WEEKS, int(requested or MIN_WEEKS))
        return min(n, min(self.max_weeks, MAX_WEEKS))


def challenge_phase_index(week: int) -> int:
    """Map global week 1..14 → phase 0/1/2."""
    w = max(1, int(week))
    for i, (lo, hi) in enumerate(CHALLENGE_PHASE_RANGES):
        if lo <= w <= hi:
            return i
    return len(CHALLENGE_PHASE_RANGES) - 1


def challenge_local_week(week: int) -> int:
    """Week index within the current challenge phase (1-based)."""
    idx = challenge_phase_index(week)
    lo, _ = CHALLENGE_PHASE_RANGES[idx]
    return max(1, int(week) - lo + 1)


def resolve_session_policy(
    capacity: TrainingCapacity,
    *,
    goal: str | None = None,
    session_minutes: int | None = 45,
    extra_goals: list[str] | None = None,
    no_equipment: bool = False,
    location: str | None = None,
) -> SessionPolicy:
    g = (goal or "").strip().lower()
    gain = g in _GAIN
    loss = g in _LOSS
    beginner = capacity.effective_level <= 1 or capacity.strength_tier == "weak"
    try:
        mins = int(session_minutes or 45)
    except (TypeError, ValueError):
        mins = 45
    extras = {str(x).strip().lower() for x in (extra_goals or [])}
    loc = (location or "").strip().lower()
    # Master gym table adds a cardio block from 60 minutes up; home no-equip always HIIT.
    long_enough_for_cardio = mins >= 60 or (bool(no_equipment) and loc == "home")
    want_liss = mins >= 45 and (
        "endurance" in extras or "lose_weight" in extras or loss
    )

    if beginner:
        return SessionPolicy(
            max_sessions=5,
            max_minutes=90,
            max_weeks=MAX_WEEKS,
            allow_pplul=True,
            allow_ppl_x2=False,
            cardio_on_lift_days=long_enough_for_cardio,
            easy_cardio=gain or not loss,
            liss_finisher=want_liss,
            reason_vi=(
                "Người mới: tối đa 5 buổi/tuần. 5 buổi theo bảng Master (nam PPLUL / nữ LULU + Cardio-Core); "
                "thời lượng buổi giữ theo lựa chọn; buổi ≥60 phút có LISS (xe đạp/đi bộ), "
                "volume tuần vẫn bị kẹp."
            ),
        )
    if capacity.effective_level <= 2:
        return SessionPolicy(
            max_sessions=6,
            max_minutes=90,
            max_weeks=MAX_WEEKS,
            allow_pplul=True,
            allow_ppl_x2=False,
            cardio_on_lift_days=long_enough_for_cardio,
            easy_cardio=gain,
            liss_finisher=want_liss,
            reason_vi=None,
        )
    return SessionPolicy(
        max_sessions=6,
        max_minutes=90,
        max_weeks=MAX_WEEKS,
        allow_pplul=True,
        allow_ppl_x2=False,
        cardio_on_lift_days=long_enough_for_cardio,
        easy_cardio=gain,
        liss_finisher=want_liss,
        reason_vi=None,
    )
