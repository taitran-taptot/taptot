"""Weekly hard-set budget and clamp (direct primary muscle only)."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any

from app.services.workout_generation.coverage import (
    coverage_ok,
    families_from_exercises,
    family_of,
    is_real_press,
    required_families,
    required_patterns,
)
from app.services.workout_generation.split_map import is_denied_for_split, normalize_split_role
from app.services.workout_generation.muscle_quotas import (
    BACK_SLUGS,
    BICEPS_SLUGS,
    CHEST_SLUGS,
    CORE_SLUGS,
    GLUTE_SLUGS,
    HINGE_MUSCLE_SLUGS,
    QUAD_SLUGS,
    SHOULDER_SLUGS,
    TRICEPS_SLUGS,
)

_ISOLATION_ROLES = frozenset({"isolation", "conditioning"})
_TRIM_SET_ROLES = frozenset({"isolation", "conditioning", "resistance"})

_LIFT_STEMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("step_up", ("step-up", "step up", "stepup", "buoc len")),
    ("lunge", ("lunge", "split squat", "bulgarian", "chung chan", "chuong chan")),
    ("pushup", ("chong day", "push-up", "push up", "pushup")),
)


def fold_lift_name(text: str) -> str:
    raw = unicodedata.normalize("NFD", (text or "").lower())
    return "".join(ch for ch in raw if unicodedata.category(ch) != "Mn")


def lift_stem(name_vi: str | None, name_en: str | None = None) -> str | None:
    blob = fold_lift_name(f"{name_vi or ''} {name_en or ''}")
    for key, needles in _LIFT_STEMS:
        if any(n in blob for n in needles):
            return key
    return None

# recommended_min, target, max hard sets / week by effective_level
_BUDGET: dict[int, dict[str, tuple[int, int, int]]] = {
    1: {
        "chest": (6, 8, 12),
        "back": (6, 8, 12),
        "quads": (6, 8, 12),
        "hinge": (6, 8, 12),
        "shoulders": (6, 8, 12),
        "biceps": (0, 4, 8),
        "triceps": (0, 2, 6),
        "core": (0, 4, 8),
    },
    2: {
        "chest": (6, 9, 14),
        "back": (6, 9, 14),
        "quads": (6, 9, 14),
        "hinge": (6, 9, 14),
        "shoulders": (4, 6, 10),
        "biceps": (0, 3, 6),
        "triceps": (0, 3, 6),
        "core": (0, 6, 10),
    },
    3: {
        "chest": (8, 10, 16),
        "back": (8, 10, 16),
        "quads": (8, 10, 16),
        "hinge": (8, 10, 16),
        "shoulders": (4, 8, 12),
        "biceps": (2, 4, 8),
        "triceps": (2, 4, 8),
        "core": (0, 6, 12),
    },
}

_TIER_MULT = {"weak": 0.8, "ok": 1.0, "strong": 1.1}

L1_SETS_PER_SESSION_AT_45 = 14
L1_SETS_PER_SESSION_HARD_CAP = 16

_FAM_LABEL_VI = {
    "chest": "ngực",
    "back": "lưng",
    "quads": "đùi trước",
    "hinge": "chuỗi sau",
    "shoulders": "vai",
    "biceps": "tay trước",
    "triceps": "tay sau",
    "core": "core",
}


@dataclass(frozen=True)
class VolumeBand:
    recommended_min: int
    target_sets: int
    max_sets: int

    @property
    def min_sets(self) -> int:
        return self.recommended_min


def volume_family(muscle_slug: str | None, movement_pattern: str | None = None) -> str:
    slug = str(muscle_slug or "").strip().lower()
    if slug in CHEST_SLUGS:
        return "chest"
    if slug in BACK_SLUGS:
        return "back"
    if slug in QUAD_SLUGS:
        return "quads"
    if slug in HINGE_MUSCLE_SLUGS or slug in GLUTE_SLUGS:
        return "hinge"
    if slug in SHOULDER_SLUGS:
        return "shoulders"
    if slug in BICEPS_SLUGS:
        return "biceps"
    if slug in TRICEPS_SLUGS:
        return "triceps"
    if slug in CORE_SLUGS:
        return "core"
    fam = family_of(movement_pattern)
    if fam in {"push"}:
        return "chest"
    if fam in {"pull"}:
        return "back"
    if fam == "squat":
        return "quads"
    if fam == "hinge":
        return "hinge"
    if fam == "core":
        return "core"
    return "other"


def _scale(n: int, mult: float) -> int:
    return max(0, int(round(n * mult)))


def weekly_budget(
    effective_level: int,
    *,
    strength_tier: str = "ok",
    focus_slugs: frozenset[str] | None = None,
    conservative_volume: bool = False,
) -> dict[str, VolumeBand]:
    level = max(1, min(3, int(effective_level or 1)))
    mult = _TIER_MULT.get((strength_tier or "ok").lower(), 1.0)
    if conservative_volume:
        mult *= 0.85
    focus_slugs = focus_slugs or frozenset()
    out: dict[str, VolumeBand] = {}
    for fam, (mn, tg, mx) in _BUDGET[level].items():
        mn_s, tg_s, mx_s = _scale(mn, mult), _scale(tg, mult), _scale(mx, mult)
        focus_hit = any(volume_family(s) == fam for s in focus_slugs)
        if focus_hit:
            mx_s = max(mx_s, mx_s + 2)
            mn_s = max(mn_s, min(mx_s, mn_s + 1))
        if mx_s < mn_s:
            mx_s = mn_s
        out[fam] = VolumeBand(mn_s, min(mx_s, max(mn_s, tg_s)), mx_s)
    return out


def l1_session_set_cap(session_minutes: int) -> int:
    mins = max(30, min(75, int(session_minutes or 45)))
    return max(8, min(L1_SETS_PER_SESSION_HARD_CAP, int(round(L1_SETS_PER_SESSION_AT_45 * mins / 45))))


def _ex_sets(ex: Any) -> int:
    try:
        return max(0, int(getattr(ex, "sets", 0) or 0))
    except (TypeError, ValueError):
        return 0


def _is_main(ex: Any) -> bool:
    return (getattr(ex, "section", "main") or "main") == "main"


MIN_ISOLATION_SETS = 2
MIN_MAIN_EXERCISES = 3


def main_lift_floor(
    session_minutes: int,
    location: str | None,
    split_role: str | None,
) -> int:
    """Main-lift count from the gym/home minute spec (Cardio-Core = 2 core)."""
    role = normalize_split_role(split_role)
    if role == "core":
        return 2
    from app.services.schedule_spec_master import (
        gym_session_spec,
        home_session_spec,
        snap_session_minutes,
    )

    loc = (location or "gym").strip().lower()
    mins = snap_session_minutes(int(session_minutes or 45))
    if loc == "home":
        return max(2, int(home_session_spec(mins).get("resistanceCount") or 2))
    return max(3, int(gym_session_spec(mins).get("totalLifts") or 3))


def main_exercise_count(day: Any) -> int:
    return sum(1 for ex in (getattr(day, "exercises", None) or []) if _is_main(ex))


def count_weekly_sets(
    plan_days: list[Any],
    meta_by_id: dict[int, dict[str, Any]],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for day in plan_days:
        for ex in getattr(day, "exercises", None) or []:
            if not _is_main(ex):
                continue
            meta = meta_by_id.get(int(ex.exercise_id)) or {}
            fam = volume_family(meta.get("muscle_slug"), meta.get("movement_pattern"))
            if fam == "other":
                continue
            counts[fam] = counts.get(fam, 0) + _ex_sets(ex)
    return counts


_VOL_TO_COV = {
    "chest": "push",
    "shoulders": "push",
    "triceps": "push",
    "back": "pull",
    "biceps": "pull",
    "quads": "squat",
    "hinge": "hinge",
    "core": "core",
}


def _cov_family(vol_fam: str) -> str | None:
    return _VOL_TO_COV.get(vol_fam)


def _day_requires_vol(day: Any, vol_fam: str) -> bool:
    cov = _cov_family(vol_fam)
    if not cov:
        return False
    return cov in required_families(getattr(day, "split_role", None))


def is_pushup_name(name: str | None) -> bool:
    n = str(name or "").strip().lower()
    return any(
        k in n for k in ("chống đẩy", "chong day", "push-up", "push up", "pushup")
    )


def is_knee_pushup_name(name_vi: str | None, name_en: str | None = None) -> bool:
    blob = fold_lift_name(f"{name_vi or ''} {name_en or ''}")
    return any(k in blob for k in ("knee", "chong goi"))


def is_standard_pushup_name(name_vi: str | None, name_en: str | None = None) -> bool:
    if not (is_pushup_name(name_vi) or is_pushup_name(name_en)):
        return False
    if is_knee_pushup_name(name_vi, name_en):
        return False
    blob = fold_lift_name(f"{name_vi or ''} {name_en or ''}")
    if any(k in blob for k in ("wall", "tuong", "incline", "decline", "ghe", "elevat")):
        return False
    return True


def prefer_knee_pushups(
    *,
    location: str | None,
    no_equipment: bool,
    pushups_max: int | None,
) -> bool:
    loc = str(location or "").strip().lower()
    try:
        n = int(pushups_max) if pushups_max is not None else None
    except (TypeError, ValueError):
        n = None
    return loc == "home" and bool(no_equipment) and n is not None and n <= 5


def is_hip_abduction_name(name_vi: str | None, name_en: str | None = None) -> bool:
    blob = fold_lift_name(f"{name_vi or ''} {name_en or ''}")
    return any(k in blob for k in ("hip abduction", "abduct", "dang hong"))


def drop_standard_pushups_if_knee_available(items: list[Any], *, name_of) -> list[Any]:
    """If a knee push-up exists, hide regular push-ups from the pool."""
    if not any(is_knee_pushup_name(name_of(x)) for x in items):
        return items
    kept = [x for x in items if not is_standard_pushup_name(name_of(x))]
    return kept or items


def pushup_cap_for_minutes(session_minutes: int | None) -> int:
    return 2 if int(session_minutes or 0) >= 90 else 1


def _sig(meta: dict[str, Any]) -> tuple[str, str, str]:
    role = str(meta.get("movement_role") or "").strip().lower()
    if role != "compound":
        fam = volume_family(meta.get("muscle_slug"), meta.get("movement_pattern"))
        return ("iso", fam or "other", role)
    return (
        str(meta.get("movement_pattern") or "").strip().lower(),
        str(meta.get("muscle_slug") or "").strip().lower(),
        role,
    )


def _sig_cap(sig: tuple[str, str, str]) -> int:
    pat, _muscle, role = sig
    if pat == "v_push" and role == "compound":
        return 1
    if role == "compound":
        return 1
    return 1


def _patterns_from_exercises(
    exercises: list[Any], meta_by_id: dict[int, dict[str, Any]]
) -> set[str]:
    out: set[str] = set()
    for ex in exercises:
        if not _is_main(ex):
            continue
        try:
            eid = int(ex.exercise_id)
        except (TypeError, ValueError, AttributeError):
            continue
        pat = str((meta_by_id.get(eid) or {}).get("movement_pattern") or "").strip().lower()
        if pat:
            out.add(pat)
    return out


def _loses_required_coverage(
    day: Any,
    before: list[Any],
    after: list[Any],
    meta_by_id: dict[int, dict[str, Any]],
) -> bool:
    """True only if dropping would lose a required family/pattern the day already had."""
    req_f = required_families(getattr(day, "split_role", None))
    if req_f:
        before_f = families_from_exercises(before, meta_by_id)
        after_f = families_from_exercises(after, meta_by_id)
        if any(fam in before_f and fam not in after_f for fam in req_f):
            return True
    req_p = required_patterns(getattr(day, "split_role", None))
    if req_p:
        before_p = _patterns_from_exercises(before, meta_by_id)
        after_p = _patterns_from_exercises(after, meta_by_id)
        if any(pat in before_p and pat not in after_p for pat in req_p):
            return True
    return False


def _drop_duplicate_lifts(
    plan_days: list[Any],
    *,
    meta_by_id: dict[int, dict[str, Any]],
    session_minutes: int | None = None,
) -> None:
    pu_cap = pushup_cap_for_minutes(session_minutes)
    for day in plan_days:
        original = list(getattr(day, "exercises", None) or [])
        kept: list[Any] = []
        seen: dict[tuple[str, str, str], int] = {}
        seen_stems: set[str] = set()
        pushup_kept = 0
        for i, ex in enumerate(original):
            if not _is_main(ex):
                kept.append(ex)
                continue
            meta = meta_by_id.get(int(ex.exercise_id)) or {}
            sig = _sig(meta)
            name = str(meta.get("name_vi") or "")
            stem = lift_stem(name, meta.get("name_en"))
            drop = False
            if is_pushup_name(name) and pushup_kept >= pu_cap:
                drop = True
            elif seen.get(sig, 0) >= _sig_cap(sig):
                drop = True
            elif stem and stem in seen_stems and str(meta.get("movement_role") or "").lower() == "compound":
                drop = True
            if drop:
                trial = kept + original[i + 1 :]
                if not _loses_required_coverage(day, original, trial, meta_by_id):
                    continue
            if is_pushup_name(name):
                pushup_kept += 1
            seen[sig] = seen.get(sig, 0) + 1
            if stem:
                seen_stems.add(stem)
            kept.append(ex)
        day.exercises = kept


def _drop_denied_split_leaks(
    plan_days: list[Any],
    *,
    meta_by_id: dict[int, dict[str, Any]],
) -> None:
    """Remove laterals/presses that leaked onto leg days, glute isos onto upper, curls onto Push."""
    for day in plan_days:
        original = list(getattr(day, "exercises", None) or [])
        kept: list[Any] = []
        role = getattr(day, "split_role", None)
        role_n = normalize_split_role(role)
        for i, ex in enumerate(original):
            if not _is_main(ex):
                kept.append(ex)
                continue
            meta = meta_by_id.get(int(ex.exercise_id)) or {}
            denied = is_denied_for_split(
                role,
                pattern=meta.get("movement_pattern"),
                muscle_slug=meta.get("muscle_slug"),
            )
            if not denied and role_n in {"upper", "push", "pull"}:
                denied = is_hip_abduction_name(meta.get("name_vi"), meta.get("name_en"))
            if denied:
                trial = kept + original[i + 1 :]
                if not _loses_required_coverage(day, original, trial, meta_by_id):
                    continue
            kept.append(ex)
        day.exercises = kept


def _over_families(
    plan_days: list[Any],
    meta_by_id: dict[int, dict[str, Any]],
    budget: dict[str, VolumeBand],
) -> dict[str, int]:
    actual = count_weekly_sets(plan_days, meta_by_id)
    return {
        fam: n
        for fam, n in actual.items()
        if fam in budget and n > budget[fam].max_sets
    }


def _ex_meta(ex: Any, meta_by_id: dict[int, dict[str, Any]]) -> dict[str, Any]:
    try:
        eid = int(ex.exercise_id)
    except (TypeError, ValueError, AttributeError):
        return {}
    return meta_by_id.get(eid) or {}


def _is_isolation_meta(meta: dict[str, Any]) -> bool:
    return str(meta.get("movement_role") or "").strip().lower() in _ISOLATION_ROLES


def _is_set_trimmable(meta: dict[str, Any]) -> bool:
    """Home resistance accessories count toward L1 set cap the same as isolation."""
    return str(meta.get("movement_role") or "").strip().lower() in _TRIM_SET_ROLES


def _protect_split_min(
    day: Any,
    ex: Any,
    meta_by_id: dict[int, dict[str, Any]],
) -> bool:
    """True if this is the last biceps (pull), squat (legs), or press (upper) on the day."""
    role = normalize_split_role(getattr(day, "split_role", None))
    meta = _ex_meta(ex, meta_by_id)
    fam = volume_family(meta.get("muscle_slug"), meta.get("movement_pattern"))
    pat = str(meta.get("movement_pattern") or "").strip().lower()
    mains = [x for x in (getattr(day, "exercises", None) or []) if _is_main(x)]
    if role == "pull" and fam == "biceps":
        n = sum(
            1
            for x in mains
            if volume_family(
                _ex_meta(x, meta_by_id).get("muscle_slug"),
                _ex_meta(x, meta_by_id).get("movement_pattern"),
            )
            == "biceps"
        )
        return n <= 1
    if role in {"legs", "lower"} and pat == "squat":
        n = sum(
            1
            for x in mains
            if str(_ex_meta(x, meta_by_id).get("movement_pattern") or "").strip().lower()
            == "squat"
        )
        return n <= 1
    if role == "upper" and is_real_press(meta):
        n = sum(1 for x in mains if is_real_press(_ex_meta(x, meta_by_id)))
        return n <= 1
    return False


def _can_drop_exercise(
    day: Any,
    ex: Any,
    meta_by_id: dict[int, dict[str, Any]],
    *,
    respect_floor: bool,
    floor: int | None = None,
    session_minutes: int = 45,
    location: str | None = "gym",
) -> bool:
    original = list(getattr(day, "exercises", None) or [])
    if ex not in original:
        return False
    if _protect_split_min(day, ex, meta_by_id):
        return False
    trial = [x for x in original if x is not ex]
    if _loses_required_coverage(day, original, trial, meta_by_id):
        return False
    if not respect_floor:
        return True
    if floor is None:
        floor = main_lift_floor(
            session_minutes, location, getattr(day, "split_role", None)
        )
    trial_mains = sum(1 for x in trial if _is_main(x))
    orig_mains = sum(1 for x in original if _is_main(x))
    if trial_mains < floor and orig_mains >= floor:
        return False
    if trial_mains < orig_mains and trial_mains < floor:
        return False
    return True


def _iter_round_robin_isolations(
    plan_days: list[Any],
    meta_by_id: dict[int, dict[str, Any]],
    *,
    fams: set[str] | None = None,
    offsplit_only: bool = False,
    surplus_days_only: bool = False,
    floor: int | None = None,
    session_minutes: int = 45,
    location: str | None = "gym",
):
    """Yield (day_index, ex, family) — richest days first, later isolations first, interleaved."""
    indexed = list(enumerate(plan_days))
    indexed.sort(key=lambda t: (-main_exercise_count(t[1]), t[0]))
    queues: list[list[tuple[int, Any, str]]] = []
    for di, day in indexed:
        day_floor = (
            int(floor)
            if floor is not None
            else main_lift_floor(
                session_minutes, location, getattr(day, "split_role", None)
            )
        )
        if surplus_days_only and main_exercise_count(day) <= day_floor:
            queues.append([])
            continue
        slots: list[tuple[int, Any, str]] = []
        for ex in getattr(day, "exercises", None) or []:
            if not _is_main(ex):
                continue
            meta = _ex_meta(ex, meta_by_id)
            if not _is_isolation_meta(meta):
                continue
            fam = volume_family(meta.get("muscle_slug"), meta.get("movement_pattern"))
            if fams is not None and fam not in fams:
                continue
            if offsplit_only and _day_requires_vol(day, fam):
                continue
            slots.append((di, ex, fam))
        slots.reverse()
        queues.append(slots)
    while any(queues):
        for q in queues:
            if q:
                yield q.pop(0)


def _reduce_isolation_sets(
    plan_days: list[Any],
    *,
    meta_by_id: dict[int, dict[str, Any]],
    budget: dict[str, VolumeBand],
    offsplit_only: bool = False,
    floor_sets: int = MIN_ISOLATION_SETS,
) -> None:
    """Lower isolation sets (floor 2) on over-budget families, spread across days."""
    for _ in range(200):
        remaining = _over_families(plan_days, meta_by_id, budget)
        if not remaining:
            return
        reduced = False
        for di, ex, fam in _iter_round_robin_isolations(
            plan_days,
            meta_by_id,
            fams=set(remaining),
            offsplit_only=offsplit_only,
        ):
            remaining = _over_families(plan_days, meta_by_id, budget)
            if not remaining:
                return
            if fam not in remaining:
                continue
            if ex not in (getattr(plan_days[di], "exercises", None) or []):
                continue
            sets = _ex_sets(ex)
            if sets > floor_sets:
                ex.sets = sets - 1
                reduced = True
                break
        if not reduced:
            return


def _drop_isolations_loop(
    plan_days: list[Any],
    *,
    meta_by_id: dict[int, dict[str, Any]],
    budget: dict[str, VolumeBand],
    offsplit_only: bool = False,
    surplus_days_only: bool = False,
    respect_floor: bool = True,
    session_minutes: int = 45,
    location: str | None = "gym",
    floor: int | None = None,
) -> None:
    for _ in range(100):
        remaining = _over_families(plan_days, meta_by_id, budget)
        if not remaining:
            return
        dropped = False
        for di, ex, fam in _iter_round_robin_isolations(
            plan_days,
            meta_by_id,
            fams=set(remaining),
            offsplit_only=offsplit_only,
            surplus_days_only=surplus_days_only,
            floor=floor,
            session_minutes=session_minutes,
            location=location,
        ):
            remaining = _over_families(plan_days, meta_by_id, budget)
            if not remaining:
                return
            if fam not in remaining:
                continue
            day = plan_days[di]
            if not _can_drop_exercise(
                day,
                ex,
                meta_by_id,
                respect_floor=respect_floor,
                floor=floor,
                session_minutes=session_minutes,
                location=location,
            ):
                continue
            day.exercises = [x for x in (day.exercises or []) if x is not ex]
            dropped = True
            break
        if not dropped:
            return


def _drop_isolation_sets(
    plan_days: list[Any],
    *,
    meta_by_id: dict[int, dict[str, Any]],
    over: dict[str, int],
    budget: dict[str, VolumeBand],
    focus_slugs: frozenset[str],
    drop_exercises: bool = True,
    session_minutes: int = 45,
    location: str | None = "gym",
) -> None:
    """Reduce isolation sets first, then drop extras without gutting the last day.

    Never drop the last exercise that covers a required movement family.
    Never drop below the recipe lift count on-split.
    """
    del over, focus_slugs  # remaining is recomputed live
    _reduce_isolation_sets(plan_days, meta_by_id=meta_by_id, budget=budget)
    if not drop_exercises:
        return
    _drop_isolations_loop(
        plan_days,
        meta_by_id=meta_by_id,
        budget=budget,
        surplus_days_only=True,
        respect_floor=True,
        session_minutes=session_minutes,
        location=location,
    )
    _drop_isolations_loop(
        plan_days,
        meta_by_id=meta_by_id,
        budget=budget,
        surplus_days_only=False,
        respect_floor=True,
        session_minutes=session_minutes,
        location=location,
    )
    _drop_isolations_loop(
        plan_days,
        meta_by_id=meta_by_id,
        budget=budget,
        surplus_days_only=False,
        respect_floor=True,
        session_minutes=session_minutes,
        location=location,
        floor=MIN_MAIN_EXERCISES,
    )
    _drop_isolations_loop(
        plan_days,
        meta_by_id=meta_by_id,
        budget=budget,
        surplus_days_only=False,
        respect_floor=False,
        session_minutes=session_minutes,
        location=location,
    )


def _drop_offsplit_over(
    plan_days: list[Any],
    *,
    meta_by_id: dict[int, dict[str, Any]],
    budget: dict[str, VolumeBand],
    drop_exercises: bool = True,
    session_minutes: int = 45,
    location: str | None = "gym",
) -> None:
    """Trim over-budget muscle work from days that do not require that family."""
    if not _over_families(plan_days, meta_by_id, budget):
        return
    _reduce_isolation_sets(
        plan_days, meta_by_id=meta_by_id, budget=budget, offsplit_only=True
    )
    if not drop_exercises:
        return
    _drop_isolations_loop(
        plan_days,
        meta_by_id=meta_by_id,
        budget=budget,
        offsplit_only=True,
        surplus_days_only=True,
        respect_floor=True,
        session_minutes=session_minutes,
        location=location,
    )
    _drop_isolations_loop(
        plan_days,
        meta_by_id=meta_by_id,
        budget=budget,
        offsplit_only=True,
        surplus_days_only=False,
        respect_floor=False,
        session_minutes=session_minutes,
        location=location,
    )


def _cap_session_sets(
    plan_days: list[Any],
    *,
    meta_by_id: dict[int, dict[str, Any]],
    cap: int,
    drop_exercises: bool = True,
    session_minutes: int = 45,
    location: str | None = "gym",
) -> None:
    for day in plan_days:
        def _day_total() -> int:
            return sum(
                _ex_sets(ex)
                for ex in (getattr(day, "exercises", None) or [])
                if _is_main(ex)
            )

        if _day_total() <= cap:
            continue
        isolations = [
            ex
            for ex in (getattr(day, "exercises", None) or [])
            if _is_main(ex) and _is_isolation_meta(_ex_meta(ex, meta_by_id))
        ]
        trimmable = [
            ex
            for ex in (getattr(day, "exercises", None) or [])
            if _is_main(ex) and _is_set_trimmable(_ex_meta(ex, meta_by_id))
        ]
        for ex in reversed(trimmable):
            if _day_total() <= cap:
                break
            while _ex_sets(ex) > MIN_ISOLATION_SETS and _day_total() > cap:
                ex.sets = _ex_sets(ex) - 1
        if _day_total() <= cap or not drop_exercises:
            continue
        for ex in reversed(list(isolations)):
            if _day_total() <= cap:
                break
            if ex not in (getattr(day, "exercises", None) or []):
                continue
            if not _can_drop_exercise(
                day,
                ex,
                meta_by_id,
                respect_floor=True,
                session_minutes=session_minutes,
                location=location,
            ):
                continue
            day.exercises = [x for x in (day.exercises or []) if x is not ex]


def recap_l1_session_sets(
    plan_days: list[Any],
    *,
    meta_by_id: dict[int, dict[str, Any]],
    session_minutes: int,
) -> None:
    """Re-apply L1 set cap after top_up (isolation sets only, keep exercises)."""
    _cap_session_sets(
        plan_days,
        meta_by_id=meta_by_id,
        cap=l1_session_set_cap(session_minutes),
        drop_exercises=False,
    )


def _volume_notes(
    actual: dict[str, int],
    budget: dict[str, VolumeBand],
    focus_slugs: frozenset[str],
    *,
    still_over: bool = False,
) -> list[str]:
    notes: list[str] = []
    for fam, band in budget.items():
        n = actual.get(fam, 0)
        if n < band.recommended_min and any(volume_family(s) == fam for s in focus_slugs):
            label = _FAM_LABEL_VI.get(fam, fam)
            notes.append(
                f"Nhóm ưu tiên ({label}) mới ~{n} set/tuần (khuyến nghị ≥{band.recommended_min}); "
                "tăng thời lượng buổi hoặc thêm 1 bài isolation nếu còn sức."
            )
        if still_over and n > band.max_sets:
            label = _FAM_LABEL_VI.get(fam, fam)
            notes.append(
                f"{label} ~{n} set/tuần (max {band.max_sets}) — đã cắt bài trùng/isolation; "
                "phần còn lại giữ để đủ pattern bắt buộc."
            )
    return notes


def apply_weekly_dose(
    plan_days: list[Any],
    *,
    meta_by_id: dict[int, dict[str, Any]],
    effective_level: int,
    strength_tier: str = "ok",
    focus_slugs: frozenset[str] | None = None,
    session_minutes: int = 45,
    conservative_volume: bool = False,
    drop_exercises: bool = True,
    location: str | None = "gym",
) -> tuple[list[Any], str | None]:
    """Clamp isolation by weekly set budget; L1 also caps sets/session. Returns notes."""
    if not plan_days:
        return plan_days, None
    focus_slugs = focus_slugs or frozenset()
    budget = weekly_budget(
        effective_level,
        strength_tier=strength_tier,
        focus_slugs=focus_slugs,
        conservative_volume=conservative_volume,
    )
    if effective_level <= 1:
        _cap_session_sets(
            plan_days,
            meta_by_id=meta_by_id,
            cap=l1_session_set_cap(session_minutes),
            drop_exercises=drop_exercises,
            session_minutes=session_minutes,
            location=location,
        )

    if drop_exercises:
        _drop_duplicate_lifts(
            plan_days, meta_by_id=meta_by_id, session_minutes=session_minutes
        )
        _drop_denied_split_leaks(plan_days, meta_by_id=meta_by_id)

    actual = count_weekly_sets(plan_days, meta_by_id)
    over = {fam: n for fam, n in actual.items() if fam in budget and n > budget[fam].max_sets}
    if over:
        _drop_isolation_sets(
            plan_days,
            meta_by_id=meta_by_id,
            over=actual,
            budget=budget,
            focus_slugs=focus_slugs,
            drop_exercises=drop_exercises,
            session_minutes=session_minutes,
            location=location,
        )
        _drop_offsplit_over(
            plan_days,
            meta_by_id=meta_by_id,
            budget=budget,
            drop_exercises=drop_exercises,
            session_minutes=session_minutes,
            location=location,
        )
        actual = count_weekly_sets(plan_days, meta_by_id)

    if not coverage_ok(plan_days, meta_by_id):
        # Guard failed unexpectedly — do not invent exercises; just note.
        pass

    still_over = any(
        actual.get(fam, 0) > band.max_sets for fam, band in budget.items()
    )
    notes = _volume_notes(actual, budget, focus_slugs, still_over=still_over)
    return plan_days, " ".join(notes) if notes else None


def apply_weekly_dose_expanded(
    plan_days: list[Any],
    *,
    sessions_per_week: int,
    meta_by_id: dict[int, dict[str, Any]],
    effective_level: int,
    strength_tier: str = "ok",
    focus_slugs: frozenset[str] | None = None,
    session_minutes: int = 45,
    conservative_volume: bool = False,
    location: str | None = "gym",
) -> tuple[list[Any], str | None]:
    """Re-clamp each expanded week after periodization; sets only, no extra drops."""
    if not plan_days:
        return plan_days, None
    spw = max(1, int(sessions_per_week or len(plan_days)))
    notes: list[str] = []
    for start in range(0, len(plan_days), spw):
        slice_days = plan_days[start : start + spw]
        _, note = apply_weekly_dose(
            slice_days,
            meta_by_id=meta_by_id,
            effective_level=effective_level,
            strength_tier=strength_tier,
            focus_slugs=focus_slugs,
            session_minutes=session_minutes,
            conservative_volume=conservative_volume,
            drop_exercises=False,
            location=location,
        )
        if note:
            notes.append(note)
    return plan_days, " ".join(notes) if notes else None
