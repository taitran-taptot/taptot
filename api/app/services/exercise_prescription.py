"""Resolve default sets/reps from experience_level × movement_role."""

from __future__ import annotations

from typing import NamedTuple

from sqlalchemy.orm import Session

from app.models.entities import ExercisePrescriptionDefault
from app.services.exercise_prescription_seed import PRESCRIBABLE_ROLES

HYPERTROPHY_GOALS = frozenset({"gain_muscle", "gain_weight"})
FAT_LOSS_GOALS = frozenset({"lose_weight"})


class Prescription(NamedTuple):
    sets: int
    reps: str
    rpe: int


def clamp_experience_level(level: int | None) -> int:
    """Map user level into seeded range 1–3 (L4+ uses L3 until seeded)."""
    try:
        n = int(level if level is not None else 2)
    except (TypeError, ValueError):
        n = 2
    if n < 1:
        return 1
    if n > 3:
        return 3
    return n


def reps_range_from_center(center: int, *, role: str, goal: str | None) -> str:
    g = (goal or "").strip().lower()
    if role == "isolation":
        lo, hi = center - 3, center + 3
        if g in FAT_LOSS_GOALS:
            hi += 2
    else:
        lo, hi = center - 2, center + 2
        if g in HYPERTROPHY_GOALS:
            hi += 1
    lo = max(5, int(lo))
    hi = min(20, max(lo + 1, int(hi)))
    return f"{lo}-{hi}"


def rpe_for(level: int, role: str) -> int:
    if level <= 1:
        return 7
    if level == 2:
        return 8
    return 8 if role == "compound" else 7


def beginner_effort_cue(rpe: int, reps: str | int, *, loaded: bool = True) -> str:
    from app.services.workout_generation.coach_notes import working_note_vi

    return working_note_vi(reps, loaded=loaded, include_progress=False, rpe=rpe)


def get_prescription(
    db: Session,
    experience_level: int | None,
    movement_role: str | None,
    *,
    goal: str | None = None,
    extra_goals: list[str] | None = None,
) -> Prescription | None:
    """Return sets + rep range + RPE for compound/isolation; else None."""
    role = (movement_role or "").strip().lower()
    # Home Master slots map onto gym prescription rows
    if role == "resistance":
        role = "compound"
    elif role == "conditioning":
        role = "isolation"
    if role not in PRESCRIBABLE_ROLES:
        return None

    level = clamp_experience_level(experience_level)
    cache: dict[tuple[int, str], ExercisePrescriptionDefault | None] = db.info.setdefault(
        "_prescription_row_cache", {}
    )
    cache_key = (level, role)
    if cache_key not in cache:
        cache[cache_key] = (
            db.query(ExercisePrescriptionDefault)
            .filter(
                ExercisePrescriptionDefault.experience_level == level,
                ExercisePrescriptionDefault.movement_role == role,
            )
            .one_or_none()
        )
    row = cache[cache_key]
    if not row:
        return None
    extras = {str(x).strip().lower() for x in (extra_goals or [])}
    g = (goal or "").strip().lower()
    center = int(row.default_reps)
    range_goal = goal
    if "strength" in extras and role == "compound":
        center = 6
        range_goal = None
    elif (
        level >= 3
        and role == "compound"
        and g in HYPERTROPHY_GOALS
        and "strength" not in extras
    ):
        center = 10
        range_goal = None
    reps = reps_range_from_center(center, role=role, goal=range_goal)
    rpe = rpe_for(level, role)
    if extras & {"mental_health", "heartbreak_recovery"}:
        rpe = max(6, rpe - 1)
    return Prescription(int(row.default_sets), reps, rpe)
