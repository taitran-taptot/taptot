"""Overlay split scoring on Master WEEK_MATRIX without replacing it."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.workout_generation.capacity import TrainingCapacity

# Loyalty so matrix wins unless an alternative clearly scores higher.
DEFAULT_BONUS = 10

# Overlay Upper/Lower over PPL only when no equipment or strength tests are weak.
SCORE_BEGINNER_OR_WEAK_3D: dict[str, int] = {
    "ul": 30,
    "fb": 0,
    "ppl": 8,
    "ppl_ul": 0,
    "ppl_x2": -25,
    "other": 0,
}

SCORE_L1_6D: dict[str, int] = {
    "ul": 34,
    "fb": 16,
    "ppl_ul": 8,
    "ppl": 4,
    "ppl_x2": -40,
    "other": 0,
}

SCORE_L1_5D: dict[str, int] = {
    "ul": 34,
    "fb": 16,
    "ppl": 8,
    "ppl_ul": 8,
    "ppl_x2": -30,
    "other": 0,
}

SCORE_L1_4D: dict[str, int] = {
    "ul": 28,
    "fb": 18,
    "ppl": -6,
    "ppl_ul": -20,
    "ppl_x2": -30,
    "other": 0,
}

SCORE_GOAL_HYPERTROPHY: dict[str, int] = {
    "ppl": 8,
    "ul": 6,
    "ppl_ul": 6,
    "fb": 0,
    "ppl_x2": 2,
    "other": 0,
}
SCORE_GOAL_FAT_LOSS: dict[str, int] = {
    "fb": 8,
    "ul": 4,
    "ppl": -4,
    "ppl_ul": 0,
    "ppl_x2": -8,
    "other": 0,
}


@dataclass(frozen=True)
class SplitChoice:
    week_code: str
    family: str
    score: int
    reason_vi: str | None
    overridden: bool


def week_family(week_code: str) -> str:
    raw = re.sub(r"\s+", " ", (week_code or "").strip())
    if not raw:
        return "other"
    compact = re.sub(r"\s+", "", raw.replace(",", "")).upper()
    compact = compact.replace("FULLBODY", "FB")
    compact = compact.replace("FULL BODY", "FB")
    if re.match(r"^(PPL){2}$", compact):
        return "ppl_x2"
    if compact.startswith("PPLUL") or compact == "PPLUL":
        return "ppl_ul"
    if compact.startswith("PPL"):
        return "ppl"
    if compact.startswith("LUL") or compact.startswith("LPPL") or compact.startswith("LOWER"):
        return "ul"
    if compact.startswith("FB") or compact.replace("FB", "") == "":
        return "fb"
    # repeated FB,FB,FB → FBFBFB
    if set(re.findall(r"FB|UL|PPL|UPPER|LOWER|CARDIO-CORE|CARDIOCORE", compact)) <= {"FB"} and "FB" in compact:
        return "fb"
    if compact.startswith("UL") or compact.startswith("UPPER"):
        return "ul"
    return "other"


def _candidates(default: str, sessions: int, *, beginner: bool = False) -> list[str]:
    out = [default]
    if sessions == 3:
        out.extend(
            [
                "Upper, Lower, Upper",
                "UL, Cardio-Core",
            ]
        )
    elif sessions == 4:
        out.extend(["Upper, Lower, Upper, Lower"])
    elif sessions == 5:
        out.extend(
            [
                "PPLUL",
                "Upper, Lower, Upper, Lower, Cardio-Core",
            ]
        )
    elif sessions >= 6:
        if beginner:
            out.extend(
                [
                    "PPLUL, Cardio-Core",
                    "Upper, Lower, Upper, Lower, Upper, Lower",
                ]
            )
        else:
            out.extend(["PPLUL", "PPL, Cardio-Core"])
    elif sessions == 2:
        out.extend(["UL"])
    seen: set[str] = set()
    uniq: list[str] = []
    for c in out:
        key = re.sub(r"\s+", "", c.lower())
        if key in seen:
            continue
        seen.add(key)
        uniq.append(c)
    return uniq


def _score_family(
    family: str,
    *,
    week_code: str,
    sessions: int,
    capacity: TrainingCapacity,
    is_default: bool,
    goal: str | None = None,
    focus_areas: list[str] | None = None,
    overlay: bool = False,
) -> int:
    s = DEFAULT_BONUS if is_default else 0
    beginner_or_weak = capacity.effective_level <= 1 or capacity.strength_tier == "weak"
    if sessions == 3 and (overlay or beginner_or_weak):
        s += SCORE_BEGINNER_OR_WEAK_3D.get(family, SCORE_BEGINNER_OR_WEAK_3D["other"])
    if overlay:
        # Overlay path is PPL → UL only; skip gym L1 5–6d UL overrides.
        compact = re.sub(r"\s+", "", week_code or "").upper()
        g = (goal or "").strip().lower()
        if "CARDIO" in compact and beginner_or_weak:
            s -= 16
        if g in {"gain_muscle", "gain_weight"} and "CARDIO" in compact:
            s -= 10
        focuses = {str(x).strip().lower() for x in (focus_areas or [])}
        if "chan" in focuses or "mong" in focuses:
            if family in {"ul", "ppl"}:
                s += 4
        if "nguc" in focuses or "lung" in focuses:
            if family in {"ppl", "ul"} and sessions >= 4:
                s += 3
        return s
    if sessions >= 6 and capacity.effective_level <= 1:
        s += SCORE_L1_6D.get(family, SCORE_L1_6D["other"])
    elif sessions == 5 and beginner_or_weak:
        s += SCORE_L1_5D.get(family, SCORE_L1_5D["other"])
    elif sessions == 4 and beginner_or_weak:
        s += SCORE_L1_4D.get(family, SCORE_L1_4D["other"])
    compact = re.sub(r"\s+", "", week_code or "").upper()
    g = (goal or "").strip().lower()
    if "CARDIO" in compact and beginner_or_weak:
        s -= 16
    if g in {"gain_muscle", "gain_weight"} and "CARDIO" in compact:
        s -= 10
    # Goal overlays only for beginners — L2/L3 keep the Master split.
    if beginner_or_weak and g in {"gain_muscle", "gain_weight"} and sessions >= 4:
        s += SCORE_GOAL_HYPERTROPHY.get(family, 0)
    if beginner_or_weak and g == "lose_weight" and sessions <= 3:
        s += SCORE_GOAL_FAT_LOSS.get(family, 0)
    focuses = {str(x).strip().lower() for x in (focus_areas or [])}
    if "chan" in focuses or "mong" in focuses:
        if family in {"ul", "ppl"}:
            s += 4
    if "nguc" in focuses or "lung" in focuses:
        if family in {"ppl", "ul"} and sessions >= 4:
            s += 3
    return s


def _reason_vi(default: str, winner: str, family: str, capacity: TrainingCapacity, sessions: int) -> str | None:
    if winner == default:
        return None
    if sessions >= 5 and (capacity.effective_level <= 1 or capacity.strength_tier == "weak") and family == "ul":
        return "Người mới 5–6 buổi: Upper/Lower lặp lại, không PPLUL."
    if sessions == 4 and (capacity.effective_level <= 1 or capacity.strength_tier == "weak"):
        return "Người mới 4 buổi: Upper/Lower, không Cardio-Core sau mọi tuần tăng cân."
    return f"Đổi split `{default}` → `{winner}` theo capacity."


def pick_week_code(
    default_week_code: str,
    *,
    sessions: int,
    capacity: TrainingCapacity,
    goal: str | None = None,
    focus_areas: list[str] | None = None,
    no_equipment: bool = False,
) -> SplitChoice:
    default = (default_week_code or "").strip()
    default_fam = week_family(default)
    weak = capacity.strength_tier == "weak"
    # Overlay Upper/Lower only when default is PPL and (no equipment or weak tests).
    # 3-day weeks stay on the Master split (male PPL). Do not override female LUL/LPPL.
    overlay_allowed = (
        default_fam == "ppl"
        and int(sessions) != 3
        and (bool(no_equipment) or weak)
    )
    if not overlay_allowed:
        return SplitChoice(
            week_code=default,
            family=default_fam or "other",
            score=DEFAULT_BONUS,
            reason_vi=None,
            overridden=False,
        )
    beginner = capacity.effective_level <= 1 or weak
    best: SplitChoice | None = None
    for code in _candidates(default, sessions, beginner=beginner):
        fam = week_family(code)
        sc = _score_family(
            fam,
            week_code=code,
            sessions=sessions,
            capacity=capacity,
            is_default=code == default,
            goal=goal,
            focus_areas=focus_areas,
            overlay=True,
        )
        choice = SplitChoice(
            week_code=code,
            family=fam,
            score=sc,
            reason_vi=None,
            overridden=code != default,
        )
        if best is None or sc > best.score:
            best = choice
    assert best is not None
    reason = _reason_vi(default, best.week_code, best.family, capacity, sessions)
    return SplitChoice(
        week_code=best.week_code,
        family=best.family,
        score=best.score,
        reason_vi=reason,
        overridden=best.week_code != default,
    )
