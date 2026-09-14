"""Safe bounds for OpenAI-proposed exercise doses.

Rules define the allowable prescription; the model may choose a value inside it.
Invalid or out-of-range model output falls back to the deterministic prescription.
"""

from __future__ import annotations

import math
import re
from typing import Any

from app.services.workout_generation.effort_mode import exercise_effort_mode

_LOADED_KEYS = (
    "barbell",
    "dumbbell",
    "machine",
    "cable",
    "kettlebell",
    "tạ ",
    "máy ",
    "cáp ",
)
_PUSHUP_KEYS = (
    "push-up",
    "push up",
    "pushup",
    "push ups",
    "diamond",
    "kim cương",
    "kim cuong",
    "chống đẩy",
    "chong day",
)
_PULLUP_KEYS = ("pull-up", "pullup", "chin-up", "chinup", "hít xà", "hit xa")
_SQUAT_KEYS = (
    "bodyweight squat",
    "air squat",
    "box squat",
    "xuống hộp",
    "xuong hop",
    "squat không tạ",
    "squat khong ta",
    "ngồi xổm",
    "ngoi xom",
    "lunge",
    "lunges",
    "split squat",
    "bulgarian",
    "glute bridge",
    "cầu mông",
    "cau mong",
    "frog pump",
    "bơm mông",
    "bom mong",
    "hip thrust",
    "cossack",
)
_HINGE_KEYS = (
    "rdl",
    "deadlift",
    "good morning",
    "hip hinge",
)
_BACK_BW_KEYS = (
    "superman",
    "bird-dog",
    "bird dog",
    "y raise",
    "t raise",
    "w raise",
    "y-t-w",
    "ytw",
    "reverse snow",
    "scapular",
)
# Home pulls with table / backpack / towel — scale from pullups_max like bar work.
_HOME_IMPROVISED_PULL_KEYS = (
    "towel",
    "table",
    "backpack",
    "self-resisted",
    "improvised",
    "khăn",
    "khan",
    "bàn",
    "ban ",
    "ba lô",
    "ba lo",
    "balo",
    "tự cản",
    "tu can",
    "dưới bàn",
    "duoi ban",
    "kéo người dưới bàn",
    "keo nguoi duoi ban",
    "chèo ba lô",
    "cheo ba lo",
    "table inverted",
)
_CORE_REP_KEYS = (
    "crunch",
    "sit-up",
    "sit up",
    "leg raise",
    "dead bug",
    "deadbug",
    "hollow rock",
    "v-up",
    "v up",
)
_PUSH_MUSCLES = frozenset(
    {
        "chest",
        "co-nguc",
        "triceps",
        "co-tay-sau",
        "shoulders",
        "shoulders-deltoids",
        "co-vai",
    }
)
_PULL_MUSCLES = frozenset(
    {
        "back",
        "co-lung",
        "biceps",
        "co-tay-truoc",
    }
)
_LEG_MUSCLES = frozenset(
    {
        "quads",
        "hamstrings",
        "glutes",
        "calves",
        "co-dui-truoc",
        "co-dui-sau",
        "co-mong",
        "co-bap-chan",
        "upper-legs",
        "lower-legs",
    }
)
_CORE_MUSCLES = frozenset({"core", "co-bung", "waist", "abs"})
_PUSH_PATTERNS = frozenset({"h_push", "v_push"})
_PULL_PATTERNS = frozenset({"h_pull", "v_pull"})
_LEG_PATTERNS = frozenset({"squat", "hinge", "lunge"})

# Free-weight / machine at home — Method B: experience presets, not pushup scaling.
_FREE_WEIGHT_PRESETS: dict[int, dict[str, tuple[int, int]]] = {
    1: {"compound": (8, 12), "isolation": (10, 15)},
    2: {"compound": (6, 10), "isolation": (8, 12)},
    3: {"compound": (5, 8), "isolation": (8, 12)},
}


def _as_nonnegative_int(value: Any) -> int | None:
    try:
        return max(0, int(value)) if value is not None else None
    except (TypeError, ValueError):
        return None


def _attr(item: Any, key: str) -> Any:
    if isinstance(item, dict):
        return item.get(key)
    return getattr(item, key, None)


def _names(item: Any) -> str:
    return f"{_attr(item, 'name_vi') or ''} {_attr(item, 'name_en') or ''}".lower()


def _muscle_slug(item: Any) -> str:
    # Prompt dicts use "muscle"; ShortlistItem / assemble meta use "muscle_slug".
    raw = _attr(item, "muscle_slug")
    if raw is None or raw == "":
        raw = _attr(item, "muscle")
    return str(raw or "").strip().lower()


def _movement_pattern(item: Any) -> str:
    return str(_attr(item, "movement_pattern") or "").strip().lower()


def _first_available_test(base: dict[str, Any]) -> int | None:
    for key in ("pushups_max", "squats_max", "pullups_max"):
        value = _as_nonnegative_int(base.get(key))
        if value is not None:
            return value
    return None


def _take_test(base: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = _as_nonnegative_int(base.get(key))
        if value is not None:
            return value
    return None


def _is_band_name(names: str) -> bool:
    return any(
        k in names
        for k in (
            "band",
            "resistance band",
            "dây kháng",
            "day khang",
            "dây thun",
            "day thun",
            "tube",
            "loop band",
        )
    )


def _is_free_weight_loaded(item: Any, *, no_equipment: bool) -> bool:
    """Dumbbell/barbell/machine — not bands (bands scale from fitness tests)."""
    if no_equipment:
        return False
    names = _names(item)
    if _is_band_name(names):
        return False
    return any(key in names for key in _LOADED_KEYS)


def _pullup_proxy(base: dict[str, Any]) -> int | None:
    """When pullups_max missing, rough proxy from pushups."""
    hit = _take_test(base, "pullups_max")
    if hit is not None:
        return hit
    push = _take_test(base, "pushups_max")
    if push is None:
        return None
    return max(0, int(math.floor(push * 0.15)))


def _transfer_factor(item: Any) -> float:
    """Difficulty vs the matched fitness-test max (HLV Method B)."""
    names = _names(item)
    pattern = _movement_pattern(item)
    role = str(_attr(item, "movement_role") or "").strip().lower()
    band = _is_band_name(names)
    ring = any(k in names for k in ("ring", "vòng treo", "vong treo", "vòng ", "vong "))

    # Push family hardness
    if any(k in names for k in ("pike", "handstand", "hspu", "hand stand")):
        return 0.25
    if any(k in names for k in ("dip",)):
        return 0.35
    if any(k in names for k in _PUSHUP_KEYS):
        if ring:
            return 0.75
        return 1.0
    if band and (pattern in _PUSH_PATTERNS or any(k in names for k in ("fly", "press", "ép ngực", "ep nguc", "chest"))):
        return 0.55
    if ring and any(k in names for k in ("fly", "ép ngực", "ep nguc", "chest")):
        return 0.55

    # Pull family
    if any(k in names for k in _PULLUP_KEYS) or (
        ring and any(k in names for k in ("pull", "hít xà", "hit xa", "chin"))
    ):
        return 1.0
    if (
        any(k in names for k in ("row", "chèo", "cheo", "inverted"))
        or any(k in names for k in _HOME_IMPROVISED_PULL_KEYS)
        or (band and pattern in _PULL_PATTERNS)
    ):
        return 2.0
    if any(
        k in names
        for k in (
            "face pull",
            "rear delt",
            "bay vai sau",
            "curl",
            "cuốn",
            "cuon",
        )
    ) or (band and role == "isolation" and pattern in _PULL_PATTERNS | frozenset({"other"})):
        return 1.5

    # Legs
    if any(k in names for k in ("pistol", "shrimp", "single-leg squat", "squat 1 chân")):
        return 0.4
    if any(k in names for k in _SQUAT_KEYS) or any(k in names for k in ("lunge",)):
        return 1.0
    if any(k in names for k in _HINGE_KEYS) or any(
        k in names for k in ("bridge", "cầu mông", "hip thrust", "frog")
    ):
        return 0.9

    if any(k in names for k in _CORE_REP_KEYS) or _muscle_slug(item) in _CORE_MUSCLES:
        return 0.8

    # Generic iso / remaining BW-ish
    if role == "isolation":
        if pattern in _PUSH_PATTERNS or _muscle_slug(item) in _PUSH_MUSCLES:
            return 0.5
        if pattern in _PULL_PATTERNS or _muscle_slug(item) in _PULL_MUSCLES:
            return 1.5
    if pattern in _PUSH_PATTERNS:
        return 0.75 if ring else 0.85
    if pattern in _PULL_PATTERNS:
        return 2.0 if ring or band else 1.2
    if pattern in _LEG_PATTERNS:
        return 1.0
    return 1.0


def _apply_transfer(raw: int | None, item: Any) -> int | None:
    if raw is None:
        return None
    if raw <= 0:
        return 0
    factor = _transfer_factor(item)
    return max(1, int(math.floor(raw * factor)))


def _raw_test_for_item(
    item: Any,
    base: dict[str, Any],
    *,
    no_equipment: bool,
    home_session: bool,
) -> int | None:
    """Pick the fitness-test integer before difficulty transfer."""
    names = _names(item)

    # Free weights: never scale from BW tests (Method B).
    if _is_free_weight_loaded(item, no_equipment=no_equipment):
        return None

    if any(key in names for key in _PUSHUP_KEYS):
        hit = _take_test(base, "pushups_max")
        if hit is not None:
            return hit
    if any(key in names for key in _PULLUP_KEYS):
        hit = _pullup_proxy(base)
        if hit is not None:
            return hit
    if any(key in names for key in _BACK_BW_KEYS):
        hit = _pullup_proxy(base)
        if hit is not None:
            return hit
    if any(key in names for key in _HOME_IMPROVISED_PULL_KEYS):
        hit = _pullup_proxy(base)
        if hit is not None:
            return hit
    if any(key in names for key in _SQUAT_KEYS) or any(key in names for key in _HINGE_KEYS):
        hit = _take_test(base, "squats_max", "pushups_max")
        if hit is not None:
            return hit
    if any(key in names for key in _CORE_REP_KEYS):
        hit = _take_test(base, "pushups_max", "squats_max")
        if hit is not None:
            return hit

    # Non-home with gear (gym path): stop after name matches — keep old behavior.
    if not home_session and not no_equipment:
        return None

    slug = _muscle_slug(item)
    pattern = _movement_pattern(item)
    band = _is_band_name(names)

    if slug in _PUSH_MUSCLES or pattern in _PUSH_PATTERNS:
        hit = _take_test(base, "pushups_max")
        if hit is not None:
            return hit
    if slug in _PULL_MUSCLES or pattern in _PULL_PATTERNS:
        hit = _pullup_proxy(base)
        if hit is not None:
            return hit
    if slug in _LEG_MUSCLES or pattern in _LEG_PATTERNS:
        hit = _take_test(base, "squats_max", "pushups_max")
        if hit is not None:
            return hit
    if slug in _CORE_MUSCLES or pattern == "core":
        hit = _take_test(base, "pushups_max", "squats_max")
        if hit is not None:
            return hit
    if band:
        hit = _take_test(base, "pushups_max", "squats_max")
        if hit is not None:
            return hit
        return _pullup_proxy(base)

    if home_session or no_equipment:
        return _first_available_test(base)
    return None


def bodyweight_test_max(
    item: Any,
    baseline: dict[str, Any] | None,
    *,
    no_equipment: bool = False,
    home_session: bool = False,
) -> int | None:
    """Return equivalent fitness-test max after difficulty transfer, else None."""
    base = dict(baseline or {})
    raw = _raw_test_for_item(
        item, base, no_equipment=no_equipment, home_session=home_session
    )
    return _apply_transfer(raw, item)


def _pct_band_for_role(
    role: str | None,
    *,
    no_equipment: bool = False,
    experience_level: int | None = None,
) -> tuple[float, float]:
    """Working % of equivalent test max. Prefer experience bands when provided."""
    is_compound = str(role or "").strip().lower() in {"compound", "resistance"}
    if experience_level is not None:
        level = max(1, min(3, int(experience_level)))
        if is_compound:
            return {1: (0.60, 0.70), 2: (0.70, 0.80), 3: (0.75, 0.85)}[level]
        return {1: (0.70, 0.80), 2: (0.80, 0.90), 3: (0.80, 0.90)}[level]
    if is_compound:
        return 0.7, 0.8
    if no_equipment:
        return 0.8, 0.9
    return 0.6, 0.7


def bodyweight_working_reps(
    test_max: int,
    *,
    role: str | None = None,
    no_equipment: bool = False,
    experience_level: int | None = None,
) -> tuple[int, int]:
    """Working-set reps from a fitness-test max (no hard cap)."""
    if test_max <= 0:
        return 1, 3
    pct_lo, pct_hi = _pct_band_for_role(
        role, no_equipment=no_equipment, experience_level=experience_level
    )
    lo = max(1, int(math.floor(test_max * pct_lo)))
    hi = max(lo, int(math.floor(test_max * pct_hi)))
    hi = min(hi, test_max)
    lo = min(lo, hi)
    return lo, hi


def free_weight_preset_reps(
    *,
    experience_level: int,
    role: str | None = None,
) -> tuple[int, int]:
    """Method B: dumbbell/kettlebell reps by experience — not from pushups."""
    level = max(1, min(3, int(experience_level or 2)))
    bucket = "compound" if str(role or "").lower() in {"compound", "resistance"} else "isolation"
    return _FREE_WEIGHT_PRESETS[level][bucket]


def primer_reps_from_baseline(
    item: Any,
    fitness_baseline: dict[str, Any] | None,
    *,
    role: str | None = None,
    no_equipment: bool = False,
    home_session: bool = False,
    experience_level: int | None = None,
) -> int | None:
    """Warmup primer reps (2 sets): 40% of test max, capped by working lo; None if no test."""
    test_max = bodyweight_test_max(
        item,
        fitness_baseline,
        no_equipment=no_equipment,
        home_session=home_session,
    )
    if test_max is None:
        return None
    if test_max <= 0:
        return 1
    item_role = role
    if item_role is None:
        item_role = _attr(item, "movement_role")
    working_lo, _ = bodyweight_working_reps(
        test_max,
        role=item_role,
        no_equipment=no_equipment,
        experience_level=experience_level,
    )
    primer = max(1, int(math.floor(test_max * 0.4)))
    return min(primer, working_lo)


def half_working_reps_label(reps: str | int | None) -> str | None:
    """~50% of a working reps prescription for home warmup primers."""
    if reps is None:
        return None
    if isinstance(reps, int):
        return str(max(1, int(round(reps * 0.5))))
    text = str(reps).strip()
    if not text:
        return None
    # Timed hold: "30 giây" / "20–30 giây"
    sec_range = re.search(
        r"(\d+)\s*[–\-]\s*(\d+)\s*(?:giây|giay|sec|secs|s)\b",
        text,
        flags=re.IGNORECASE,
    )
    if sec_range:
        lo = int(sec_range.group(1))
        hi = int(sec_range.group(2))
        mid = (lo + hi) / 2.0
        half = max(15, min(30, int(round(mid * 0.5))))
        return f"{half} giây"
    sec = re.search(r"(\d+)\s*(?:giây|giay|sec|secs|s)\b", text, flags=re.IGNORECASE)
    if sec:
        half = max(15, min(30, int(round(int(sec.group(1)) * 0.5))))
        return f"{half} giây"
    # Rep range: "8–12" / "8-12"
    rep_range = re.search(r"(\d+)\s*[–\-]\s*(\d+)", text)
    if rep_range:
        lo = int(rep_range.group(1))
        hi = int(rep_range.group(2))
        mid = (lo + hi) / 2.0
        return str(max(1, int(round(mid * 0.5))))
    # Single int-like
    single = re.fullmatch(r"(\d+)", text)
    if single:
        return str(max(1, int(round(int(single.group(1)) * 0.5))))
    return None


def dose_bounds_for_item(
    item: Any,
    *,
    experience_level: int,
    fitness_baseline: dict[str, Any] | None = None,
    plan_section: str | None = None,
    no_equipment: bool = False,
    home_session: bool = False,
) -> dict[str, Any]:
    """Build compact bounds suitable for both the prompt and server validation."""
    baseline = dict(fitness_baseline or {})
    role = _attr(item, "movement_role")
    mode = exercise_effort_mode(item, movement_role=role, plan_section=plan_section)
    level = max(1, min(3, int(experience_level or 2)))

    if str(plan_section or "").strip().lower() in {"warmup", "cooldown"}:
        return {
            "work_mode": "hold",
            "sets_min": 2,
            "sets_max": 3,
            "seconds_min": 20,
            "seconds_max": 45,
        }
    if mode == "continuous":
        return {
            "work_mode": "continuous",
            "sets_min": 1,
            "sets_max": 1,
            "minutes_min": 5,
            "minutes_max": 30,
        }
    if mode == "hold":
        plank_max = _as_nonnegative_int(baseline.get("plank_seconds"))
        if plank_max:
            lo = max(15, min(60, int(math.floor(plank_max * 0.5 / 5) * 5)))
            hi = max(lo, min(60, int(math.floor(plank_max * 0.7 / 5) * 5)))
        else:
            default = {1: 20, 2: 30, 3: 40}[level]
            lo, hi = max(15, default - 5), min(60, default + 5)
        return {
            "work_mode": "hold",
            "sets_min": 2,
            "sets_max": 3,
            "seconds_min": lo,
            "seconds_max": hi,
        }

    # Method B: free weights at home → experience presets (not pushup scaling).
    if home_session and _is_free_weight_loaded(item, no_equipment=no_equipment):
        lo, hi = free_weight_preset_reps(experience_level=level, role=role)
        return {
            "work_mode": "reps",
            "sets_min": 2,
            "sets_max": 4,
            "reps_min": lo,
            "reps_max": hi,
        }

    test_max = bodyweight_test_max(
        item,
        baseline,
        no_equipment=no_equipment,
        home_session=home_session,
    )
    if test_max is not None:
        lo, hi = bodyweight_working_reps(
            test_max,
            role=role,
            no_equipment=no_equipment,
            experience_level=level if (home_session or no_equipment) else None,
        )
    elif str(role or "").lower() in {"compound", "resistance"}:
        lo, hi = (5, 12) if not home_session else free_weight_preset_reps(
            experience_level=level, role=role
        )
    else:
        lo, hi = (8, 20) if not home_session else free_weight_preset_reps(
            experience_level=level, role="isolation"
        )
    return {
        "work_mode": "reps",
        "sets_min": 2,
        "sets_max": 4,
        "reps_min": lo,
        "reps_max": hi,
    }


def default_reps_label(bounds: dict[str, Any]) -> str:
    """Deterministic reps/seconds/minutes string from bounds (no OpenAI)."""
    mode = str(bounds.get("work_mode") or "reps")
    if mode == "hold":
        lo, hi = int(bounds["seconds_min"]), int(bounds["seconds_max"])
        mid = int(round((lo + hi) / 10) * 5)
        mid = max(lo, min(hi, mid))
        return f"{mid} giây"
    if mode == "continuous":
        lo, hi = int(bounds["minutes_min"]), int(bounds["minutes_max"])
        mid = max(lo, min(hi, (lo + hi) // 2))
        return f"{mid} phút"
    lo, hi = int(bounds["reps_min"]), int(bounds["reps_max"])
    return f"{lo}-{hi}" if lo != hi else str(lo)


_UNILATERAL_KEYS = (
    "một chân",
    "mot chan",
    "single leg",
    "single-leg",
    "unilateral",
    "bulgarian",
    "split squat",
    "lunge",
    "lunges",
)
UNILATERAL_NOTE_VI = "Làm {target} cái mỗi chân, xong đổi chân còn lại."


def is_unilateral_name(
    item: Any = None,
    *,
    name_vi: str | None = None,
    name_en: str | None = None,
) -> bool:
    if item is not None and name_vi is None and name_en is None:
        blob = _names(item)
    else:
        blob = f"{name_vi or ''} {name_en or ''}".strip().lower()
        if item is not None and not blob:
            blob = _names(item)
    return any(key in blob for key in _UNILATERAL_KEYS)


def _halve_reps_range(lo: int, hi: int) -> tuple[int, int]:
    lo2 = max(1, int(lo) // 2)
    hi2 = max(lo2, int(hi) // 2)
    return lo2, hi2


def _format_reps_range(lo: int, hi: int) -> str:
    return f"{lo}-{hi}" if lo != hi else str(lo)


def _target_reps_display(reps: str) -> str:
    values = [int(x) for x in re.findall(r"\d+", str(reps or ""))]
    if not values:
        return "số cái trên lịch"
    lo, hi = values[0], values[-1]
    return f"{lo}–{hi}" if lo != hi else str(lo)


def _meta_to_item(meta: Any, *, movement_role: str | None = None) -> dict[str, Any]:
    if meta is None:
        return {"movement_role": movement_role}
    if isinstance(meta, dict):
        item = dict(meta)
        if movement_role and not item.get("movement_role"):
            item["movement_role"] = movement_role
        if item.get("muscle") and not item.get("muscle_slug"):
            item["muscle_slug"] = item.get("muscle")
        return item
    return {
        "name_vi": getattr(meta, "name_vi", None),
        "name_en": getattr(meta, "name_en", None),
        "movement_role": getattr(meta, "movement_role", None) or movement_role,
        "movement_pattern": getattr(meta, "movement_pattern", None),
        "muscle_slug": getattr(meta, "muscle_slug", None),
    }


def _is_timed_reps(reps: Any) -> bool:
    s = str(reps or "").strip().lower()
    return any(tok in s for tok in ("phút", "phut", "min", "giây", "giay", "sec"))


def apply_home_fitness_doses(
    days: list[Any],
    *,
    fitness_baseline: dict[str, Any] | None,
    meta_by_id: dict[int, Any],
    experience_level: int,
    no_equipment: bool,
    home_session: bool = True,
    primer_sets: int | None = None,
) -> None:
    """Overwrite main reps from fitness baseline; home primers = ~50% of matching main."""
    if not home_session:
        return
    from app.services.workout_generation.coach_notes import (
        PRIMER_NOTE_BW_VI,
        PRIMER_NOTE_LOADED_VI,
        PRIMER_TIMED_NOTE_VI,
        load_kind_for_item,
        working_note_vi,
    )

    for day in days or []:
        exercises = list(getattr(day, "exercises", None) or [])
        mains = [
            ex
            for ex in exercises
            if str(getattr(ex, "section", None) or "main") == "main"
        ]
        main_by_id = {int(getattr(ex, "exercise_id")): ex for ex in mains}

        # 1) Dose main lifts first.
        for ex in mains:
            if _is_timed_reps(getattr(ex, "reps", None)):
                continue
            eid = int(getattr(ex, "exercise_id"))
            meta = meta_by_id.get(eid)
            item = _meta_to_item(meta)
            role = str(item.get("movement_role") or "").lower()
            bounds = dose_bounds_for_item(
                item,
                experience_level=experience_level,
                fitness_baseline=fitness_baseline,
                plan_section=None,
                no_equipment=no_equipment,
                home_session=True,
            )
            if str(bounds.get("work_mode")) != "reps":
                continue
            default_sets = int(getattr(ex, "sets", None) or bounds["sets_min"])
            sets, reps = clamp_openai_dose(
                None,
                bounds,
                default_sets=default_sets,
                default_reps=default_reps_label(bounds),
            )
            uni = is_unilateral_name(item)
            if uni:
                parsed = _parse_work_value(reps, "reps")
                if parsed:
                    lo2, hi2 = _halve_reps_range(parsed[0], parsed[1])
                    reps = _format_reps_range(lo2, hi2)
            ex.sets = sets
            ex.reps = reps
            kind = load_kind_for_item(item, no_equipment=no_equipment)
            if uni:
                uni_note = UNILATERAL_NOTE_VI.format(target=_target_reps_display(str(reps)))
                base_note = working_note_vi(reps, kind=kind, include_progress=False)
                ex.notes_vi = f"{uni_note} {base_note}"
            else:
                progress = role in {"compound", "resistance"}
                ex.notes_vi = working_note_vi(
                    reps, kind=kind, include_progress=progress
                )

        # 2) Primers (same id as a main): ~50% of that main's working reps.
        for ex in exercises:
            if str(getattr(ex, "section", None) or "") != "warmup":
                continue
            eid = int(getattr(ex, "exercise_id"))
            main = main_by_id.get(eid)
            if main is None:
                # Stretch / mobility warmup — ensure rest ≥60s on home.
                if int(getattr(ex, "rest_seconds", 0) or 0) < 60:
                    ex.rest_seconds = 60
                continue
            meta = meta_by_id.get(eid)
            item = _meta_to_item(meta)
            kind = load_kind_for_item(item, no_equipment=no_equipment)
            half = half_working_reps_label(getattr(main, "reps", None))
            if half is None and _is_timed_reps(getattr(main, "reps", None)):
                half = half_working_reps_label("30 giây") or "15 giây"
            if half is None:
                half = "5"
            ex.sets = 2 if primer_sets is None else max(1, int(primer_sets))
            ex.reps = half
            ex.rest_seconds = max(60, int(getattr(ex, "rest_seconds", 0) or 0))
            timed_primer = _is_timed_reps(half)
            if timed_primer:
                ex.notes_vi = PRIMER_TIMED_NOTE_VI
            elif kind == "loaded":
                ex.notes_vi = PRIMER_NOTE_LOADED_VI
            else:
                uni = is_unilateral_name(item)
                if uni:
                    uni_note = UNILATERAL_NOTE_VI.format(
                        target=_target_reps_display(str(half))
                    )
                    ex.notes_vi = f"{PRIMER_NOTE_BW_VI} {uni_note}"
                else:
                    ex.notes_vi = PRIMER_NOTE_BW_VI


def apply_no_equip_fitness_doses(
    days: list[Any],
    *,
    fitness_baseline: dict[str, Any] | None,
    meta_by_id: dict[int, Any],
    experience_level: int,
    no_equipment: bool,
) -> None:
    """Backward-compatible alias — only runs for no-equipment home sessions."""
    if not no_equipment:
        return
    apply_home_fitness_doses(
        days,
        fitness_baseline=fitness_baseline,
        meta_by_id=meta_by_id,
        experience_level=experience_level,
        no_equipment=no_equipment,
        home_session=True,
    )


def annotate_week_dose_bounds(
    week_payload: list[dict[str, Any]],
    *,
    experience_level: int,
    fitness_baseline: dict[str, Any] | None,
    no_equipment: bool = False,
    home_session: bool = False,
) -> None:
    """Add bounds to every candidate row in-place before the OpenAI call."""
    for day in week_payload:
        for container_key in ("slots", "blocks"):
            for spec in day.get(container_key) or []:
                section = "cardio" if str(spec.get("block_key") or "") == "cardio" else None
                pool_key = "pool" if container_key == "slots" else "shortlist"
                for item in spec.get(pool_key) or []:
                    item["dose_bounds"] = dose_bounds_for_item(
                        item,
                        experience_level=experience_level,
                        fitness_baseline=fitness_baseline,
                        plan_section=section,
                        no_equipment=no_equipment,
                        home_session=home_session,
                    )


def _parse_work_value(raw: Any, mode: str) -> tuple[int, int] | None:
    text = str(raw or "").strip().lower()
    if mode == "hold":
        match = re.fullmatch(r"(\d+)\s*(?:s|sec|secs|giây|giay)", text)
        return (int(match.group(1)), int(match.group(1))) if match else None
    if mode == "continuous":
        match = re.fullmatch(r"(\d+)\s*(?:p|phút|phut|min|mins|m)", text)
        return (int(match.group(1)), int(match.group(1))) if match else None
    match = re.fullmatch(r"(\d+)(?:\s*[-–]\s*(\d+))?", text)
    if not match:
        return None
    lo = int(match.group(1))
    hi = int(match.group(2) or lo)
    return (min(lo, hi), max(lo, hi))


def clamp_openai_dose(
    proposal: dict[str, Any] | None,
    bounds: dict[str, Any],
    *,
    default_sets: int,
    default_reps: str,
) -> tuple[int, str]:
    """Accept a complete in-range proposal, otherwise use deterministic defaults."""
    mode = str(bounds["work_mode"])
    if mode == "hold":
        minimum, maximum, suffix = bounds["seconds_min"], bounds["seconds_max"], " giây"
    elif mode == "continuous":
        minimum, maximum, suffix = bounds["minutes_min"], bounds["minutes_max"], " phút"
    else:
        minimum, maximum, suffix = bounds["reps_min"], bounds["reps_max"], ""
    safe_sets = max(int(bounds["sets_min"]), min(int(bounds["sets_max"]), int(default_sets)))
    default_value = _parse_work_value(default_reps, mode)
    if default_value and default_value[0] >= int(minimum) and default_value[1] <= int(maximum):
        fallback = (safe_sets, str(default_reps))
    else:
        fallback_reps = (
            f"{int(minimum)}-{int(maximum)}" if int(minimum) != int(maximum) else str(minimum)
        )
        fallback = (safe_sets, f"{fallback_reps}{suffix}")
    if not proposal:
        return fallback
    try:
        sets = int(proposal.get("sets"))
    except (TypeError, ValueError):
        return fallback
    if not int(bounds["sets_min"]) <= sets <= int(bounds["sets_max"]):
        return fallback

    parsed = _parse_work_value(proposal.get("reps"), mode)
    if not parsed:
        return fallback
    lo, hi = parsed
    if lo < int(minimum) or hi > int(maximum):
        return fallback
    reps = f"{lo}-{hi}" if lo != hi else str(lo)
    return sets, f"{reps}{suffix}"
