"""Mesocycle phase metadata and RPE tweaks for the 100-day challenge."""

from __future__ import annotations

import re
from typing import Any

from app.schemas.plans import PlanDayIn, PlanExerciseIn
from app.services.exercise_muscle_region import CORE_SLUGS
from app.services.workout_generation.coach_notes import (
    FALLBACK_WORKING_NOTE_VI,
    FOCUS_PHASE_TIP_VI,
)
from app.services.workout_rest import snap_rest_seconds
from app.services.workout_generation.session_policy import (
    CHALLENGE_DELOAD_WEEKS,
    CHALLENGE_PHASE_RANGES,
    CHALLENGE_WEEKS,
)


MESOCYCLE_PHASES: tuple[dict[str, Any], ...] = (
    {
        "key": "accumulation",
        "label_vi": "Nền tảng",
        "blurb_vi": "Học lịch, làm đẹp kỹ thuật; tuần 4 tập nhẹ.",
        "rpe_vi": "Ưu tiên form",
    },
    {
        "key": "intensification",
        "label_vi": "Ổn định",
        "blurb_vi": "Giữ số buổi, ăn và ngủ cho đều; tuần 8 tập nhẹ.",
        "rpe_vi": "Tăng sức vừa phải",
    },
    {
        "key": "specialization",
        "label_vi": "Bám tiến bộ",
        "blurb_vi": "Tăng cái khi kỹ thuật còn đẹp; tuần 14 xả tải.",
        "rpe_vi": "Ưu tiên nhóm mục tiêu",
    },
)

# Legacy RIR / tạ sentences — strip if still on a template, never re-append.
_OLD_RPE_CUES = (
    "Ưu tiên kỹ thuật: dừng khi cảm thấy còn làm thêm được 3–4 cái.",
    "Tăng sức vừa phải: dừng khi cảm thấy còn làm thêm được 2–3 cái.",
    "Ưu tiên nhóm mục tiêu; tăng tạ khi làm đủ số cái cao nhất với form đẹp.",
    "Ưu tiên nhóm mục tiêu pha 3.",
)


def _strip_rpe_notes(notes: str | None) -> str:
    text = str(notes or "")
    for cue in _OLD_RPE_CUES:
        text = text.replace(cue, "")
    text = re.sub(r"RPE\s*\d+(?:[.,]\d+)?(?:\s*[–-]\s*\d+(?:[.,]\d+)?)?", "", text)
    text = " ".join(text.split())
    return text.strip(" .")


def _phase_notes(notes: str | None) -> str:
    return _strip_rpe_notes(notes) or FALLBACK_WORKING_NOTE_VI


def _is_main(ex: PlanExerciseIn) -> bool:
    return (ex.section or "main") in {"main", "exercises"}


def _muscle_slug(ex: PlanExerciseIn, meta_by_id: dict[int, Any]) -> str:
    meta = meta_by_id.get(int(ex.exercise_id))
    if meta is None:
        return ""
    if isinstance(meta, dict):
        return str(meta.get("muscle_slug") or "").strip().lower()
    return str(getattr(meta, "muscle_slug", "") or "").strip().lower()


def _matches_focus(ex: PlanExerciseIn, meta_by_id: dict[int, Any], focus: set[str]) -> bool:
    if not focus:
        return False
    slug = _muscle_slug(ex, meta_by_id)
    return bool(slug and slug in focus)


def _is_strength_main(ex: PlanExerciseIn) -> bool:
    return (ex.section or "main") in {"main", "exercises"}


def _is_core_main(ex: PlanExerciseIn, meta_by_id: dict[int, Any]) -> bool:
    slug = _muscle_slug(ex, meta_by_id)
    return slug in CORE_SLUGS or slug in {"bung", "core"}


def _intensify_day(day: PlanDayIn) -> PlanDayIn:
    new_ex: list[PlanExerciseIn] = []
    for ex in day.exercises:
        e = ex.model_copy(deep=True)
        if _is_main(e):
            e.notes_vi = _phase_notes(e.notes_vi)
            try:
                rest = int(e.rest_seconds or 90)
            except (TypeError, ValueError):
                rest = 90
            e.rest_seconds = snap_rest_seconds(max(45, int(rest * 0.95)))
            try:
                s = int(e.sets or 3)
            except (TypeError, ValueError):
                s = 3
            e.sets = min(4, s + (1 if s < 4 else 0))
        new_ex.append(e)
    return day.model_copy(update={"exercises": new_ex})


def _specialize_day(
    day: PlanDayIn,
    *,
    meta_by_id: dict[int, Any],
    focus_slugs: set[str],
    experience_level: int | None,
) -> PlanDayIn:
    cap = 4 if int(experience_level or 2) <= 1 else 5
    core_is_focus = bool(focus_slugs & CORE_SLUGS) or "bung" in focus_slugs
    new_ex: list[PlanExerciseIn] = []
    for ex in day.exercises:
        e = ex.model_copy(deep=True)
        if not _is_strength_main(e):
            new_ex.append(e)
            continue
        e.notes_vi = _phase_notes(e.notes_vi)
        if _is_core_main(e, meta_by_id) and not core_is_focus:
            new_ex.append(e)
            continue
        try:
            s = int(e.sets or 3)
        except (TypeError, ValueError):
            s = 3
        if focus_slugs and _matches_focus(e, meta_by_id, focus_slugs):
            e.sets = min(cap, s + 1)
            if FOCUS_PHASE_TIP_VI not in str(e.notes_vi or ""):
                e.notes_vi = f"{e.notes_vi} {FOCUS_PHASE_TIP_VI}".strip()
        elif focus_slugs:
            e.sets = max(2, s - 1)
        new_ex.append(e)
    return day.model_copy(update={"exercises": new_ex})


def _accumulate_day(day: PlanDayIn) -> PlanDayIn:
    new_ex: list[PlanExerciseIn] = []
    for ex in day.exercises:
        e = ex.model_copy(deep=True)
        if _is_main(e):
            e.notes_vi = _phase_notes(e.notes_vi)
        new_ex.append(e)
    return day.model_copy(update={"exercises": new_ex})


def curriculum_insight_payload(
    *,
    rationale_vi: list[str] | None = None,
    blurb_vi: list[str] | None = None,
    label_vi: list[str] | None = None,
    knowledge_refs: list[list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Insights payload for thử thách 100 ngày (kept name for service callers)."""
    reasons = list(rationale_vi or [])
    blurbs = list(blurb_vi or [])
    labels = list(label_vi or [])
    refs = list(knowledge_refs or [])
    mesocycles = []
    for i, (phase, (lo, hi)) in enumerate(zip(MESOCYCLE_PHASES, CHALLENGE_PHASE_RANGES)):
        item = {
            "month": i + 1,
            "weeks": list(range(lo, hi + 1)),
            "deload_week": CHALLENGE_DELOAD_WEEKS[i],
            **{k: v for k, v in phase.items() if k in {"key", "label_vi", "blurb_vi", "rpe_vi"}},
        }
        if i < len(labels) and str(labels[i] or "").strip():
            item["label_vi"] = str(labels[i]).strip()
        if i < len(blurbs) and str(blurbs[i] or "").strip():
            item["blurb_vi"] = str(blurbs[i]).strip()
        if i < len(reasons) and str(reasons[i] or "").strip():
            item["rationale_vi"] = str(reasons[i]).strip()
        if i < len(refs) and refs[i]:
            item["knowledge_refs"] = [
                {"slug": str(r.get("slug") or ""), "label": str(r.get("label") or "")}
                for r in refs[i]
                if str(r.get("slug") or "").strip()
            ]
        mesocycles.append(item)
    return {
        "mesocycles": mesocycles,
        "deload_weeks": list(CHALLENGE_DELOAD_WEEKS),
        "duration_weeks": CHALLENGE_WEEKS,
    }


def apply_phase_rpe(
    days: list[PlanDayIn],
    phase_index: int,
    *,
    meta_by_id: dict[int, dict[str, Any]] | None = None,
    focus_slugs: set[str] | frozenset[str] | None = None,
    experience_level: int | None = None,
) -> list[PlanDayIn]:
    """Apply accumulation / intensification / specialization set/rest tweaks to a week."""
    meta = meta_by_id if meta_by_id is not None else {}
    focus = {str(s).strip().lower() for s in (focus_slugs or set()) if str(s).strip()}
    idx = max(0, min(2, int(phase_index)))
    level = int(experience_level or 2)
    if idx <= 0:
        return [_accumulate_day(d) for d in days]
    if idx == 1:
        if level <= 1:
            return [_accumulate_day(d) for d in days]
        return [_intensify_day(d) for d in days]
    return [
        _specialize_day(
            d, meta_by_id=meta, focus_slugs=focus, experience_level=level
        )
        for d in days
    ]
