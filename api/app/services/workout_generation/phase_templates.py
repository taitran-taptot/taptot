"""Mesocycle phase metadata and RPE tweaks for the 100-day challenge."""

from __future__ import annotations

import re
from typing import Any

from app.schemas.plans import PlanDayIn, PlanExerciseIn
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
        "blurb_vi": "Volume ổn định, ưu tiên form và phục hồi.",
        "rpe_vi": "Ưu tiên form",
    },
    {
        "key": "intensification",
        "label_vi": "Tăng áp lực",
        "blurb_vi": "Intensity cao hơn; giữ volume, nghỉ ngắn hơn một chút.",
        "rpe_vi": "Tăng sức vừa phải",
    },
    {
        "key": "specialization",
        "label_vi": "Tinh chỉnh",
        "blurb_vi": "Nhấn nhóm cơ ưu tiên / mục tiêu phụ.",
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


def _matches_focus(ex: PlanExerciseIn, meta_by_id: dict[int, dict[str, Any]], focus: set[str]) -> bool:
    if not focus:
        return False
    meta = meta_by_id.get(int(ex.exercise_id)) or {}
    slug = str(meta.get("muscle_slug") or "").strip().lower()
    return bool(slug and slug in focus)


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
    meta_by_id: dict[int, dict[str, Any]],
    focus_slugs: set[str],
) -> PlanDayIn:
    new_ex: list[PlanExerciseIn] = []
    for ex in day.exercises:
        e = ex.model_copy(deep=True)
        if _is_main(e):
            e.notes_vi = _phase_notes(e.notes_vi)
            if _matches_focus(e, meta_by_id, focus_slugs):
                try:
                    s = int(e.sets or 3)
                except (TypeError, ValueError):
                    s = 3
                e.sets = min(5, s + 1)
                if FOCUS_PHASE_TIP_VI not in str(e.notes_vi or ""):
                    e.notes_vi = f"{e.notes_vi} {FOCUS_PHASE_TIP_VI}".strip()
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


def curriculum_insight_payload(*, rationale_vi: list[str] | None = None) -> dict[str, Any]:
    """Insights payload for thử thách 100 ngày (kept name for service callers)."""
    reasons = list(rationale_vi or [])
    mesocycles = []
    for i, (phase, (lo, hi)) in enumerate(zip(MESOCYCLE_PHASES, CHALLENGE_PHASE_RANGES)):
        item = {
            "month": i + 1,
            "weeks": list(range(lo, hi + 1)),
            "deload_week": CHALLENGE_DELOAD_WEEKS[i],
            **{k: v for k, v in phase.items() if k in {"key", "label_vi", "blurb_vi", "rpe_vi"}},
        }
        if i < len(reasons) and str(reasons[i] or "").strip():
            item["rationale_vi"] = str(reasons[i]).strip()
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
) -> list[PlanDayIn]:
    """Apply accumulation / intensification / specialization set/rest tweaks to a week."""
    meta = meta_by_id if meta_by_id is not None else {}
    focus = {str(s).strip().lower() for s in (focus_slugs or set()) if str(s).strip()}
    idx = max(0, min(2, int(phase_index)))
    if idx <= 0:
        return [_accumulate_day(d) for d in days]
    if idx == 1:
        return [_intensify_day(d) for d in days]
    return [_specialize_day(d, meta_by_id=meta, focus_slugs=focus) for d in days]
