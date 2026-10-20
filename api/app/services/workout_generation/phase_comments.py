"""Learner-facing 100-day phase copy (no OpenAI, no internal playbook dump)."""

from __future__ import annotations

from typing import Any

from app.services.exercise_prescription import clamp_experience_level
from app.services.workout_generation.phase_knowledge import refs_for_challenge_phases_ui
from app.services.workout_generation.session_policy import CHALLENGE_DELOAD_WEEKS
from app.services.workout_generation.wizard_inputs import format_challenge_100_days_label

_ACTIVITY_JOB = {
    "sedentary": "ngày thường ngồi nhiều",
    "light": "ngày thường đứng hoặc đi nhẹ",
    "moderate": "ngày thường đi lại nhiều",
    "active": "ngày thường lao động chân tay",
    "very_active": "ngày thường lao động nặng",
}

_PHASE_LABEL = ("Nền tảng", "Ổn định", "Bám tiến bộ")
_PHASE_WEEKS = ("Tuần 1–4", "Tuần 5–8", "Tuần 9–14")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _level(wizard: dict[str, Any]) -> int:
    return int(clamp_experience_level(wizard.get("experience_level")))


def _goal(wizard: dict[str, Any]) -> str:
    return _text(wizard.get("goal")).lower()


def _activity(wizard: dict[str, Any]) -> str:
    a = _text(wizard.get("activity")).lower()
    return a if a in _ACTIVITY_JOB else "moderate"


def _schedule(wizard: dict[str, Any]) -> str:
    sessions = wizard.get("sessions_per_week")
    minutes = wizard.get("session_minutes")
    try:
        s = int(sessions)
    except (TypeError, ValueError):
        s = 0
    try:
        m = int(minutes)
    except (TypeError, ValueError):
        m = 0
    if s and m:
        return f"{s} buổi mỗi tuần, khoảng {m} phút"
    if s:
        return f"{s} buổi mỗi tuần"
    if m:
        return f"khoảng {m} phút mỗi buổi"
    return "lịch trên app"


def _place(wizard: dict[str, Any]) -> str:
    loc = _text(wizard.get("location")).lower()
    kit = _text(wizard.get("equipment_vi"))
    if loc == "home":
        return f"{kit} ở nhà" if kit else "tập ở nhà"
    loc_vi = _text(wizard.get("location_vi"))
    return loc_vi.lower() if loc_vi else "phòng gym"


def _goal_phrase(wizard: dict[str, Any]) -> str:
    g = _goal(wizard)
    label = None
    if g in {"lose_weight", "gain_weight"} and wizard.get("kg_per_week") is not None:
        try:
            label = format_challenge_100_days_label(g, float(wizard["kg_per_week"]))
        except (TypeError, ValueError):
            label = None
    if label:
        return label[0].lower() + label[1:]
    if g == "lose_weight":
        return "giảm cân"
    if g in {"gain_weight", "gain_muscle"}:
        return "tăng cân"
    return "giữ cân"


def _focus_phrase(wizard: dict[str, Any]) -> str | None:
    labels = [str(x).strip() for x in (wizard.get("focus_vi") or []) if str(x).strip()]
    if not labels:
        return None
    return ", ".join(labels).lower()


def _blurb(phase_i: int, wizard: dict[str, Any]) -> str:
    deload = CHALLENGE_DELOAD_WEEKS[phase_i]
    if phase_i == 0:
        return f"Làm quen động tác trên lịch {_schedule(wizard)}. Tuần {deload} nhẹ."
    if phase_i == 1:
        return f"Tăng sức vừa phải, giữ đúng số buổi. Tuần {deload} nhẹ."
    focus = _focus_phrase(wizard)
    extra = f" nhấn {focus}," if focus else ""
    return f"Tập trung nhóm muốn,{extra} tuần {deload} nhẹ."


def _rationale_p1(wizard: dict[str, Any], *, level: int) -> str:
    _ = level
    job = _ACTIVITY_JOB[_activity(wizard)]
    return (
        f"{_PHASE_WEEKS[0]} bạn làm quen động tác: {_schedule(wizard)}, {_place(wizard)}, "
        f"hướng tới {_goal_phrase(wizard)}. Đọc lịch, làm đúng kỹ thuật, đừng tăng tạ cho oai. "
        f"Vì {job}, khởi động cho hết rồi mới vào bài chính. "
        f"Tuần {CHALLENGE_DELOAD_WEEKS[0]} vẫn đi tập, chỉ nhẹ hơn."
    )


def _rationale_p2(wizard: dict[str, Any], *, level: int) -> str:
    _ = level
    return (
        f"{_PHASE_WEEKS[1]} khung buổi đã quen — lúc này tăng sức vừa phải, giữ {_schedule(wizard)}, "
        f"không tự đổi lịch. Ăn và ngủ cho đều, bám {_goal_phrase(wizard)}. "
        f"Tuần {CHALLENGE_DELOAD_WEEKS[1]} nhẹ một nhịp, vẫn đi đủ buổi."
    )


def _rationale_p3(wizard: dict[str, Any], *, level: int) -> str:
    _ = level
    focus = _focus_phrase(wizard)
    focus_s = (
        f"nhóm {focus} được thêm một hiệp, bài khác bớt một hiệp (không xuống dưới hai)."
        if focus
        else "giữ đủ các nhóm trên lịch, đừng chỉ tập bài mình thích."
    )
    return (
        f"{_PHASE_WEEKS[2]} tập trung vào nhóm cơ bạn muốn: {focus_s} "
        f"Mục tiêu {_goal_phrase(wizard)} vẫn đi cùng ăn trên lịch. "
        f"Tuần {CHALLENGE_DELOAD_WEEKS[2]} tập nhẹ, không tự thêm bài."
    )


_BUILDERS = (_rationale_p1, _rationale_p2, _rationale_p3)


def challenge_phase_copy(wizard: dict[str, Any] | None) -> list[dict[str, Any]]:
    w = dict(wizard or {})
    level = _level(w)
    goal = _goal(w) or None
    activity = _activity(w)
    reading = refs_for_challenge_phases_ui(level, goal=goal, activity=activity)
    rows: list[dict[str, Any]] = []
    for i, builder in enumerate(_BUILDERS):
        text = " ".join(builder(w, level=level).split())
        rows.append(
            {
                "label_vi": _PHASE_LABEL[i],
                "blurb_vi": _blurb(i, w),
                "rationale_vi": text,
                "knowledge_refs": reading[i],
            }
        )
    return rows
