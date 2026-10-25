"""Challenge-only working-load hints from kit tests (Epley / bodyweight proxies)."""

from __future__ import annotations

import math
from typing import Any

BAND_LEVEL_ORDER = ("yellow", "red", "blue", "green", "black")
BAND_LEVEL_ALIAS = {"light": "yellow", "medium": "blue", "heavy": "black"}
BAND_LEVEL_LBS = {"yellow": 10, "red": 15, "blue": 20, "green": 25, "black": 30}
BAND_LEVEL_NAME_VI = {
    "yellow": "vàng",
    "red": "đỏ",
    "blue": "xanh dương",
    "green": "xanh lá",
    "black": "đen",
}

_KIT_ALIASES = {
    "dumbbell": "dumbbell",
    "db": "dumbbell",
    "ta": "dumbbell",
    "tạ đơn": "dumbbell",
    "band": "band",
    "resistance-band": "band",
    "resistance_band": "band",
    "dây": "band",
    "bar_rings": "bar_rings",
    "bar-and-rings": "bar_rings",
    "bar-rings": "bar_rings",
    "bodyweight": "bar_rings",
    "xa": "bar_rings",
}


def epley_1rm(weight_kg: float, reps: int) -> float:
    """Epley 1RM = w × (1 + reps/30)."""
    return float(weight_kg) * (1.0 + max(0, int(reps)) / 30.0)


def working_8_10(one_rm: float) -> float:
    """Working load for ~8–10 reps ≈ 1RM / 1.30."""
    return float(one_rm) / 1.30


def clamp(value: float, lo: float, hi: float) -> float:
    return max(float(lo), min(float(hi), float(value)))


def round_kg(value: float) -> float:
    if value <= 0:
        return 0.0
    return round(float(value) * 2.0) / 2.0


def working_rep_band(test_max: int, *, easy: bool = False) -> tuple[int, int]:
    """70–80% of an AMRAP test (60–75% for beginners / weak tests)."""
    if test_max <= 0:
        return 1, 3
    lo_pct, hi_pct = (0.60, 0.75) if easy else (0.70, 0.80)
    lo = max(1, int(math.floor(test_max * lo_pct)))
    hi = max(lo, int(math.floor(test_max * hi_pct)))
    return lo, min(hi, test_max)


def floor_from_knee_band(test_max: int) -> tuple[int, int]:
    """Standard push-up working reps from a knee-push-up test (not 70% of knee max)."""
    if test_max <= 0:
        return 3, 5
    lo = max(3, int(math.floor(test_max * 0.40)))
    hi = max(lo, int(math.floor(test_max * 0.55)))
    return lo, min(6, max(hi, 5))


def _as_int(val: Any) -> int | None:
    if val is None or val == "":
        return None
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None


def _as_float(val: Any) -> float | None:
    if val is None or val == "":
        return None
    try:
        n = float(val)
    except (TypeError, ValueError):
        return None
    if n < 0 or not math.isfinite(n):
        return None
    return n


def normalize_band_level(raw: Any) -> str | None:
    key = str(raw or "").strip().lower()
    if not key:
        return None
    if key in BAND_LEVEL_ALIAS:
        return BAND_LEVEL_ALIAS[key]
    if key in BAND_LEVEL_LBS:
        return key
    return None


def band_level_label_vi(raw: Any) -> str | None:
    key = normalize_band_level(raw)
    if not key:
        return None
    return f"Dây {BAND_LEVEL_NAME_VI[key]} · {BAND_LEVEL_LBS[key]} lbs"


def suggest_band_level(
    test_level: Any,
    *,
    section: str | None = None,
    role: str | None = None,
) -> str | None:
    key = normalize_band_level(test_level)
    if not key:
        return None
    idx = BAND_LEVEL_ORDER.index(key)
    sec = str(section or "").strip().lower()
    role_l = str(role or "").strip().lower()
    shift = 0
    if sec in {"warmup", "primer"} or role_l in {"primer", "warmup"}:
        shift = -2
    elif role_l in {"isolation", "accessory"}:
        shift = -1
    idx = max(0, min(len(BAND_LEVEL_ORDER) - 1, idx + shift))
    return BAND_LEVEL_ORDER[idx]


def _search_blob(item: Any) -> str:
    if item is None:
        return ""
    if isinstance(item, dict):
        pattern = str(item.get("movement_pattern") or item.get("pattern") or "")
        name = f"{item.get('name_en') or ''} {item.get('name_vi') or ''}"
    else:
        pattern = str(getattr(item, "movement_pattern", "") or "")
        name = f"{getattr(item, 'name_en', '') or ''} {getattr(item, 'name_vi', '') or ''}"
    return f"{pattern} {name}".lower()


def band_slot_for_item(item: Any) -> str:
    blob = _search_blob(item)
    if any(
        tok in blob
        for tok in (
            "h_press",
            "v_press",
            "chest",
            "press",
            "đẩy ngực",
            "day nguc",
            "push-up",
            "push up",
            "fly",
        )
    ):
        return "push"
    if any(
        tok in blob
        for tok in (
            "v_pull",
            "h_pull",
            "pulldown",
            "row",
            "chèo",
            "cheo",
            "kéo xô",
            "keo xo",
            "pull-apart",
            "face pull",
        )
    ):
        return "pull"
    return "squat"


def slot_band_level(baseline: dict[str, Any] | None, slot: str) -> str | None:
    base = baseline or {}
    key = {
        "push": "band_level_push",
        "pull": "band_level_pull",
        "squat": "band_level_squat",
    }.get(slot, "band_level")
    return normalize_band_level(base.get(key) or base.get("band_level"))


def slot_test_reps(baseline: dict[str, Any] | None, slot: str) -> int | None:
    base = baseline or {}
    if slot == "push":
        return _as_int(base.get("pushups_max"))
    if slot == "pull":
        return _as_int(base.get("pullups_max"))
    return _as_int(base.get("squats_max"))


def _amrap_ladder_delta(reps: int) -> int:
    """How many load steps to add so AMRAP lands near 10–20."""
    if reps > 30:
        return 2
    if reps > 20:
        return 1
    if reps < 10:
        return -1
    return 0


def _calibrate_step(
    idx: int,
    n_steps: int,
    test_reps: int | None,
) -> tuple[int, int]:
    """Shift ladder steps so capacity sits in 10–20; return (index, calibrated_reps).

    AMRAP >20 → +1 step, >30 → +2 steps; <10 → −1. Working reps reset to 15 after a bump.
    """
    n = max(1, int(n_steps))
    idx = max(0, min(n - 1, int(idx)))
    if test_reps is None:
        return idx, 15
    reps = int(test_reps)
    delta = _amrap_ladder_delta(reps)
    if delta == 0:
        return idx, reps
    nxt = idx + delta
    if 0 <= nxt <= n - 1:
        return nxt, 15
    if delta > 0:
        return n - 1, max(10, min(20, reps))
    return 0, max(10, min(20, max(reps, 10)))


def _even_floor(n: int) -> int:
    n = int(n)
    return n - (n % 2)


def rep_window(
    calibrated: int,
    *,
    width: int,
    isolation: bool = False,
) -> tuple[int, int]:
    """Even lo–hi span of 2, 4, or 6 reps from ~80% of calibrated AMRAP."""
    w = 2 if int(width) <= 2 else 4 if int(width) <= 4 else 6
    raw = int(round(0.8 * max(0, int(calibrated))))
    hi = _even_floor(max(6, raw))
    floor = 10 if isolation else 4
    cap = 20 if isolation else max(hi, floor + w)
    if isolation:
        hi = min(cap, max(floor, hi))
        hi = _even_floor(hi) or 10
    lo = hi - w
    if lo < floor:
        lo = floor
        hi = min(cap, lo + w)
    lo = max(floor, _even_floor(lo))
    hi = min(cap, lo + w)
    if isolation:
        hi = min(20, max(lo + 2, hi))
    return int(lo), int(hi)


def rep_span_width(
    *,
    section: str | None = None,
    role: str | None = None,
    test_reps: int | None = None,
    isolation: bool = False,
) -> int:
    """2 = heavy/low AMRAP compound, 4 = in-zone compound, 6 = isolation/warmup."""
    sec = str(section or "").strip().lower()
    role_l = str(role or "").strip().lower()
    if isolation or sec in {"warmup", "primer"} or role_l in {
        "primer",
        "warmup",
        "isolation",
        "accessory",
    }:
        return 6
    if test_reps is not None:
        n = int(test_reps)
        if n < 10 or _amrap_ladder_delta(n) > 0:
            return 2
    return 4


def compound_working_reps(calibrated: int) -> tuple[int, int]:
    return rep_window(calibrated, width=4, isolation=False)


def isolation_working_reps(calibrated: int) -> tuple[int, int]:
    return rep_window(calibrated, width=6, isolation=True)


def _timed_load_reps(reps: Any) -> bool:
    blob = str(reps or "").lower()
    return any(tok in blob for tok in ("phút", "phut", "giây", "giay", "min", "sec"))


def _stamp_isolation(section: str | None, role: str | None) -> bool:
    sec = str(section or "").strip().lower()
    role_l = str(role or "").strip().lower()
    return sec in {"warmup", "primer"} or role_l in {
        "primer",
        "warmup",
        "isolation",
        "accessory",
    }


def fallback_rep_label(*, isolation: bool) -> str:
    return "12-18" if isolation else "8-12"


def prescribed_rep_label(
    calibrated: int,
    *,
    section: str | None = None,
    role: str | None = None,
    test_reps: int | None = None,
    has_test: bool = True,
) -> str:
    isolation = _stamp_isolation(section, role)
    if not has_test:
        return fallback_rep_label(isolation=isolation)
    width = rep_span_width(
        section=section, role=role, test_reps=test_reps, isolation=isolation
    )
    lo, hi = rep_window(calibrated, width=width, isolation=isolation)
    return _rep_label(lo, hi)


def calibrate_band_level(
    test_level: Any,
    test_reps: int | None,
) -> tuple[str | None, int]:
    key = normalize_band_level(test_level)
    if not key:
        return None, 15
    idx, cal = _calibrate_step(
        BAND_LEVEL_ORDER.index(key),
        len(BAND_LEVEL_ORDER),
        test_reps,
    )
    return BAND_LEVEL_ORDER[idx], cal


def progress_band_prescription(
    test_level: Any,
    test_reps: int | None,
    *,
    section: str | None = None,
    role: str | None = None,
    easy: bool = False,
) -> tuple[str | None, str | None]:
    """Compound load after 10–20 calibration; isolation/warmup step down.

    Already-black + AMRAP >20 stacks a second tube (yellow) instead of inventing kg.
    L1/weak (`easy`) drops one extra colour after calibration.
    """
    started = normalize_band_level(test_level)
    working, _cal = calibrate_band_level(test_level, test_reps)
    if not working:
        return None, None
    if easy:
        idx = max(0, BAND_LEVEL_ORDER.index(working) - 1)
        working = BAND_LEVEL_ORDER[idx]
    sec = str(section or "").strip().lower()
    role_l = str(role or "").strip().lower()
    light_set = sec in {"warmup", "primer"} or role_l in {
        "primer",
        "warmup",
        "isolation",
        "accessory",
    }
    extra = None
    if light_set:
        working = suggest_band_level(working, section=section, role=role)
    elif (
        working == "black"
        and started == "black"
        and test_reps is not None
        and int(test_reps) > 20
    ):
        extra = "yellow"
    return working, extra


# Adjustable 40 kg kit plates only (no handle): 4×5 + 4×2.5 + 4×1.25.
# Bilateral (two DBs) can use at most half the plates per hand.
DB_EACH_SIDE_KG = (2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 17.5)
# Single implement (goblet / one-arm) may use all plates.
DB_SQUAT_KG = tuple(i * 2.5 for i in range(1, 15))  # 2.5 … 35


def _db_ladder(slot: str) -> tuple[float, ...]:
    return DB_SQUAT_KG if str(slot or "").strip().lower() == "squat" else DB_EACH_SIDE_KG


def snap_db_kg(raw: Any, slot: str = "press") -> float | None:
    kg = _as_float(raw)
    if kg is None or kg <= 0:
        return None
    ladder = _db_ladder(slot)
    return min(ladder, key=lambda step: abs(step - kg))


def _light_db_set(section: str | None, role: str | None, item: Any = None) -> bool:
    return _db_light_steps(section, role, item) > 0


def _db_light_steps(section: str | None, role: str | None, item: Any = None) -> int:
    """Plate steps vs the test load. Negative = heavier (flat bench vs overhead)."""
    sec = str(section or "").strip().lower()
    role_l = str(role or "").strip().lower()
    names, pattern, item_role = _item_blob(item) if item is not None else ("", "", "")
    role_l = role_l or str(item_role or "").strip().lower()
    iso_name = any(
        tok in names
        for tok in (
            "fly",
            "mở ngực",
            "mo nguc",
            "raise",
            "crossover",
            "kickback",
            "skull",
            "pec deck",
        )
    )
    press_name = any(tok in names for tok in ("press", "đẩy", "day nguc", "đẩy ngực"))
    overhead = pattern == "v_push" or any(
        tok in names
        for tok in (
            "overhead",
            "đẩy vai",
            "day vai",
            "military",
            "shoulder press",
        )
    )
    incline = any(tok in names for tok in ("incline", "dốc", "doc ", "dốc lên", "doc len"))
    floor = "floor" in names or "nằm sàn" in names or "san nha" in names
    iso = (role_l in {"isolation", "accessory"} or iso_name) and not (
        press_name and not iso_name
    )
    steps = 0
    if iso:
        steps = 2
    elif overhead:
        steps = 1
    elif incline or floor:
        steps = 1
    if sec in {"warmup", "primer"} or role_l in {"primer", "warmup"}:
        steps += 2
    return steps


def calibrate_db_load(
    test_kg: Any,
    test_reps: int | None,
    *,
    slot: str,
) -> tuple[float | None, int]:
    snapped = snap_db_kg(test_kg, slot)
    if snapped is None:
        return None, 15
    ladder = _db_ladder(slot)
    idx, cal = _calibrate_step(ladder.index(snapped), len(ladder), test_reps)
    return ladder[idx], cal


def progress_db_prescription(
    test_kg: Any,
    test_reps: int | None,
    *,
    slot: str,
    section: str | None = None,
    role: str | None = None,
    easy: bool = False,
    item: Any = None,
    gender: Any = None,
) -> tuple[float | None, int]:
    """Compound kg after 10–20 calibration; isolation/warmup and L1/weak step lighter."""
    kg, cal = calibrate_db_load(test_kg, test_reps, slot=slot)
    if kg is None:
        return None, cal
    ladder = _db_ladder(slot)
    idx = ladder.index(kg)
    steps = _db_light_steps(section, role, item) + (1 if easy else 0)
    if steps:
        idx = max(0, min(len(ladder) - 1, idx - int(steps)))
    return ladder[idx], cal


def db_working_reps(
    test_max: int,
    *,
    bumped: bool = False,
    easy: bool = False,
    isolation: bool = False,
    calibrated: int | None = None,
) -> tuple[int, int]:
    cal = int(calibrated) if calibrated is not None else int(test_max or 0)
    if isolation:
        return isolation_working_reps(cal if cal else 15)
    if calibrated is not None:
        return compound_working_reps(cal)
    if bumped:
        return compound_working_reps(15)
    n = max(0, int(test_max))
    if 10 <= n <= 20:
        return compound_working_reps(n)
    if n > 20 or n < 10:
        return compound_working_reps(15)
    return working_rep_band(n, easy=easy)


def prescription_rpe(raw: Any) -> float | None:
    """PlanSetPrescription.rpe is 1–10; engine uses 0 as “unset”."""
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if 1 <= value <= 10:
        return value
    return None


def suggest_load_note_vi(label: str | None) -> str | None:
    s = str(label or "").strip()
    if not s:
        return None
    if s.lower().startswith("gợi ý"):
        return s[:64]
    return f"Gợi ý: {s}"[:64]


def band_load_note_vi(primary: Any, extra: Any = None) -> str | None:
    main = band_level_label_vi(primary)
    if not main:
        return None
    extra_key = normalize_band_level(extra)
    if not extra_key:
        return main
    return (
        f"{main} + {BAND_LEVEL_NAME_VI[extra_key]} · {BAND_LEVEL_LBS[extra_key]} lbs"
    )


def is_band_exercise(item: Any) -> bool:
    if item is None:
        return False
    if isinstance(item, dict):
        slugs = item.get("equipment_slugs") or item.get("equipment") or ()
        name = f"{item.get('name_en') or ''} {item.get('name_vi') or ''}".lower()
    else:
        slugs = getattr(item, "equipment_slugs", None) or ()
        name = f"{getattr(item, 'name_en', '') or ''} {getattr(item, 'name_vi', '') or ''}".lower()
    slug_s = {str(s or "").strip().lower() for s in slugs if str(s or "").strip()}
    if any("resistance-band" in s or s == "day-mini-band" for s in slug_s):
        return True
    return any(
        tok in name
        for tok in (
            "band",
            "dây kháng",
            "day khang",
            "dây thun",
            "day thun",
            "loop band",
        )
    )


def _as_experience_level(raw: Any) -> int:
    try:
        return max(1, min(3, int(raw)))
    except (TypeError, ValueError):
        return 2


def default_band_level(*, gender: Any = None, experience_level: Any = None) -> str:
    female = str(gender or "").strip().lower() == "female"
    level = _as_experience_level(experience_level)
    if female and level <= 1:
        return "yellow"
    if female or level <= 1:
        return "red"
    return "blue"


def default_db_kg(*, gender: Any = None, experience_level: Any = None, slot: str = "press") -> float:
    female = str(gender or "").strip().lower() == "female"
    level = _as_experience_level(experience_level)
    squat = str(slot or "").strip().lower() == "squat"
    if female and level <= 1:
        return 5.0 if squat else 2.5
    if female or level <= 1:
        return 7.5 if squat else 5.0
    return 10.0 if squat else 7.5


def _stamp_easy(baseline: dict[str, Any] | None) -> bool:
    base = baseline or {}
    flag = base.get("_easy")
    if flag is True:
        return True
    if flag is False:
        return False
    try:
        return int(base.get("experience_level")) <= 1
    except (TypeError, ValueError):
        return False


def attach_band_set_prescriptions(
    days: list[Any] | Any,
    *,
    meta_by_id: dict[int, Any] | None,
    fitness_baseline: dict[str, Any] | None,
) -> None:
    """Stamp per-set band color on generated band exercises."""
    base = fitness_baseline or {}
    easy = _stamp_easy(base)
    fallback = default_band_level(
        gender=base.get("gender"),
        experience_level=base.get("experience_level"),
    )
    day_list = days if isinstance(days, list) else [days]
    metas = meta_by_id or {}
    from app.schemas.plans import PlanSetPrescription

    for day in day_list:
        for ex in list(getattr(day, "exercises", None) or []):
            eid = int(getattr(ex, "exercise_id", 0) or 0)
            meta = metas.get(eid)
            if getattr(ex, "set_prescriptions", None):
                continue
            if not is_band_exercise(meta):
                continue
            section = str(getattr(ex, "section", None) or "main")
            role = None
            if meta is not None:
                role = (
                    meta.get("movement_role")
                    if isinstance(meta, dict)
                    else getattr(meta, "movement_role", None)
                )
            slot = band_slot_for_item(meta)
            test_color = slot_band_level(base, slot)
            test_reps = slot_test_reps(base, slot) if test_color else None
            color, extra = progress_band_prescription(
                test_color or fallback,
                test_reps,
                section=section,
                role=role,
                easy=easy if test_color else False,
            )
            label = suggest_load_note_vi(band_load_note_vi(color, extra))
            if not label:
                continue
            _lv, cal = calibrate_band_level(test_color or fallback, test_reps)
            if (
                str(getattr(ex, "section", "") or "") not in {"abs", "cardio", "warmup", "primer"}
                and not _timed_load_reps(getattr(ex, "reps", None))
            ):
                ex.reps = prescribed_rep_label(
                    cal,
                    section=section,
                    role=role,
                    test_reps=test_reps,
                    has_test=bool(test_color),
                )
            n = max(1, int(getattr(ex, "sets", None) or 1))
            reps = getattr(ex, "reps", None)
            rest = int(getattr(ex, "rest_seconds", None) or 90)
            rpe = prescription_rpe(getattr(ex, "rpe", None))
            ex.set_prescriptions = [
                PlanSetPrescription(
                    reps=reps if reps is not None else "12",
                    rest_seconds=rest,
                    rpe=rpe,
                    load_note_vi=label,
                )
                for _ in range(n)
            ]
            notes = str(getattr(ex, "notes_vi", None) or "").strip()
            if notes:
                kept = [
                    part.strip()
                    for part in notes.rstrip(".").split(".")
                    if part.strip()
                    and "mức dây" not in part.lower()
                    and not part.strip().lower().startswith("dây ")
                ]
                ex.notes_vi = (". ".join(kept) + ".") if kept else None


_DB_NAME_KEYS = (
    "dumbbell",
    "tạ đơn",
    "ta don",
    "goblet",
    "kettlebell",
    "tạ ấm",
    "ta am",
)
_NOT_DB_NAME_KEYS = (
    "không tạ",
    "khong ta",
    "bodyweight",
    "push-up",
    "push up",
    "chống đẩy",
    "chong day",
    "pull-up",
    "pull up",
    "kéo xà",
    "keo xa",
    "plank",
    "jumping jack",
)
_DB_LIFT_KEYS = (
    "press",
    "đẩy",
    "day nguc",
    "day vai",
    "row",
    "chèo",
    "cheo",
    "fly",
    "ép ngực",
    "ep nguc",
    "raise",
    "nâng vai",
    "nang vai",
    "curl",
    "deadlift",
    "rdl",
    "shrug",
    "pullover",
    "kickback",
    "arnold",
    "mở ngực",
    "mo nguc",
)


def is_dumbbell_exercise(item: Any) -> bool:
    """True for named DB lifts, or slug=dumbbell plus a loaded-lift name — never BW."""
    if item is None or is_band_exercise(item):
        return False
    if isinstance(item, dict):
        name = f"{item.get('name_en') or ''} {item.get('name_vi') or ''}".lower()
        slugs = item.get("equipment_slugs") or item.get("equipment") or ()
    else:
        name = f"{getattr(item, 'name_en', '') or ''} {getattr(item, 'name_vi', '') or ''}".lower()
        slugs = getattr(item, "equipment_slugs", None) or ()
    if any(tok in name for tok in _NOT_DB_NAME_KEYS):
        return False
    if any(tok in name for tok in _DB_NAME_KEYS):
        return True
    linked = {str(s).strip().lower() for s in (slugs or ()) if str(s).strip()}
    if "dumbbell" not in linked:
        return False
    return any(tok in name for tok in _DB_LIFT_KEYS)


def should_stamp_db_load(item: Any, *, section: str | None = None) -> bool:
    sec = str(section or "main").strip().lower()
    if sec in {"cardio", "cooldown"}:
        return False
    if item is None or is_band_exercise(item):
        return False
    names, _pattern, role = _item_blob(item)
    if role in {"cardio", "conditioning", "core"}:
        return False
    from app.services.workout_generation.effort_mode import exercise_effort_mode

    mode = exercise_effort_mode(item, plan_section=sec)
    if mode in {"hold", "continuous"}:
        return False
    if "plank" in names or "hollow" in names:
        return False
    return is_dumbbell_exercise(item)


_ONE_ARM_KEYS = (
    "one-arm",
    "one arm",
    "single-arm",
    "single arm",
    "một tay",
    "mot tay",
    "suitcase",
)
_ONE_BELL_KEYS = (
    "goblet",
    "ôm tạ",
    "om ta",
    "front squat",
    "sumo squat",
    "skullcrusher",
    "skull crusher",
    "overhead tricep",
    "seated overhead tricep",
    "situp",
    "sit-up",
    "sit up",
)
_SPLIT_LOAD_KEYS = (
    "lunge",
    "step-up",
    "step up",
    "kickstand",
    "single-leg",
    "single leg",
    "một chân",
    "mot chan",
    "kickback",
    "concentration",
    "unilateral",
    "one-arm",
    "one arm",
    "single-arm",
    "single arm",
    "một tay",
    "mot tay",
    "single leg calf",
)


def _is_one_arm_db(item: Any) -> bool:
    names, _pattern, _role = _item_blob(item)
    return any(tok in names for tok in _ONE_ARM_KEYS)


def _db_hold_kind(item: Any) -> str:
    """one_bell = two hands on one DB; split = one arm/leg; pair = a DB in each hand."""
    names, _pattern, _role = _item_blob(item)
    if any(tok in names for tok in _SPLIT_LOAD_KEYS):
        return "split"
    if any(tok in names for tok in _ONE_BELL_KEYS):
        return "one_bell"
    return "pair"


def _halve_db_kg(kg: Any, slot: str) -> float | None:
    raw = _as_float(kg)
    if raw is None or raw <= 0:
        return None
    return snap_db_kg(raw / 2.0, slot)


def _db_slot_for_item(item: Any) -> str:
    names, pattern, _role = _item_blob(item)
    if (
        pattern in {"squat", "hinge"}
        or any(tok in names for tok in ("squat", "goblet", "lunge", "bulgarian", "deadlift"))
    ):
        return "squat"
    if pattern == "h_pull" or any(tok in names for tok in ("row", "chèo", "cheo")):
        return "row"
    return "press"


def attach_db_set_prescriptions(
    days: list[Any] | Any,
    *,
    meta_by_id: dict[int, Any] | None,
    fitness_baseline: dict[str, Any] | None,
) -> None:
    """Stamp per-set dumbbell kg as a suggestion, not a hard prescription."""
    base = fitness_baseline or {}
    easy = _stamp_easy(base)
    day_list = days if isinstance(days, list) else [days]
    metas = meta_by_id or {}
    hints = list(base.get("_load_hints") or [])
    if not hints:
        hints = build_load_hints("dumbbell", base)
    from app.schemas.plans import PlanSetPrescription

    for day in day_list:
        for ex in list(getattr(day, "exercises", None) or []):
            eid = int(getattr(ex, "exercise_id", 0) or 0)
            meta = metas.get(eid)
            if not should_stamp_db_load(meta, section=str(getattr(ex, "section", None) or "main")):
                continue
            section = str(getattr(ex, "section", None) or "main")
            role = None
            if meta is not None:
                role = (
                    meta.get("movement_role")
                    if isinstance(meta, dict)
                    else getattr(meta, "movement_role", None)
                )
            slot = _db_slot_for_item(meta)
            if slot == "squat":
                test_kg = _as_float(base.get("goblet_kg"))
                test_reps = _as_int(base.get("goblet_reps")) or _as_int(base.get("squats_max"))
            elif slot == "row":
                test_kg = _as_float(base.get("db_row_kg"))
                test_reps = _as_int(base.get("db_row_reps"))
            else:
                test_kg = _as_float(base.get("db_press_kg"))
                test_reps = _as_int(base.get("db_press_reps"))
            used_test = test_kg is not None
            if not used_test:
                test_kg = default_db_kg(
                    gender=base.get("gender"),
                    experience_level=base.get("experience_level"),
                    slot=slot,
                )
                test_reps = None
            work, cal = progress_db_prescription(
                test_kg,
                test_reps,
                slot=slot,
                section=section,
                role=role,
                easy=easy if used_test else False,
                item=meta,
                gender=base.get("gender"),
            )
            if not work:
                continue
            hold = _db_hold_kind(meta)
            if hold in {"split", "pair"} and slot == "squat":
                work = _halve_db_kg(work, slot)
            elif hold == "split":
                work = _halve_db_kg(work, slot)
            if not work:
                continue
            kg = round_kg(work)
            suffix = "kg mỗi tay" if hold == "pair" else "kg"
            label = suggest_load_note_vi(f"{kg:g}{suffix}")
            if not label:
                continue
            from app.services.workout_generation.effort_mode import exercise_effort_mode

            if (
                str(getattr(ex, "section", "") or "") not in {"abs", "cardio", "warmup", "primer"}
                and not (
                    _timed_load_reps(getattr(ex, "reps", None))
                    and exercise_effort_mode(meta) == "hold"
                )
            ):
                ex.reps = prescribed_rep_label(
                    cal,
                    section=section,
                    role=role,
                    test_reps=test_reps,
                    has_test=used_test,
                )
            n = max(1, int(getattr(ex, "sets", None) or 1))
            reps = getattr(ex, "reps", None)
            rest = int(getattr(ex, "rest_seconds", None) or 90)
            rpe = prescription_rpe(getattr(ex, "rpe", None))
            ex.set_prescriptions = [
                PlanSetPrescription(
                    reps=reps if reps is not None else "12",
                    rest_seconds=rest,
                    rpe=rpe,
                    load_note_vi=label,
                )
                for _ in range(n)
            ]
            notes = str(getattr(ex, "notes_vi", None) or "").strip()
            if notes:
                kept = [
                    part.strip()
                    for part in notes.rstrip(".").split(".")
                    if part.strip()
                    and "gợi ý tạ" not in part.lower()
                    and "kg mỗi tay" not in part.lower()
                    and "kg tổng" not in part.lower()
                ]
                ex.notes_vi = (". ".join(kept) + ".") if kept else None


def infer_test_kit(baseline: dict[str, Any] | None, equipment_list: list[str] | None) -> str:
    raw = str((baseline or {}).get("test_kit") or "").strip().lower()
    if raw in _KIT_ALIASES:
        return _KIT_ALIASES[raw]
    slugs = {str(s or "").strip().lower() for s in (equipment_list or []) if str(s or "").strip()}
    if "dumbbell" in slugs:
        return "dumbbell"
    if any("resistance-band" in s or s == "day-mini-band" for s in slugs):
        return "band"
    return "bar_rings"


def _rep_label(lo: int, hi: int) -> str:
    return f"{lo}-{hi}" if lo != hi else str(lo)


def _hint(
    pattern: str,
    *,
    working_reps: str,
    load_kg_each: float | None = None,
    note_vi: str,
    band_level: str | None = None,
    load_note_vi: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "pattern": pattern,
        "working_reps": working_reps,
        "note_vi": note_vi,
    }
    if load_kg_each is not None and load_kg_each > 0:
        row["load_kg_each"] = round_kg(load_kg_each)
    if load_note_vi:
        row["load_note_vi"] = load_note_vi
    elif band_level:
        row["band_level"] = band_level
        label = band_level_label_vi(band_level)
        if label:
            row["load_note_vi"] = label
    if band_level:
        row["band_level"] = band_level
    return row


def build_tests_vi(kit: str, baseline: dict[str, Any], gender: str | None = None) -> list[str]:
    """Vietnamese sentences naming the tests the user actually did."""
    out: list[str] = []
    female = str(gender or "").strip().lower() == "female"
    plank = _as_int(baseline.get("plank_seconds"))

    if kit == "dumbbell":
        press_r = _as_int(baseline.get("db_press_reps"))
        press_kg = _as_float(baseline.get("db_press_kg"))
        row_r = _as_int(baseline.get("db_row_reps"))
        row_kg = _as_float(baseline.get("db_row_kg"))
        gob_r = _as_int(baseline.get("goblet_reps"))
        gob_kg = _as_float(baseline.get("goblet_kg"))
        if press_r is not None:
            if press_kg:
                out.append(f"đẩy ngực tạ đơn {press_r} cái × {press_kg:g} kg")
            else:
                out.append(f"đẩy ngực tạ đơn {press_r} cái")
        if row_r is not None:
            if row_kg:
                out.append(f"chèo tạ đơn {row_r} cái × {row_kg:g} kg")
            else:
                out.append(f"chèo tạ đơn {row_r} cái")
        if gob_r is not None:
            if gob_kg:
                out.append(f"goblet squat {gob_r} cái × {gob_kg:g} kg")
            else:
                out.append(f"goblet squat {gob_r} cái")
        elif _as_int(baseline.get("squats_max")) is not None:
            out.append(f"squat {_as_int(baseline.get('squats_max'))} cái")
    elif kit == "band":
        push = _as_int(baseline.get("pushups_max"))
        pull = _as_int(baseline.get("pullups_max"))
        squat = _as_int(baseline.get("squats_max"))
        if push is not None:
            out.append(f"đẩy ngực dây {push} cái")
        if pull is not None:
            out.append(f"kéo xô dây {pull} cái")
        if squat is not None:
            out.append(f"squat {squat} cái")
        level = str(baseline.get("band_level") or "").strip()
        if level:
            label = band_level_label_vi(level) or level
            out.append(f"mức dây {label}")
    else:
        push = _as_int(baseline.get("pushups_max"))
        if push is not None:
            variant = str(baseline.get("pushup_variant") or "")
            name = "chống đẩy gối" if variant == "knee" else "chống đẩy"
            out.append(f"{name} {push} cái")
        hang = _as_int(baseline.get("pull_hold_seconds"))
        inv = _as_int(baseline.get("inverted_rows_max"))
        pull = _as_int(baseline.get("pullups_max"))
        variant = str(baseline.get("pull_test_variant") or "")
        if variant == "hang" or (hang is not None and pull is None and inv is None):
            if hang is not None:
                out.append(f"treo xà {hang} giây")
        elif variant.startswith("inverted") or inv is not None:
            if inv is not None:
                out.append(f"chèo vòng treo {inv} cái")
        elif pull is not None:
            out.append("treo xà" if female and pull == 0 else f"kéo xà {pull} cái")
        squat = _as_int(baseline.get("squats_max"))
        if squat is not None:
            out.append(f"squat {squat} cái")

    if plank is not None:
        out.append(f"plank {plank} giây")
    return out


def build_load_hints(
    kit: str,
    baseline: dict[str, Any],
    weight_kg: Any = None,
    *,
    easy: bool = False,
) -> list[dict[str, Any]]:
    hints: list[dict[str, Any]] = []
    bw = _as_float(weight_kg) or 0.0
    pct_note = "60–75% max test" if easy else "70–80% max test"

    def _wr(n: int) -> tuple[int, int]:
        return working_rep_band(n, easy=easy)

    if kit == "dumbbell":
        press_r = _as_int(baseline.get("db_press_reps"))
        press_kg = _as_float(baseline.get("db_press_kg"))
        if press_r is not None and press_kg:
            work, cal = progress_db_prescription(
                press_kg,
                press_r,
                slot="press",
                section="main",
                role="compound",
                easy=easy,
            )
            wr = compound_working_reps(cal)
            iso_kg, _ = progress_db_prescription(
                press_kg,
                press_r,
                slot="press",
                section="isolation",
                role="isolation",
                easy=easy,
            )
            inc_kg, _ = progress_db_prescription(
                press_kg,
                press_r,
                slot="press",
                section="main",
                role="compound",
                easy=easy,
                item={"name_en": "incline press", "name_vi": "đẩy ngực dốc lên"},
            )
            iso_wr = isolation_working_reps(cal)
            hints.append(
                _hint(
                    "h_press",
                    working_reps=_rep_label(*wr),
                    load_kg_each=work,
                    load_note_vi=f"{round_kg(work or 0):g}kg",
                    note_vi=(
                        f"Đẩy ngực tạ đơn: {round_kg(work or 0):g} kg mỗi tay "
                        f"({_rep_label(*wr)} cái)."
                    ),
                )
            )
            hints.append(
                _hint(
                    "h_press_incline",
                    working_reps=_rep_label(*wr),
                    load_kg_each=inc_kg,
                    load_note_vi=f"{round_kg(inc_kg or 0):g}kg",
                    note_vi=(
                        f"Đẩy ngực dốc tạ đơn: {round_kg(inc_kg or 0):g} kg mỗi tay "
                        f"(nhẹ hơn đẩy phẳng 1 nấc)."
                    ),
                )
            )
            hints.append(
                _hint(
                    "iso_chest",
                    working_reps=_rep_label(*iso_wr),
                    load_kg_each=iso_kg,
                    load_note_vi=(
                        f"{round_kg(iso_kg or 0):g}kg"
                    ),
                    note_vi=(
                        f"Isolation/fly ngực {round_kg(iso_kg or 0):g} kg, "
                        f"{_rep_label(*iso_wr)} cái ({pct_note})."
                    ),
                )
            )
        elif press_r is not None:
            wr = _wr(press_r)
            hints.append(
                _hint(
                    "h_press",
                    working_reps=_rep_label(*wr),
                    note_vi=f"Đẩy ngực: {_rep_label(*wr)} cái ({pct_note}).",
                )
            )
        row_r = _as_int(baseline.get("db_row_reps"))
        row_kg = _as_float(baseline.get("db_row_kg"))
        if row_r is not None and row_kg:
            work, cal = progress_db_prescription(
                row_kg,
                row_r,
                slot="row",
                section="main",
                role="compound",
                easy=easy,
            )
            wr = compound_working_reps(cal)
            hints.append(
                _hint(
                    "h_pull",
                    working_reps=_rep_label(*wr),
                    load_kg_each=work,
                    load_note_vi=f"{round_kg(work or 0):g}kg",
                    note_vi=(
                        f"Chèo tạ đơn hai tay: {round_kg(work or 0):g} kg mỗi tay "
                        f"({_rep_label(*wr)} cái)."
                    ),
                )
            )
            one_kg = _halve_db_kg(work, "row")
            hints.append(
                _hint(
                    "h_pull_one_arm",
                    working_reps=_rep_label(*wr),
                    load_kg_each=one_kg,
                    load_note_vi=f"{round_kg(one_kg or 0):g}kg",
                    note_vi=(
                        f"Chèo tạ đơn một tay: {round_kg(one_kg or 0):g} kg "
                        f"(khoảng nửa tạ chèo hai tay)."
                    ),
                )
            )
        elif row_r is not None:
            wr = _wr(row_r)
            hints.append(
                _hint(
                    "h_pull",
                    working_reps=_rep_label(*wr),
                    note_vi=f"Chèo: {_rep_label(*wr)} cái ({pct_note}).",
                )
            )
        gob_r = _as_int(baseline.get("goblet_reps")) or _as_int(baseline.get("squats_max"))
        gob_kg = _as_float(baseline.get("goblet_kg"))
        if gob_r is not None and gob_kg:
            work, cal = progress_db_prescription(
                gob_kg,
                gob_r,
                slot="squat",
                section="main",
                role="compound",
                easy=easy,
            )
            wr = compound_working_reps(cal)
            hints.append(
                _hint(
                    "squat",
                    working_reps=_rep_label(*wr),
                    load_kg_each=work,
                    load_note_vi=f"{round_kg(work or 0):g}kg",
                    note_vi=(
                        f"Goblet squat: {round_kg(work or 0):g} kg "
                        f"({_rep_label(*wr)} cái)."
                    ),
                )
            )
        elif gob_r is not None:
            wr = _wr(gob_r)
            hints.append(
                _hint(
                    "squat",
                    working_reps=_rep_label(*wr),
                    note_vi=f"Squat: {_rep_label(*wr)} cái ({pct_note}).",
                )
            )
        return hints

    if kit == "band":

        def _slot_hint(slot: str) -> tuple[str | None, str, str | None, int]:
            reps = slot_test_reps(baseline, slot)
            color, extra = progress_band_prescription(
                slot_band_level(baseline, slot),
                reps,
                section="main",
                role="compound",
                easy=easy,
            )
            _lv, cal = calibrate_band_level(slot_band_level(baseline, slot), reps)
            note = band_load_note_vi(color, extra)
            extra_txt = f" ({note})" if note else ""
            return color, extra_txt, note, cal

        push_lv, push_extra, push_note, push_cal = _slot_hint("push")
        pull_lv, pull_extra, pull_note, pull_cal = _slot_hint("pull")
        squat_lv, squat_extra, squat_note, squat_cal = _slot_hint("squat")
        push = _as_int(baseline.get("pushups_max"))
        if push is not None:
            wr = compound_working_reps(push_cal)
            hints.append(
                _hint(
                    "h_press",
                    working_reps=_rep_label(*wr),
                    note_vi=f"Band Chest Press / đẩy ngực dây: {_rep_label(*wr)} cái — không bịa kg.{push_extra}",
                    band_level=push_lv,
                    load_note_vi=push_note,
                )
            )
            iso_lv, _ = progress_band_prescription(
                slot_band_level(baseline, "push"),
                push,
                section="main",
                role="isolation",
                easy=easy,
            )
            iso_wr = isolation_working_reps(push_cal)
            iso_note = band_load_note_vi(iso_lv, None)
            hints.append(
                _hint(
                    "iso_chest",
                    working_reps=_rep_label(*iso_wr),
                    note_vi=f"Isolation ngực dây: {_rep_label(*iso_wr)} cái.{(' (' + iso_note + ')') if iso_note else ''}",
                    band_level=iso_lv,
                    load_note_vi=iso_note,
                )
            )
        pull = _as_int(baseline.get("pullups_max"))
        if pull is not None:
            wr = compound_working_reps(pull_cal)
            note = f"Kéo xô/chèo dây: {_rep_label(*wr)} cái — không bịa kg{pull_extra}."
            hints.append(
                _hint(
                    "v_pull",
                    working_reps=_rep_label(*wr),
                    note_vi=note,
                    band_level=pull_lv,
                    load_note_vi=pull_note,
                )
            )
            hints.append(
                _hint(
                    "h_pull",
                    working_reps=_rep_label(*wr),
                    note_vi=note,
                    band_level=pull_lv,
                    load_note_vi=pull_note,
                )
            )
        squat = _as_int(baseline.get("squats_max"))
        if squat is not None:
            wr = compound_working_reps(squat_cal)
            hints.append(
                _hint(
                    "squat",
                    working_reps=_rep_label(*wr),
                    note_vi=f"Squat dây: {_rep_label(*wr)} cái.{squat_extra}",
                    band_level=squat_lv,
                    load_note_vi=squat_note,
                )
            )
        return hints

    push = _as_int(baseline.get("pushups_max"))
    variant = str(baseline.get("pushup_variant") or "")
    if push is not None:
        wr = _wr(push)
        bench_kg = None
        db_press = None
        if bw > 0 and variant != "knee":
            load = 0.66 * bw
            factor = clamp(push / 20.0, 0.45, 1.3)
            bench_kg = load * factor
            db_press = 0.40 * bench_kg
        name = "Chống đẩy gối" if variant == "knee" else "Chống đẩy"
        note = f"{name}: {_rep_label(*wr)} cái."
        if db_press:
            note += (
                f" Nếu lịch có tạ: bench 8–10 ~{round_kg(bench_kg or 0):g} kg; "
                f"DB press mỗi tay ~{round_kg(db_press):g} kg."
            )
        hints.append(
            _hint("h_press", working_reps=_rep_label(*wr), load_kg_each=db_press, note_vi=note)
        )
        if variant == "knee":
            fl = floor_from_knee_band(push)
            hints.append(
                _hint(
                    "h_press_floor",
                    working_reps=_rep_label(*fl),
                    note_vi=f"Chống đẩy sàn (từ test quỳ): {_rep_label(*fl)} cái.",
                )
            )

    pull_variant = str(baseline.get("pull_test_variant") or "").strip().lower()
    inv = _as_int(baseline.get("inverted_rows_max"))
    pullups = _as_int(baseline.get("pullups_max"))
    inverted = pull_variant.startswith("inverted") or (inv is not None and pullups is None)
    if inverted and inv is not None:
        wr = _wr(inv)
        hints.append(
            _hint(
                "h_pull",
                working_reps=_rep_label(*wr),
                note_vi=f"Chèo vòng treo: {_rep_label(*wr)} cái — không gắn kg kéo xà.",
            )
        )
    elif pullups is not None:
        wr = _wr(pullups)
        pulldown = None
        db_row = None
        if bw > 0:
            one_rm = bw * (1.0 + pullups / 30.0)
            pulldown = working_8_10(one_rm)
            db_row = 0.40 * pulldown
        note = f"Kéo xà: {_rep_label(*wr)} cái."
        if pulldown:
            note += (
                f" Pulldown 8–10 ~{round_kg(pulldown):g} kg; "
                f"DB row mỗi tay ~{round_kg(db_row or 0):g} kg."
            )
        hints.append(_hint("v_pull", working_reps=_rep_label(*wr), load_kg_each=pulldown, note_vi=note))
        hints.append(_hint("h_pull", working_reps=_rep_label(*wr), load_kg_each=db_row, note_vi=note))

    squat = _as_int(baseline.get("squats_max"))
    if squat is not None:
        wr = _wr(squat)
        hints.append(
            _hint("squat", working_reps=_rep_label(*wr), note_vi=f"Squat thể trọng: {_rep_label(*wr)} cái.")
        )
    return hints


def _kits_for_load_hints(
    baseline: dict[str, Any],
    equipment_list: list[str] | None,
    primary: str,
) -> list[str]:
    slugs = {str(s or "").strip().lower() for s in (equipment_list or []) if str(s or "").strip()}
    has_db = (
        primary == "dumbbell"
        or "dumbbell" in slugs
        or any(baseline.get(k) not in (None, "") for k in ("db_press_kg", "db_row_kg", "goblet_kg"))
    )
    has_band = (
        primary == "band"
        or any("resistance-band" in s or s == "day-mini-band" for s in slugs)
        or any(
            baseline.get(k) not in (None, "")
            for k in ("band_level", "band_level_push", "band_level_pull", "band_level_squat")
        )
    )
    has_bar = primary == "bar_rings" or bool(
        slugs & {"pull-up-bar", "gymnastic-rings", "parallel-bars"}
    )
    kits: list[str] = []
    if has_db:
        kits.append("dumbbell")
    if has_band:
        kits.append("band")
    if has_bar or not kits:
        kits.append("bar_rings")
    return kits


def apply_challenge_load(
    baseline: dict[str, Any] | None,
    *,
    weight_kg: Any = None,
    gender: str | None = None,
    experience_level: Any = None,
    equipment_list: list[str] | None = None,
    easy: bool = False,
) -> dict[str, Any]:
    """Attach test_kit, tests_vi, load_hints onto a fitness_baseline copy."""
    out = dict(baseline or {})
    if gender and not out.get("gender"):
        out["gender"] = str(gender).strip().lower()
    if experience_level is not None and out.get("experience_level") is None:
        out["experience_level"] = experience_level
    out["_easy"] = bool(easy)
    kit = infer_test_kit(out, equipment_list)
    out["test_kit"] = kit
    tests = build_tests_vi(kit, out, gender)
    hints: list[dict[str, Any]] = []
    for extra_kit in _kits_for_load_hints(out, equipment_list, kit):
        hints.extend(build_load_hints(extra_kit, out, weight_kg, easy=easy))
    out["_tests_vi"] = tests
    out["_load_hints"] = hints
    return out


def public_baseline(baseline: dict[str, Any] | None) -> dict[str, Any]:
    return {k: v for k, v in dict(baseline or {}).items() if not str(k).startswith("_")}


def _item_blob(item: Any) -> tuple[str, str, str]:
    if isinstance(item, dict):
        names = f"{item.get('name_vi') or ''} {item.get('name_en') or ''}".strip().lower()
        pattern = str(item.get("movement_pattern") or "").strip().lower()
        role = str(item.get("movement_role") or "").strip().lower()
        return names, pattern, role
    names = f"{getattr(item, 'name_vi', '') or ''} {getattr(item, 'name_en', '') or ''}".strip().lower()
    pattern = str(getattr(item, "movement_pattern", "") or "").strip().lower()
    role = str(getattr(item, "movement_role", "") or "").strip().lower()
    return names, pattern, role


def hint_for_item(item: Any, hints: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    """Pick the load hint whose pattern best matches an exercise."""
    if not hints:
        return None
    dict_hints = [h for h in hints if isinstance(h, dict)]
    if is_band_exercise(item):
        dict_hints = [
            h
            for h in dict_hints
            if h.get("band_level")
            or (h.get("load_note_vi") and not h.get("load_kg_each"))
        ]
    elif is_dumbbell_exercise(item):
        dict_hints = [h for h in dict_hints if h.get("load_kg_each")]
    else:
        dict_hints = [
            h
            for h in dict_hints
            if not h.get("load_kg_each") and not h.get("band_level")
        ]
    if not dict_hints:
        return None
    hints = dict_hints
    names, pattern, role = _item_blob(item)
    want: str | None = None
    knee = any(k in names for k in ("knee", "gối", "goi", "quỳ", "quy"))
    pullupish = any(
        k in names
        for k in ("pull-up", "pullup", "pull up", "kéo xà", "hít xà", "chin-up", "chinup")
    ) and not any(k in names for k in ("inverted", "row", "chèo", "scapular", "assisted", "1/3"))
    iso_name = any(
        k in names
        for k in ("fly", "mở ngực", "mo nguc", "raise", "crossover", "curl", "kickback", "skull")
    )
    press_name = any(k in names for k in ("press", "đẩy", "day nguc"))
    if (role == "isolation" or iso_name) and not (press_name and not iso_name):
        want = "iso_chest"
    elif any(k in names for k in ("incline", "dốc", "doc ")) and (
        pattern in {"h_push", "v_push"} or "press" in names or "đẩy" in names
    ):
        want = "h_press_incline"
    elif pattern in {"h_push", "v_push"} or any(
        k in names for k in ("press", "push-up", "push up", "chống đẩy", "bench", "đẩy ngực")
    ):
        want = "h_press"
    elif pattern == "v_pull" or any(
        k in names for k in ("pulldown", "pull-up", "kéo xà", "kéo xô", "chin")
    ):
        want = "v_pull"
    elif pattern == "h_pull" or any(k in names for k in ("row", "chèo", "face pull")):
        want = "h_pull_one_arm" if _is_one_arm_db(item) else "h_pull"
    elif pattern == "squat" or "squat" in names or "goblet" in names:
        want = "squat"
    elif pattern == "hinge":
        want = "squat"
    by_pat = {str(h.get("pattern") or ""): h for h in hints if isinstance(h, dict)}
    if want and want in by_pat:
        return by_pat[want]
    if want == "h_pull_one_arm" and "h_pull" in by_pat:
        return by_pat["h_pull"]
    if want == "h_press_incline" and "h_press" in by_pat:
        return by_pat["h_press"]
    if want == "h_press_floor" and "h_press" in by_pat:
        return by_pat["h_press"]
    if want == "v_pull" and "h_pull" in by_pat and not pullupish:
        return by_pat["h_pull"]
    if want == "h_pull" and "v_pull" in by_pat:
        return by_pat["v_pull"]
    if role == "isolation" or iso_name:
        for key in ("iso_chest", "h_press", "h_pull"):
            if key in by_pat:
                return by_pat[key]
    return None
