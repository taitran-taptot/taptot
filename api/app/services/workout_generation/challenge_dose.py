"""Challenge-only set allocation: floor 2, cap 3 (L1) / 4 (L2+)."""

from __future__ import annotations

from typing import Any

_MAIN = "main"
_SKIP_ROLES = frozenset({"cardio", "conditioning", "mobility"})
_COMPOUND_ROLES = frozenset({"compound", "resistance"})
FALLBACK_LOAD_NOTE_VI = "Chọn tải còn dư 2–3 cái."


def challenge_set_cap(experience_level: int) -> int:
    return 3 if int(experience_level or 1) <= 1 else 4


TEST_LIFT_SETS_BY_PHASE = (3, 4, 3)


def challenge_test_lift_sets(phase_index: int) -> int:
    """Working sets on the day's test lift: P1 3, P2 4, P3 3."""
    try:
        idx = max(0, min(2, int(phase_index)))
    except (TypeError, ValueError):
        idx = 0
    return TEST_LIFT_SETS_BY_PHASE[idx]


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
    phase_index: int | None = None,
) -> None:
    """Clamp main strength sets to [2, cap]. Prefer keeping compounds at the floor.

    Phase 2 allows 4 sets on the first compound (test lift) so the +1 is not swallowed.
    """
    cap = challenge_set_cap(experience_level)
    try:
        phase = None if phase_index is None else max(0, min(2, int(phase_index)))
    except (TypeError, ValueError):
        phase = None
    floor = 2
    for day in plan_days or []:
        saw_test = False
        for ex in list(getattr(day, "exercises", None) or []):
            eid = int(getattr(ex, "exercise_id", 0) or 0)
            meta = meta_by_id.get(eid) or {}
            if not _is_strength_main(ex, meta):
                continue
            try:
                sets = int(getattr(ex, "sets", None) or floor)
            except (TypeError, ValueError):
                sets = floor
            this_cap = cap
            slug = str(meta.get("muscle_slug") or "").strip().lower()
            is_core = slug in {"bung", "core"} or slug.startswith("core") or "bung" in slug
            is_test = (
                (not saw_test)
                and (not is_core)
                and _role(meta) in _COMPOUND_ROLES
            )
            if is_test:
                saw_test = True
                if phase == 1:
                    this_cap = max(this_cap, challenge_test_lift_sets(1))
                elif phase in (0, 2):
                    sets = min(sets, challenge_test_lift_sets(phase))
            ex.sets = max(floor, min(this_cap, sets))
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
