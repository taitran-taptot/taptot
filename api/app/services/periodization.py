"""Periodization helpers — expand a 1-week template across multiple weeks."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any

from app.services.workout_rest import snap_rest_seconds

MAIN_SECTIONS = frozenset({"main", "exercises"})


@dataclass(frozen=True)
class OverloadProfile:
    name: str
    max_sets: int
    set_ramp_from_week: int
    set_ramp_every_n_weeks: int | None
    max_set_bonus: int
    rep_bump_from_week: int | None
    rest_reduction_pct_per_step: float
    max_rest_reduction_pct: float
    deload_min_weeks: int
    deload_rest_multiplier: float
    sections_to_bump: frozenset[str]


# Double progression cue is load-based (user-driven). Engine keeps range fixed.
# Novice: no auto set/rep ramps — only deload.
NOVICE = OverloadProfile(
    name="novice",
    max_sets=4,
    set_ramp_from_week=99,
    set_ramp_every_n_weeks=None,
    max_set_bonus=0,
    rep_bump_from_week=None,
    rest_reduction_pct_per_step=0.0,
    max_rest_reduction_pct=0.0,
    deload_min_weeks=6,
    deload_rest_multiplier=1.15,
    sections_to_bump=frozenset({"main"}),
)

DEVELOPING = OverloadProfile(
    name="developing",
    max_sets=4,
    set_ramp_from_week=4,
    set_ramp_every_n_weeks=3,
    max_set_bonus=1,
    rep_bump_from_week=None,
    rest_reduction_pct_per_step=0.05,
    max_rest_reduction_pct=0.05,
    deload_min_weeks=4,
    deload_rest_multiplier=1.20,
    sections_to_bump=frozenset({"main"}),
)

EXPERIENCED = OverloadProfile(
    name="experienced",
    max_sets=5,
    set_ramp_from_week=3,
    set_ramp_every_n_weeks=2,
    max_set_bonus=2,
    rep_bump_from_week=None,
    rest_reduction_pct_per_step=0.05,
    max_rest_reduction_pct=0.15,
    deload_min_weeks=4,
    deload_rest_multiplier=1.20,
    sections_to_bump=frozenset({"main"}),
)

DELOAD_NOTE_VI = (
    "Tuần tập nhẹ: giảm độ nặng khoảng một phần ba, tập thoải mái, không tăng."
)

_PROFILE_ORDER = (NOVICE, DEVELOPING, EXPERIENCED)


def _load_cues() -> tuple[str, str, str, str]:
    from app.services.workout_generation.coach_notes import (
        LOAD_CUE_BW_VI,
        LOAD_CUE_GYM_VI,
        LOAD_CUE_VI,
        RAMP_NOTE_VI,
    )

    return LOAD_CUE_VI, LOAD_CUE_GYM_VI, LOAD_CUE_BW_VI, RAMP_NOTE_VI


def _strip_load_notes(notes: str | None) -> str:
    text = str(notes or "")
    load_cue_vi, load_cue_gym_vi, load_cue_bw_vi, ramp_note = _load_cues()
    for cue in (load_cue_vi, load_cue_gym_vi, load_cue_bw_vi, ramp_note):
        text = text.replace(cue, "")
    text = re.sub(r"RPE\s*\d+(?:\.\d+)?", "", text, flags=re.I)
    text = re.sub(r"\s*\.\s*\.", ".", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip(" .")


def _deload_notes(notes: str | None, *, section: str) -> str | None:
    if section in MAIN_SECTIONS:
        return DELOAD_NOTE_VI
    cleaned = _strip_load_notes(notes)
    return cleaned or None


def resolve_overload_profile(
    experience_level: int | None,
    *,
    strength_tier: str | None = None,
) -> OverloadProfile:
    """Map experience level 1–5 to Novice / Developing / Experienced."""
    try:
        level = int(experience_level if experience_level is not None else 2)
    except (TypeError, ValueError):
        level = 2
    level = max(1, min(5, level))

    if level <= 2:
        profile = NOVICE
    elif level == 3:
        profile = DEVELOPING
    else:
        profile = EXPERIENCED

    if strength_tier == "weak":
        idx = _PROFILE_ORDER.index(profile)
        profile = _PROFILE_ORDER[max(0, idx - 1)]

    return profile


def periodization_advice_vi(
    profile: OverloadProfile,
    weeks: int,
    *,
    curriculum: bool = False,
    experience_level: int | None = None,
) -> str:
    if curriculum:
        from app.services.workout_generation.phase_knowledge import flags_for_phase, refs_for_phase

        labels = []
        for month in (1, 2, 3):
            refs = refs_for_phase(experience_level, month)
            if refs:
                labels.append(str(refs[0].get("label") or ""))
        extra = (" Kiến thức theo pha: " + " · ".join(x for x in labels if x) + ".") if labels else ""
        flags = [flags_for_phase(experience_level, m) for m in (1, 2, 3)]
        tech: list[str] = []
        if any(f.want_rep_ramp for f in flags):
            tech.append("tăng cái tuần chẵn trong pha overload")
        if any(f.want_set_ramp for f in flags):
            tech.append("thêm hiệp compound khi volume")
        if any(f.want_carb_cycle for f in flags):
            tech.append("carb cycling ngày tập/nghỉ")
        else:
            tech.append("không carb cycling")
        if any(f.want_refeed for f in flags):
            tech.append("refeed nếu giảm cân")
        if any(f.want_beginner_deload for f in flags):
            tech.append("tuần nhẹ người mới (không cắt calo sâu)")
        tech_txt = (" " + "; ".join(tech) + ".") if tech else ""
        load_cue_vi, _, _, _ = _load_cues()
        return (
            f"Thử thách 100 ngày ({weeks} tuần): 3 pha (tuần 1–4 / 5–8 / 9–14), "
            f"deload tuần 4/8/14; lịch tập đổi theo pha.{extra}{tech_txt} {load_cue_vi}"
        )
    load_cue_vi, _, _, _ = _load_cues()
    deload = f"; tuần cuối deload." if weeks >= profile.deload_min_weeks else "."
    if profile.name == "novice":
        return (
            f"Lịch {weeks} tuần — người mới: giữ nguyên set/rep range; "
            f"{load_cue_vi}{deload}"
        )
    if profile.name == "developing":
        return (
            f"Lịch {weeks} tuần — giữ range cố định, có thể thêm set từ tuần "
            f"{profile.set_ramp_from_week} nếu còn phục hồi. {load_cue_vi}{deload}"
        )
    return (
        f"Lịch {weeks} tuần — range cố định, thêm set mỗi {profile.set_ramp_every_n_weeks} tuần "
        f"nếu chưa chạm trần volume. {load_cue_vi}{deload}"
    )


def periodization_description_note(
    profile: OverloadProfile,
    weeks: int,
    *,
    curriculum: bool = False,
) -> str:
    if curriculum:
        return (
            f"Chu kỳ {weeks} tuần (thử thách 100 ngày; deload tuần 4/8/14; "
            "lịch tập đổi theo pha)."
        )
    tier = {"novice": "người mới", "developing": "trung cấp", "experienced": "có kinh nghiệm"}[
        profile.name
    ]
    note = f"Chu kỳ {weeks} tuần ({tier}; range cố định, tăng nhẹ khi làm hết mà vẫn dễ"
    if weeks >= profile.deload_min_weeks:
        note += ", tuần cuối deload"
    return note + ")."


def select_challenge_src_days(
    phase_entry: Any,
    *,
    local_week: int,
    is_deload: bool,
) -> list[Any]:
    """Odd local weeks + deload use week A; even weeks use week B when present."""
    if isinstance(phase_entry, dict) and ("a" in phase_entry or "b" in phase_entry):
        a = list(phase_entry.get("a") or [])
        b = list(phase_entry.get("b") or [])
        if is_deload or int(local_week) % 2 == 1:
            return a or b
        return b or a
    if isinstance(phase_entry, list):
        return phase_entry
    return []


def expand_plan_days_for_weeks(
    days: list[Any],
    duration_weeks: int,
    *,
    is_dict: bool = False,
    experience_level: int | None = None,
    strength_tier: str | None = None,
    week_templates: list[Any] | None = None,
    curriculum: bool = False,
    mesocycle_weeks: int = 4,
) -> list[Any]:
    """Clone weekly day templates across N weeks with tiered progressive overload.

    When ``curriculum`` is True (thử thách 100 ngày), use challenge phase map
    (weeks 1–4 / 5–8 / 9–14), deload on 4/8/14, and optional per-phase templates.
    """
    from app.services.workout_generation.session_policy import (
        CHALLENGE_DELOAD_WEEKS,
        CHALLENGE_WEEKS,
        challenge_local_week,
        challenge_phase_index,
    )

    weeks = max(1, min(CHALLENGE_WEEKS, int(duration_weeks or 1)))
    if weeks <= 1 or not days:
        return days

    profile = resolve_overload_profile(experience_level, strength_tier=strength_tier)
    templates = week_templates if week_templates else None
    if curriculum:
        deload_weeks = set(CHALLENGE_DELOAD_WEEKS)
        if weeks < CHALLENGE_WEEKS:
            # Shorter curriculum-like runs: deload last week of each full phase present.
            deload_weeks = {w for w in CHALLENGE_DELOAD_WEEKS if w <= weeks}
            if weeks not in deload_weeks and weeks >= profile.deload_min_weeks:
                deload_weeks.add(weeks)
    else:
        deload_weeks = {weeks} if weeks >= profile.deload_min_weeks else set()

    expanded: list[Any] = []
    sessions_per_week = len(days)

    for week in range(1, weeks + 1):
        is_deload = week in deload_weeks
        if curriculum:
            phase_idx = challenge_phase_index(week)
            month = phase_idx + 1
            local_week = challenge_local_week(week)
        else:
            phase_idx = 0
            month = None
            local_week = week

        flags = None
        if curriculum and month is not None:
            from app.services.workout_generation.phase_knowledge import flags_for_phase

            flags = flags_for_phase(experience_level, month)
        extra_rep_even = bool(flags and flags.want_rep_ramp)
        extra_set_late = bool(flags and flags.want_set_ramp)

        src_days = days
        if templates and 0 <= phase_idx < len(templates) and templates[phase_idx]:
            picked = select_challenge_src_days(
                templates[phase_idx],
                local_week=local_week,
                is_deload=is_deload,
            )
            if picked:
                src_days = picked
        sessions_per_week = len(src_days) or sessions_per_week

        for src in src_days:
            if is_dict:
                day = copy.deepcopy(src)
                base_num = int(day.get("day_number") or day.get("day_index", 0) + 1)
                day["day_number"] = (week - 1) * sessions_per_week + base_num
                title = day.get("title_vi") or day.get("label_vi") or f"Ngày {base_num}"
                title = re.sub(
                    r"^(Tháng\s+\d+\s*·\s*|Pha\s+\d+\s*·\s*)?Tuần\s+\d+(?:\s*—\s*Deload)?\s*[:：]\s*",
                    "",
                    str(title),
                )
                if curriculum and month is not None:
                    week_tag = f"Pha {month} · Tuần {week}" + (" — Deload" if is_deload else "")
                else:
                    week_tag = f"Tuần {week}" + (" — Deload" if is_deload else "")
                day["title_vi"] = f"{week_tag}: {title}"
                if "label_vi" in day:
                    day["label_vi"] = day["title_vi"]
                _bump_exercises_dict(
                    day,
                    local_week,
                    is_deload,
                    profile,
                    extra_rep_even=extra_rep_even,
                    extra_set_late=extra_set_late,
                    curriculum=curriculum,
                    global_week=week,
                    deload_weeks=deload_weeks,
                )
                expanded.append(day)
            else:
                day = src.model_copy(deep=True)
                base_num = day.day_number
                day.day_number = (week - 1) * sessions_per_week + base_num
                title = day.title_vi or f"Ngày {base_num}"
                title = re.sub(
                    r"^(Tháng\s+\d+\s*·\s*|Pha\s+\d+\s*·\s*)?Tuần\s+\d+(?:\s*—\s*Deload)?\s*[:：]\s*",
                    "",
                    str(title),
                )
                if curriculum and month is not None:
                    week_tag = f"Pha {month} · Tuần {week}" + (" — Deload" if is_deload else "")
                else:
                    week_tag = f"Tuần {week}" + (" — Deload" if is_deload else "")
                day.title_vi = f"{week_tag}: {title}"
                new_ex = []
                for ex in day.exercises:
                    e = ex.model_copy(deep=True)
                    section = getattr(ex, "section", "main") or "main"
                    e.sets, e.reps, e.rest_seconds = _adjust_load(
                        e.sets,
                        e.reps,
                        e.rest_seconds,
                        week=local_week,
                        is_deload=is_deload,
                        profile=profile,
                        section=section,
                        extra_rep_even=extra_rep_even,
                        extra_set_late=extra_set_late,
                        curriculum=curriculum,
                        global_week=week,
                        deload_weeks=deload_weeks,
                    )
                    if is_deload:
                        e.notes_vi = _deload_notes(
                            getattr(e, "notes_vi", None),
                            section=section,
                        )
                    new_ex.append(e)
                day.exercises = new_ex
                expanded.append(day)

    return expanded


def _bump_exercises_dict(
    day: dict[str, Any],
    week: int,
    is_deload: bool,
    profile: OverloadProfile,
    *,
    extra_rep_even: bool = False,
    extra_set_late: bool = False,
    curriculum: bool = False,
    global_week: int | None = None,
    deload_weeks: set[int] | None = None,
) -> None:
    for section in ("warmup", "main", "cooldown", "cardio", "exercises"):
        items = day.get(section)
        if not isinstance(items, list):
            continue
        effective_section = "main" if section == "exercises" else section
        for item in items:
            if not isinstance(item, dict):
                continue
            sets = item.get("sets")
            reps = item.get("reps")
            rest = item.get("rest_seconds")
            ns, nr, nrest = _adjust_load(
                sets,
                reps,
                rest,
                week=week,
                is_deload=is_deload,
                profile=profile,
                section=effective_section,
                extra_rep_even=extra_rep_even,
                extra_set_late=extra_set_late,
                curriculum=curriculum,
                global_week=global_week,
                deload_weeks=deload_weeks,
            )
            item["sets"] = ns
            item["reps"] = nr
            item["rest_seconds"] = nrest
            if is_deload and "notes_vi" in item:
                item["notes_vi"] = _deload_notes(item.get("notes_vi"), section=effective_section)


def _compute_set_bonus(week: int, profile: OverloadProfile, is_deload: bool) -> int:
    if is_deload or week < profile.set_ramp_from_week:
        return 0
    if profile.set_ramp_every_n_weeks is None:
        return min(profile.max_set_bonus, 1)
    if profile.set_ramp_every_n_weeks == 2:
        bonus = (week - 1) // 2
    else:
        bonus = week // profile.set_ramp_every_n_weeks
    return min(profile.max_set_bonus, bonus)


def _adjust_load(
    sets: Any,
    reps: Any,
    rest_seconds: Any,
    *,
    week: int,
    is_deload: bool,
    profile: OverloadProfile,
    section: str,
    extra_rep_even: bool = False,
    extra_set_late: bool = False,
    curriculum: bool = False,
    global_week: int | None = None,
    deload_weeks: set[int] | None = None,
) -> tuple[int, Any, int]:
    try:
        s = int(sets or 3)
    except (TypeError, ValueError):
        s = 3
    if rest_seconds is None:
        rest = 90
    else:
        try:
            rest = int(rest_seconds)
        except (TypeError, ValueError):
            rest = 90

    if section not in profile.sections_to_bump and section not in MAIN_SECTIONS:
        return s, reps, snap_rest_seconds(rest)
    if section == "exercises":
        section = "main"
    if section not in profile.sections_to_bump:
        return s, reps, snap_rest_seconds(rest)

    # 100-day curriculum: integer +1 each non-deload global week, cap at band hi.
    if curriculum:
        reps = _curriculum_working_reps(
            reps,
            global_week=int(global_week or week),
            is_deload=is_deload,
            deload_weeks=deload_weeks or set(),
        )
    elif profile.rep_bump_from_week is not None and week >= profile.rep_bump_from_week and not is_deload:
        bumps = min(3, week - profile.rep_bump_from_week + 1)
        for _ in range(bumps):
            reps = _bump_reps(reps)
    elif profile.rep_bump_from_week is not None and week >= profile.rep_bump_from_week and is_deload:
        bumps = min(3, max(0, week - profile.rep_bump_from_week))
        for _ in range(bumps):
            reps = _bump_reps(reps)

    bonus = _compute_set_bonus(week, profile, is_deload=False)
    s = min(profile.max_sets, s + bonus)
    if extra_set_late and not is_deload and week >= 3:
        s = min(profile.max_sets, s + 1)
    if (not curriculum) and extra_rep_even and not is_deload and week % 2 == 0:
        reps = _bump_reps(reps)

    if is_deload:
        if s <= 1:
            s = 1
        else:
            s = max(2, int(round(s * 0.6)))
        if rest > 0:
            rest = min(180, int(rest * profile.deload_rest_multiplier))
        return s, reps, snap_rest_seconds(rest)

    if profile.max_rest_reduction_pct > 0:
        progress = week - 1
        if profile.name == "developing":
            if week >= (profile.set_ramp_from_week or 99):
                pct = profile.max_rest_reduction_pct
            else:
                pct = 0.0
        elif progress >= 1:
            steps = min(3, progress)
            pct = min(profile.max_rest_reduction_pct, profile.rest_reduction_pct_per_step * steps)
        else:
            pct = 0.0
        if pct > 0:
            rest = max(30, int(rest * (1 - pct)))

    return s, reps, snap_rest_seconds(rest)


def _is_timed_reps(reps: Any) -> bool:
    blob = str(reps or "").strip().lower()
    return any(tok in blob for tok in ("giây", "giay", "phút", "phut", "sec", "min"))


def _parse_rep_band(reps: Any) -> tuple[int, int] | None:
    """lo/hi for working reps. Timed cardio/holds are left alone."""
    if _is_timed_reps(reps):
        return None
    text = str(reps or "").strip()
    found = re.search(r"(\d+)\s*[–\-]\s*(\d+)", text)
    if found:
        lo = int(found.group(1))
        hi = min(20, int(found.group(2)))
        return min(lo, hi), max(lo, hi)
    if isinstance(reps, int) or (isinstance(reps, str) and text.isdigit()):
        n = int(reps)
        return n, n
    return None


def _non_deload_weeks_before(global_week: int, deload_weeks: set[int]) -> int:
    return sum(1 for w in range(1, max(1, int(global_week))) if w not in deload_weeks)


def _curriculum_working_reps(
    reps: Any,
    *,
    global_week: int,
    is_deload: bool,
    deload_weeks: set[int],
) -> Any:
    band = _parse_rep_band(reps)
    if band is None:
        return reps
    lo, hi = band
    out = lo if is_deload else min(hi, lo + _non_deload_weeks_before(global_week, deload_weeks))
    if isinstance(reps, str) and not str(reps).strip().isdigit():
        return str(out)
    if isinstance(reps, str):
        return str(out)
    return out


def _bump_reps(reps: Any) -> Any:
    """Bump integer reps or the top of a '8-12' range by 1, cap 20."""
    if isinstance(reps, int) or (isinstance(reps, str) and str(reps).isdigit()):
        try:
            r = int(reps)
            r = min(20, r + 1)
            return r if not isinstance(reps, str) else str(r)
        except (TypeError, ValueError):
            pass
    text = str(reps or "").strip()
    found = re.search(r"(\d+)\s*[–\-]\s*(\d+)", text)
    if found:
        lo = int(found.group(1))
        hi = min(20, int(found.group(2)) + 1)
        lo = min(lo, hi)
        return f"{lo}-{hi}"
    return reps
