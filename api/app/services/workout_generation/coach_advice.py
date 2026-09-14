"""OpenAI coach advice from user profile + assembled schedule summary."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from app.core.config import get_settings
from app.services.workout_generation.session_duration import (
    estimate_day_minutes,
    parse_reps_minutes,
    parse_reps_seconds,
)

logger = logging.getLogger(__name__)

GOAL_VI = {
    "lose_weight": "Giảm cân",
    "maintain": "Giữ cân",
    "gain_weight": "Tăng cân",
    "gain_muscle": "Tăng cơ",
}

EXTRA_GOAL_VI = {
    "endurance": "Sức bền",
    "flexibility": "Dẻo dai",
    "strength": "Sức mạnh",
    "muscle": "Tăng cơ",
    "fat_loss": "Giảm mỡ",
    "physique": "Cải thiện vóc dáng",
    "mental_health": "Sức khỏe tinh thần",
    "heartbreak_recovery": "Phục hồi sau thất tình",
}

FALLBACK_ADVICE = [
    "Khởi động kỹ trước working sets; tăng dần mức tạ nếu dùng tạ.",
    "Giữ form đúng; giảm tạ hoặc đổi biến thể dễ hơn nếu form vỡ.",
    "Ngủ đủ và ăn đủ protein để phục hồi giữa các buổi.",
]

_ALLOWED_REST = frozenset({60, 90, 120, 180})
_ALLOWED_SETS = frozenset({2, 3, 4, 5})


def build_schedule_summary(
    frame: Any,
    plan_days: list[Any],
    *,
    session_minutes: int,
    location: str,
) -> dict[str, Any]:
    days_out = []
    for day in plan_days:
        exs = []
        for ex in getattr(day, "exercises", []) or []:
            exs.append(
                {
                    "exercise_id": ex.exercise_id,
                    "sets": ex.sets,
                    "reps": ex.reps,
                    "rest_seconds": getattr(ex, "rest_seconds", None),
                    "section": ex.section,
                }
            )
        days_out.append(
            {
                "day_number": day.day_number,
                "title_vi": day.title_vi,
                "split_role": day.split_role,
                "estimate_min": int(estimate_day_minutes(day)),
                "exercises": exs,
            }
        )
    return {
        "frame_code": getattr(frame, "code", ""),
        "frame_name_vi": getattr(frame, "name_vi", ""),
        "week_code": getattr(frame, "week_code", ""),
        "session_minutes": session_minutes,
        "location": location,
        "days": days_out,
    }


def _profile_for_prompt(payload: dict[str, Any]) -> dict[str, Any]:
    baseline = payload.get("fitness_baseline") or {}
    if hasattr(baseline, "model_dump"):
        baseline = baseline.model_dump()
    extra = payload.get("extra_goals") or []
    return {
        "goal": payload.get("goal"),
        "goal_vi": GOAL_VI.get(str(payload.get("goal") or ""), payload.get("goal")),
        "extra_goals": extra,
        "extra_goals_vi": [EXTRA_GOAL_VI.get(str(x), x) for x in extra],
        "focus_areas": payload.get("focus_areas") or [],
        "gender": payload.get("gender"),
        "age": payload.get("age"),
        "experience_level": payload.get("experience_level"),
        "sessions_per_week": payload.get("sessions_per_week"),
        "session_minutes": payload.get("session_minutes"),
        "location": payload.get("location"),
        "health_note": payload.get("health_note"),
        "fitness_baseline": baseline,
        "no_equipment": payload.get("no_equipment"),
        "equipment_list": list(payload.get("equipment_list") or []),
        "duration_weeks": payload.get("duration_weeks"),
    }


def generate_coach_advice(
    payload: dict[str, Any],
    schedule_summary: dict[str, Any],
    *,
    exercise_names: dict[int, str] | None = None,
) -> dict[str, Any]:
    """
    Return {advice_vi, summary_vi, week_notes_vi, used_openai}.
    Does not mutate schedule.
    """
    settings = get_settings()
    if not settings.workout_gen_coach_advice:
        return {
            "advice_vi": list(FALLBACK_ADVICE),
            "summary_vi": None,
            "week_notes_vi": None,
            "used_openai": False,
            "swaps": [],
            "duration_tweaks": [],
        }
    if not (settings.openai_api_key or "").strip():
        return {
            "advice_vi": list(FALLBACK_ADVICE),
            "summary_vi": None,
            "week_notes_vi": None,
            "used_openai": False,
            "swaps": [],
            "duration_tweaks": [],
        }

    summary = dict(schedule_summary)
    if exercise_names:
        for day in summary.get("days") or []:
            for ex in day.get("exercises") or []:
                eid = ex.get("exercise_id")
                if eid in exercise_names:
                    ex["name_vi"] = exercise_names[eid]

    user_payload = {
        "profile": _profile_for_prompt(payload),
        "schedule": summary,
    }

    system = (
        "Bạn là huấn luyện viên thể hình Việt Nam. Số bài mỗi buổi đã cố định; "
        "KHÔNG thêm/bớt bài, KHÔNG đổi số buổi, KHÔNG đổi id bài, KHÔNG bịa kcal. "
        "Mỗi ngày có estimate_min. Nếu estimate_min > session_minutes hoặc "
        "< 0.9*session_minutes, chỉnh sets/rest/phút cardio qua duration_tweaks. "
        "rest_seconds chỉ 60, 90, 120 hoặc 180. sets chỉ 2–5. "
        "reps cardio continuous dạng '8 phút'; interval home BW dạng '45 giây'. "
        "Viết 3 câu lời khuyên an toàn. Trả JSON: "
        '{"advice_vi":["..."],"summary_vi":"...","week_notes_vi":"...",'
        '"swaps":[],'
        '"duration_tweaks":[{"day_number":1,"exercise_id":10,"sets":3,'
        '"rest_seconds":90,"reps":null}]} '
        "swaps phải luôn []. duration_tweaks có thể []. advice_vi: đúng 3 câu ngắn."
    )
    user = json.dumps(user_payload, ensure_ascii=False)

    max_out = min(2048, int(settings.openai_max_tokens or 2048))
    body = {
        "model": settings.openai_model,
        "temperature": min(0.5, float(settings.openai_temperature or 0.4)),
        "max_completion_tokens": max_out,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    url = settings.openai_base_url.rstrip("/") + "/chat/completions"
    timeout = min(45, int(settings.openai_timeout_seconds or 45))

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        advice = parsed.get("advice_vi") or []
        if not isinstance(advice, list):
            advice = [str(advice)]
        advice = [str(a).strip() for a in advice if str(a).strip()]
        if not advice:
            advice = list(FALLBACK_ADVICE)
        duration_tweaks = parsed.get("duration_tweaks") or []
        if not isinstance(duration_tweaks, list):
            duration_tweaks = []
        clean_tweaks = []
        for raw in duration_tweaks:
            if not isinstance(raw, dict):
                continue
            try:
                item: dict[str, Any] = {
                    "day_number": int(raw.get("day_number")),
                    "exercise_id": int(raw.get("exercise_id")),
                }
            except (TypeError, ValueError):
                continue
            if raw.get("sets") is not None:
                try:
                    sets = int(raw.get("sets"))
                except (TypeError, ValueError):
                    sets = None
                else:
                    if sets in _ALLOWED_SETS:
                        item["sets"] = sets
            if raw.get("rest_seconds") is not None:
                try:
                    rest = int(raw.get("rest_seconds"))
                except (TypeError, ValueError):
                    rest = None
                else:
                    if rest in _ALLOWED_REST:
                        item["rest_seconds"] = rest
            reps = raw.get("reps")
            if isinstance(reps, str):
                if parse_reps_minutes(reps) is not None:
                    item["reps"] = f"{parse_reps_minutes(reps)} phút"
                elif parse_reps_seconds(reps) is not None:
                    item["reps"] = f"{parse_reps_seconds(reps)} giây"
            if len(item) > 2:
                clean_tweaks.append(item)
        return {
            "advice_vi": advice[:8],
            "summary_vi": (parsed.get("summary_vi") or "").strip() or None,
            "week_notes_vi": (parsed.get("week_notes_vi") or "").strip() or None,
            "used_openai": True,
            "swaps": [],
            "duration_tweaks": clean_tweaks,
        }
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        KeyError,
        IndexError,
        json.JSONDecodeError,
        ValueError,
        TimeoutError,
    ) as exc:
        logger.warning("Coach advice OpenAI failed: %s", exc)
        return {
            "advice_vi": list(FALLBACK_ADVICE),
            "summary_vi": None,
            "week_notes_vi": None,
            "used_openai": False,
            "swaps": [],
            "duration_tweaks": [],
        }


def apply_schedule_swaps(
    plan_days: list[Any],
    swaps: list[dict[str, Any]] | None,
    allowed_ids_by_day: dict[int, set[int]],
) -> list[Any]:
    """Replace exercise ids when to_id is on that day's shortlist. Same slot count."""
    for swap in swaps or []:
        try:
            day_n = int(swap.get("day_number"))
            from_id = int(swap.get("from_id"))
            to_id = int(swap.get("to_id"))
        except (TypeError, ValueError, AttributeError):
            continue
        allowed = allowed_ids_by_day.get(day_n) or set()
        if to_id not in allowed or to_id == from_id:
            continue
        for day in plan_days:
            if int(getattr(day, "day_number", 0) or 0) != day_n:
                continue
            used = {int(ex.exercise_id) for ex in day.exercises}
            if to_id in used:
                continue
            for ex in day.exercises:
                if int(ex.exercise_id) == from_id:
                    ex.exercise_id = to_id
                    break
    return plan_days


def apply_duration_tweaks(
    plan_days: list[Any],
    tweaks: list[dict[str, Any]] | None,
    allowed_ids_by_day: dict[int, set[int]] | None = None,
) -> list[Any]:
    """Apply validated set/rest/cardio-minute tweaks. Ignores unknown ids."""
    for raw in tweaks or []:
        try:
            day_n = int(raw.get("day_number"))
            eid = int(raw.get("exercise_id"))
        except (TypeError, ValueError, AttributeError):
            continue
        allowed = (allowed_ids_by_day or {}).get(day_n)
        for day in plan_days:
            if int(getattr(day, "day_number", 0) or 0) != day_n:
                continue
            for ex in day.exercises:
                if int(ex.exercise_id) != eid:
                    continue
                if allowed is not None and eid not in allowed and (ex.section or "") == "main":
                    # Already on the day — tweaking sets/rest of a picked lift is OK.
                    pass
                if raw.get("sets") is not None:
                    try:
                        sets = int(raw["sets"])
                    except (TypeError, ValueError):
                        sets = None
                    else:
                        if sets in _ALLOWED_SETS:
                            ex.sets = sets
                if raw.get("rest_seconds") is not None:
                    try:
                        rest = int(raw["rest_seconds"])
                    except (TypeError, ValueError):
                        rest = None
                    else:
                        if rest in _ALLOWED_REST:
                            ex.rest_seconds = rest
                reps = raw.get("reps")
                if isinstance(reps, str):
                    if parse_reps_minutes(reps) is not None:
                        # Continuous cardio only — do not rewrite interval (giây) pieces.
                        if parse_reps_minutes(ex.reps) is not None:
                            ex.reps = f"{parse_reps_minutes(reps)} phút"
                    elif parse_reps_seconds(reps) is not None and parse_reps_seconds(
                        ex.reps
                    ) is not None:
                        ex.reps = reps
                break
    return plan_days
