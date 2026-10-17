"""Dose for pull-up bar and gymnastic rings — isolated from band / DB / floor BW."""

from __future__ import annotations

import math
from typing import Any

_BAND_KEYS = (
    "band",
    "resistance band",
    "dây kháng",
    "day khang",
    "dây thun",
    "day thun",
    "loop band",
)
_IMPROVISED_KEYS = (
    "table",
    "backpack",
    "towel",
    "khăn",
    "khan",
    "ba lô",
    "ba lo",
    "balo",
    "dưới bàn",
    "duoi ban",
    "gầm bàn",
)
_BAR_RINGS_KEYS = (
    "ring",
    "vòng treo",
    "vong treo",
    "pull-up",
    "pullup",
    "pull up",
    "chin-up",
    "chinup",
    "chin up",
    "hít xà",
    "hit xa",
    "kéo xà",
    "keo xa",
    "dead hang",
    "scapular",
    "toes-to-bar",
    "toes to bar",
    "chân chạm xà",
    "chan cham xa",
    "skin the cat",
    "false grip",
    "xà kép",
    "xa kep",
    "pike",
    "hspu",
    "handstand",
    "hand stand",
)
_HOLD_CAP_HANG = 45
_HOLD_CAP_SKILL = 20


def _as_nonnegative_int(value: Any) -> int | None:
    try:
        return max(0, int(value)) if value is not None else None
    except (TypeError, ValueError):
        return None


def _attr(item: Any, key: str) -> Any:
    if isinstance(item, dict):
        return item.get(key)
    return getattr(item, key, None)


def _blob(item: Any) -> str:
    return f"{_attr(item, 'name_vi') or ''} {_attr(item, 'name_en') or ''}".lower()


def is_bar_rings_item(item: Any) -> bool:
    names = _blob(item)
    if not names.strip():
        return False
    if any(k in names for k in _BAND_KEYS):
        return False
    if any(k in names for k in _IMPROVISED_KEYS):
        return False
    if any(k in names for k in _BAR_RINGS_KEYS):
        return True
    if "dip" in names and any(k in names for k in ("ring", "vòng", "vong")):
        return True
    if "hanging" in names or "treo xà" in names or "treo xa" in names:
        return True
    return False


def _is_row(names: str) -> bool:
    if "face pull" in names:
        return False
    return any(k in names for k in ("row", "chèo", "cheo", "inverted"))


def _is_skill_fixed(names: str) -> bool:
    return any(
        k in names
        for k in (
            "skin the cat",
            "toes-to-bar",
            "toes to bar",
            "chân chạm xà",
            "chan cham xa",
            "weighted",
            "đeo tạ",
            "deo ta",
        )
    )


def _is_hold_skill(names: str) -> bool:
    if any(k in names for k in ("l-sit", "lsit", "l sit")):
        return True
    if "false grip" in names:
        return True
    if any(
        k in names
        for k in (
            "dead hang",
            "ring hold",
            "ring support",
            "giữ vòng",
            "giu vong",
            "giữ chống thẳng",
            "treo thả lỏng",
            "treo tha long",
        )
    ):
        return True
    return False


def _t_push(base: dict[str, Any]) -> int | None:
    hit = _as_nonnegative_int(base.get("pushups_max"))
    if hit is None:
        return None
    variant = str(base.get("pushup_variant") or "").strip().lower()
    if variant == "knee":
        return max(0, int(math.floor(hit * 0.45)))
    return hit


def _t_squat(base: dict[str, Any]) -> int | None:
    return _as_nonnegative_int(base.get("squats_max"))


def _t_pull(base: dict[str, Any], *, row_item: bool) -> tuple[int | None, bool]:
    """Return (anchor, identity_row). Never proxy push when a row test exists."""
    pullups = _as_nonnegative_int(base.get("pullups_max"))
    rows = _as_nonnegative_int(base.get("inverted_rows_max"))
    if row_item:
        if rows is not None and (pullups is None or pullups <= 0):
            return rows, True
        if pullups is not None:
            return pullups, False
        if rows is not None:
            return rows, True
        return None, False
    if pullups is not None:
        return pullups, False
    if rows is not None:
        return max(0, int(math.floor(rows * 0.25))), False
    push = _t_push(base)
    if push is None:
        return None, False
    return max(0, int(math.floor(push * 0.15))), False


def _pct_band(role: str | None, experience_level: int | None, no_equipment: bool) -> tuple[float, float]:
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


def _working_reps(
    test_max: int,
    *,
    role: str | None,
    no_equipment: bool,
    experience_level: int | None,
) -> tuple[int, int]:
    if test_max <= 0:
        return 1, 3
    pct_lo, pct_hi = _pct_band(role, experience_level, no_equipment)
    lo = max(1, int(math.floor(test_max * pct_lo)))
    hi = max(lo, int(math.floor(test_max * pct_hi)))
    hi = min(hi, test_max)
    return min(lo, hi), hi


def _slot_and_k(item: Any, base: dict[str, Any]) -> tuple[int | None, float] | None:
    names = _blob(item)
    if _is_skill_fixed(names) or _is_hold_skill(names):
        return None

    row_item = _is_row(names)
    if any(k in names for k in ("bulgarian", "squat bulgaria")):
        raw = _t_squat(base)
        return (raw, 0.65) if raw is not None else None
    if "hamstring" in names or "cuốn đùi sau" in names or "cuon dui sau" in names:
        raw = _t_squat(base)
        return (raw, 0.85) if raw is not None else None

    if any(k in names for k in ("assisted", "trợ", "tro luc", "trợ lực")) and "dip" in names:
        raw = _t_push(base)
        return (raw, 0.75) if raw is not None else None
    if "dip" in names:
        raw = _t_push(base)
        return (raw, 0.65) if raw is not None else None
    if any(k in names for k in ("hspu", "handstand", "hand stand")):
        raw = _t_push(base)
        return (raw, 0.22) if raw is not None else None
    if "pike" in names:
        raw = _t_push(base)
        k = 0.35 if any(x in names for x in ("elevated", "chân cao", "chan cao", "decline")) else 0.45
        return (raw, k) if raw is not None else None
    if any(k in names for k in ("push-up", "push up", "pushup", "chống đẩy", "chong day")):
        raw = _t_push(base)
        return (raw, 0.85) if raw is not None else None
    if any(k in names for k in ("fly", "ép ngực", "ep nguc")) and "rear" not in names and "delt" not in names:
        raw = _t_push(base)
        return (raw, 0.90) if raw is not None else None
    if "triceps" in names or "tay sau" in names:
        raw = _t_push(base)
        return (raw, 0.70) if raw is not None else None

    if "leg raise" in names or "nâng chân" in names or "nang chan" in names:
        raw = _t_push(base)
        if raw is None:
            raw = _t_squat(base)
        return (raw, 0.48) if raw is not None else None
    if "knee raise" in names or "nâng gối" in names or "nang goi" in names:
        raw = _t_push(base)
        if raw is None:
            raw = _t_squat(base)
        return (raw, 0.80) if raw is not None else None

    t_pull, identity = _t_pull(base, row_item=row_item)
    if t_pull is None:
        return None

    if row_item:
        return t_pull, (1.0 if identity else 2.0)
    if "face pull" in names:
        return t_pull, 1.5
    if "rear delt" in names or "bay vai sau" in names:
        return t_pull, 1.5
    if "biceps" in names or "tay trước" in names or "tay truoc" in names:
        return t_pull, 1.5
    if "1/3" in names or "scapular" in names:
        return t_pull, (1.8 if t_pull <= 0 else 0.8)
    if "wide" in names or "tay rộng" in names or "tay rong" in names:
        return t_pull, 0.85
    if "chin" in names or "hướng vào" in names or "huong vao" in names:
        return t_pull, 1.1
    if "neutral" in names or "nắm dọc" in names or "nam doc" in names:
        return t_pull, 1.05
    return t_pull, 1.0


def bar_rings_equivalent_max(
    item: Any,
    baseline: dict[str, Any] | None,
) -> int | None:
    """Equivalent AMRAP on the target bar/rings move after difficulty k."""
    if not is_bar_rings_item(item):
        return None
    names = _blob(item)
    if _is_hold_skill(names):
        return None
    base = dict(baseline or {})
    if _is_skill_fixed(names):
        pullups = _as_nonnegative_int(base.get("pullups_max")) or 0
        if "weighted" in names or "đeo tạ" in names or "deo ta" in names:
            return 8 if pullups >= 8 else 4
        return 5
    pair = _slot_and_k(item, base)
    if pair is None:
        return None
    raw, k = pair
    if raw is None:
        return None
    if raw <= 0:
        return 0
    return max(1, int(math.floor(raw * k)))


def _stretch_ramp(lo: int, hi: int, test_max: int) -> tuple[int, int]:
    """Week 1 at working %; ceiling is equivalent max so weeks can +1 toward the test."""
    if test_max <= 0:
        return 1, 3
    hi = max(lo, int(test_max))
    lo = max(1, min(lo, hi))
    return lo, hi


def bar_rings_working_reps(
    item: Any,
    baseline: dict[str, Any] | None,
    *,
    experience_level: int | None = None,
    no_equipment: bool = False,
) -> tuple[int, int] | None:
    names = _blob(item)
    if not is_bar_rings_item(item) or _is_hold_skill(names):
        return None
    if _is_skill_fixed(names):
        base = dict(baseline or {})
        pullups = _as_nonnegative_int(base.get("pullups_max")) or 0
        if "weighted" in names or "đeo tạ" in names or "deo ta" in names:
            return (5, 8) if pullups >= 8 else (3, 6)
        return (3, 6)
    test_max = bar_rings_equivalent_max(item, baseline)
    if test_max is None:
        return None
    role = str(_attr(item, "movement_role") or "").strip().lower()
    lo, hi = _working_reps(
        test_max,
        role=role,
        no_equipment=no_equipment,
        experience_level=experience_level,
    )
    return _stretch_ramp(lo, hi, test_max)


def bar_rings_hold_bounds(
    item: Any,
    baseline: dict[str, Any] | None,
    *,
    experience_level: int = 2,
) -> dict[str, Any] | None:
    if not is_bar_rings_item(item):
        return None
    names = _blob(item)
    if not _is_hold_skill(names):
        return None
    plank = _as_nonnegative_int((baseline or {}).get("plank_seconds"))
    level = max(1, min(3, int(experience_level or 2)))
    skill = any(k in names for k in ("l-sit", "lsit", "l sit", "false grip"))
    if plank:
        if skill:
            lo = max(8, min(_HOLD_CAP_SKILL, int(math.floor(plank * 0.25 / 5) * 5) or 8))
            hi = max(lo, min(_HOLD_CAP_SKILL, int(math.floor(plank * 0.35 / 5) * 5) or lo))
        else:
            lo = max(15, min(_HOLD_CAP_HANG, int(math.floor(plank * 0.8 / 5) * 5)))
            hi = max(lo, min(_HOLD_CAP_HANG, int(math.floor(plank * 1.0 / 5) * 5)))
    else:
        default = {1: 20, 2: 30, 3: 40}[level]
        if skill:
            lo, hi = 8, min(_HOLD_CAP_SKILL, default)
        else:
            lo, hi = max(15, default - 5), min(_HOLD_CAP_HANG, default + 5)
    return {
        "work_mode": "hold",
        "sets_min": 2,
        "sets_max": 3,
        "seconds_min": lo,
        "seconds_max": hi,
    }
