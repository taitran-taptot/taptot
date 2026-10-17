"""Challenge-only set allocation: floor 2, cap 3 (L1) / 4 (L2+)."""

from __future__ import annotations

from typing import Any

_MAIN = "main"
_SKIP_ROLES = frozenset({"cardio", "conditioning", "mobility"})
_COMPOUND_ROLES = frozenset({"compound", "resistance"})
FALLBACK_LOAD_NOTE_VI = "Chọn tải còn dư 2–3 cái."


def challenge_set_cap(experience_level: int) -> int:
    return 3 if int(experience_level or 1) <= 1 else 4


def _role(meta: dict[str, Any] | None) -> str:
    return str((meta or {}).get("movement_role") or "").strip().lower()


def _is_strength_main(ex: Any, meta: dict[str, Any] | None) -> bool:
    if str(getattr(ex, "section", "main") or "main") != _MAIN:
        return False
    return _role(meta) not in _SKIP_ROLES


def allocate_challenge_sets(
    plan_days: list[Any],
    *,
    meta_by_id: dict[int, dict[str, Any]],
    experience_level: int,
) -> None:
    """Clamp main strength sets to [2, cap]. Prefer keeping compounds at the floor."""
    cap = challenge_set_cap(experience_level)
    floor = 2
    for day in plan_days or []:
        for ex in list(getattr(day, "exercises", None) or []):
            eid = int(getattr(ex, "exercise_id", 0) or 0)
            meta = meta_by_id.get(eid) or {}
            if not _is_strength_main(ex, meta):
                continue
            try:
                sets = int(getattr(ex, "sets", None) or floor)
            except (TypeError, ValueError):
                sets = floor
            ex.sets = max(floor, min(cap, sets))
            if _role(meta) in _COMPOUND_ROLES and ex.sets < floor:
                ex.sets = floor
            notes = str(getattr(ex, "notes_vi", None) or "").strip()
            rx = list(getattr(ex, "set_prescriptions", None) or [])
            if not notes and not rx:
                from app.services.workout_generation.load_estimate import (
                    is_band_exercise,
                    is_dumbbell_exercise,
                )

                if is_dumbbell_exercise(meta) or is_band_exercise(meta):
                    ex.notes_vi = FALLBACK_LOAD_NOTE_VI
            elif rx:
                n = max(1, int(ex.sets))
                if len(rx) != n:
                    first = rx[0]
                    ex.set_prescriptions = [first for _ in range(n)]
