"""Local coach notes and schedule-summary helpers."""

from __future__ import annotations

from typing import Any

from app.services.workout_generation.session_duration import (
    estimate_day_minutes,
    parse_reps_minutes,
    parse_reps_seconds,
)

GOAL_VI = {
    "lose_weight": "Giảm cân",
    "maintain": "Giữ cân",
    "gain_weight": "Tăng cân",
    "gain_muscle": "Tăng cơ",
}

EXTRA_GOAL_VI = {
    "endurance": "Sức bền",
    "flexibility": "Dẻo dai",
    "strength": "Sức mạnh",
    "muscle": "Tăng cơ",
    "fat_loss": "Giảm mỡ",
    "physique": "Cải thiện vóc dáng",
    "mental_health": "Sức khỏe tinh thần",
    "heartbreak_recovery": "Phục hồi sau thất tình",
}

FALLBACK_ADVICE = [
    "Khởi động kỹ trước working sets; tăng dần mức tạ nếu dùng tạ.",
    "Giữ form đúng; giảm tạ hoặc đổi biến thể dễ hơn nếu form vỡ.",
    "Ngủ đủ và ăn đủ protein để phục hồi giữa các buổi.",
]

_ALLOWED_REST = frozenset({60, 90, 120, 180})
_ALLOWED_SETS = frozenset({2, 3, 4, 5})


def build_schedule_summary(
    frame: Any,
    plan_days: list[Any],
    *,
    session_minutes: int,
    location: str,
) -> dict[str, Any]:
    days_out = []
    for day in plan_days:
        exs = []
        for ex in getattr(day, "exercises", []) or []:
            exs.append(
                {
                    "exercise_id": ex.exercise_id,
                    "sets": ex.sets,
                    "reps": ex.reps,
                    "rest_seconds": getattr(ex, "rest_seconds", None),
                    "section": ex.section,
                }
            )
        days_out.append(
            {
                "day_number": day.day_number,
                "title_vi": day.title_vi,
                "split_role": day.split_role,
                "estimate_min": int(estimate_day_minutes(day)),
                "exercises": exs,
            }
        )
    return {
        "frame_code": getattr(frame, "code", ""),
        "frame_name_vi": getattr(frame, "name_vi", ""),
        "week_code": getattr(frame, "week_code", ""),
        "session_minutes": session_minutes,
        "location": location,
        "days": days_out,
    }


def generate_coach_advice(
    payload: dict[str, Any],
    schedule_summary: dict[str, Any],
    *,
    exercise_names: dict[int, str] | None = None,
) -> dict[str, Any]:
    """Return local fallback coach copy. Does not mutate schedule."""
    del payload, schedule_summary, exercise_names
    return {
        "advice_vi": list(FALLBACK_ADVICE),
        "summary_vi": None,
        "week_notes_vi": None,
        "swaps": [],
        "duration_tweaks": [],
    }


def apply_schedule_swaps(
    plan_days: list[Any],
    swaps: list[dict[str, Any]] | None,
    allowed_ids_by_day: dict[int, set[int]],
) -> list[Any]:
    """Replace exercise ids when to_id is on that day's shortlist. Same slot count."""
    for swap in swaps or []:
        try:
            day_n = int(swap.get("day_number"))
            from_id = int(swap.get("from_id"))
            to_id = int(swap.get("to_id"))
        except (TypeError, ValueError, AttributeError):
            continue
        allowed = allowed_ids_by_day.get(day_n) or set()
        if to_id not in allowed or to_id == from_id:
            continue
        for day in plan_days:
            if int(getattr(day, "day_number", 0) or 0) != day_n:
                continue
            used = {int(ex.exercise_id) for ex in day.exercises}
            if to_id in used:
                continue
            for ex in day.exercises:
                if int(ex.exercise_id) == from_id:
                    ex.exercise_id = to_id
                    break
    return plan_days


def apply_duration_tweaks(
    plan_days: list[Any],
    tweaks: list[dict[str, Any]] | None,
    allowed_ids_by_day: dict[int, set[int]] | None = None,
) -> list[Any]:
    """Apply validated set/rest/cardio-minute tweaks. Ignores unknown ids."""
    for raw in tweaks or []:
        try:
            day_n = int(raw.get("day_number"))
            eid = int(raw.get("exercise_id"))
        except (TypeError, ValueError, AttributeError):
            continue
        allowed = (allowed_ids_by_day or {}).get(day_n)
        for day in plan_days:
            if int(getattr(day, "day_number", 0) or 0) != day_n:
                continue
            for ex in day.exercises:
                if int(ex.exercise_id) != eid:
                    continue
                if allowed is not None and eid not in allowed and (ex.section or "") == "main":
                    # Already on the day — tweaking sets/rest of a picked lift is OK.
                    pass
                if raw.get("sets") is not None:
                    try:
                        sets = int(raw["sets"])
                    except (TypeError, ValueError):
                        sets = None
                    else:
                        if sets in _ALLOWED_SETS:
                            ex.sets = sets
                if raw.get("rest_seconds") is not None:
                    try:
                        rest = int(raw["rest_seconds"])
                    except (TypeError, ValueError):
                        rest = None
                    else:
                        if rest in _ALLOWED_REST:
                            ex.rest_seconds = rest
                reps = raw.get("reps")
                if isinstance(reps, str):
                    if parse_reps_minutes(reps) is not None:
                        # Continuous cardio only — do not rewrite interval (giây) pieces.
                        if parse_reps_minutes(ex.reps) is not None:
                            ex.reps = f"{parse_reps_minutes(reps)} phút"
                    elif parse_reps_seconds(reps) is not None and parse_reps_seconds(
                        ex.reps
                    ) is not None:
                        ex.reps = reps
                break
    return plan_days
