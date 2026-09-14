"""Build structured plan insights for the AI knowledge toggle."""

from __future__ import annotations

from typing import Any

from app.services.plan_notes import sanitize_advice, sanitize_meal_notes, sanitize_section_notes
from app.services.periodization import periodization_advice_vi, resolve_overload_profile

SPLIT_ROLE_VI: dict[str, str] = {
    "fb": "Toàn thân",
    "fb_a": "Toàn thân A",
    "fb_b": "Toàn thân B",
    "upper": "Thân trên",
    "lower": "Thân dưới",
    "push": "Đẩy (ngực – vai – tay sau)",
    "pull": "Kéo (lưng – tay trước)",
    "legs": "Chân",
    "chest": "Ngực",
    "back": "Lưng",
    "shoulders": "Vai",
    "arms": "Tay",
    "quads": "Đùi trước",
    "posterior": "Chuỗi sau",
    "anterior": "Chuỗi trước",
    "weak": "Điểm yếu",
    "conditioning": "Cardio / đốt mỡ nhẹ",
    "recovery": "Phục hồi / giãn cơ",
    "power": "Sức mạnh",
    "hypertrophy": "Tăng cơ",
}

MEAL_TYPE_VI: dict[str, str] = {
    "breakfast": "Bữa sáng",
    "lunch": "Bữa trưa",
    "dinner": "Bữa tối",
    "snack": "Bữa phụ",
}


def _split_label(role: str | None) -> str:
    if not role:
        return "Tập luyện"
    return SPLIT_ROLE_VI.get(str(role).lower(), str(role))


def _clamp_why(text: Any, *, max_len: int = 120) -> str | None:
    if text is None:
        return None
    s = str(text).strip()
    if not s:
        return None
    return s[:max_len]


def _build_schedule_vi(output: dict[str, Any], params: dict[str, Any]) -> str | None:
    try:
        sessions = int(params.get("sessions_per_week") or 0)
    except (TypeError, ValueError):
        sessions = 0
    if sessions <= 0:
        days = output.get("days") or []
        sessions = len(days) if isinstance(days, list) else 0
    if sessions <= 0:
        return None

    split_name = (
        output.get("split_name_vi")
        or (output.get("assigned_split") or {}).get("name_vi")
        or params.get("split_name_vi")
    )
    roles: list[str] = []
    for raw in output.get("days") or []:
        if not isinstance(raw, dict):
            continue
        role = raw.get("split_role")
        if role:
            label = _split_label(str(role))
            if label not in roles:
                roles.append(label)

    parts = [
        f"{sessions} buổi/tuần: xen kẽ các nhóm cơ để cơ có 1–2 ngày phục hồi giữa các buổi nặng."
    ]
    if split_name:
        parts.append(f"Chia lịch theo {split_name}.")
    reason = output.get("split_reason_vi") or params.get("split_reason_vi")
    if reason:
        parts.append(str(reason))
    if roles:
        parts.append(f"Các buổi: {', '.join(roles[:5])}.")
    if any(str(d.get("split_role") or "").lower() == "recovery" for d in (output.get("days") or []) if isinstance(d, dict)):
        parts.append("Ngày recovery giữ bài nhẹ, tránh tập cùng nhóm liên tiếp.")
    return " ".join(parts)


def _build_nutrition_vi(params: dict[str, Any]) -> str | None:
    nut = params.get("nutrition") or {}
    try:
        tdee = int(nut.get("tdee") or 0)
    except (TypeError, ValueError):
        tdee = 0
    try:
        target = int(nut.get("target_calories") or params.get("target_calories") or 0)
    except (TypeError, ValueError):
        target = 0
    if tdee <= 0 and target <= 0:
        return None

    goal_vi = nut.get("goal_vi") or params.get("goal") or "mục tiêu của bạn"
    if tdee <= 0:
        tdee = target

    delta = target - tdee
    base = f"TDEE (~{tdee:,} kcal) là lượng calo ước tính để giữ cân với mức vận động của bạn.".replace(",", ".")
    if abs(delta) < 50:
        return (
            f"{base} Mục tiêu {goal_vi} → ~{target:,} kcal trung bình/ngày (gần mức duy trì). "
            "Calo thay đổi theo ngày tập và ngày nghỉ."
        ).replace(",", ".")
    if delta < 0:
        return (
            f"{base} Mục tiêu {goal_vi} → ~{target:,} kcal trung bình/ngày "
            f"(thiếu ~{abs(delta):,} kcal) để giảm mỡ từ từ. "
            "Ngày tập strength cao hơn, ngày nghỉ thấp hơn."
        ).replace(",", ".")
    return (
        f"{base} Mục tiêu {goal_vi} → ~{target:,} kcal trung bình/ngày "
        f"(dư ~{delta:,} kcal) để tăng cân/tăng cơ. "
        "Ngày tập strength cao hơn, ngày nghỉ thấp hơn."
    ).replace(",", ".")


def _build_periodization_vi(output: dict[str, Any], params: dict[str, Any]) -> str | None:
    try:
        weeks = int(output.get("duration_weeks") or params.get("duration_weeks") or 1)
    except (TypeError, ValueError):
        weeks = 1
    if weeks <= 1:
        return None
    try:
        level = int(params.get("experience_level") or 2)
    except (TypeError, ValueError):
        level = 2
    profile = resolve_overload_profile(level, strength_tier=params.get("strength_tier"))
    return periodization_advice_vi(profile, weeks)


def _exercise_why_fallback(item: dict[str, Any], *, split_role: str | None, catalog_by_id: dict[str, dict]) -> str:
    ex_id = str(item.get("exercise_id") or "")
    cat = catalog_by_id.get(ex_id) or {}
    name = item.get("name_vi") or cat.get("name_vi") or "Bài tập"
    body = item.get("body_part") or cat.get("body_part") or "nhóm cơ phù hợp"
    sets = item.get("sets") or 3
    reps = item.get("reps") or 12
    role = _split_label(split_role)
    return f"{name} — tập {body}, {sets}×{reps} phù hợp buổi {role}."


def _meal_why_fallback(item: dict[str, Any], *, target_cal: int | None) -> str:
    name = item.get("name_vi") or "Món ăn"
    meal_type = MEAL_TYPE_VI.get(str(item.get("meal_type") or "lunch"), "Bữa ăn")
    cal = item.get("calories")
    cal_txt = f", ~{cal} kcal" if cal else ""
    target_txt = f" góp phần đạt ~{target_cal} kcal/ngày" if target_cal else ""
    return f"{name} cho {meal_type.lower()}{cal_txt}{target_txt}."


def build_plan_insights(output: dict[str, Any], params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return JSON-serializable insights for PlanInsightsOut."""
    params = params or {}
    catalog = params.get("exercises_catalog") or output.get("exercises_catalog") or []
    catalog_by_id = {str(c.get("exercise_id")): c for c in catalog if isinstance(c, dict)}

    nut = params.get("nutrition") or {}
    try:
        target_cal = int(nut.get("target_calories") or params.get("target_calories") or 0) or None
    except (TypeError, ValueError):
        target_cal = None

    overview = {
        "summary_vi": _clamp_why(output.get("summary_vi"), max_len=800),
        "schedule_vi": _build_schedule_vi(output, params),
        "nutrition_vi": _build_nutrition_vi(params),
        "periodization_vi": _build_periodization_vi(output, params),
    }

    advice = sanitize_advice(output.get("advice_vi"))
    days_out: list[dict[str, Any]] = []

    for raw in output.get("days") or []:
        if not isinstance(raw, dict):
            continue
        day_number = int(raw.get("day_index", 0)) + 1
        split_role = str(raw["split_role"]) if raw.get("split_role") else None
        section_notes = sanitize_section_notes(raw.get("section_notes"))
        meal_notes = sanitize_meal_notes(raw.get("meal_notes"))

        ex_insights: list[dict[str, Any]] = []
        for section in ("warmup", "main", "cooldown", "cardio"):
            for item in raw.get(section) or []:
                if not isinstance(item, dict):
                    continue
                try:
                    ex_id = int(item["exercise_id"])
                except (TypeError, ValueError, KeyError):
                    continue
                why = _clamp_why(item.get("why_vi")) or _exercise_why_fallback(
                    item, split_role=split_role, catalog_by_id=catalog_by_id
                )
                ex_insights.append({"exercise_id": ex_id, "why_vi": why})

        meal_insights: list[dict[str, Any]] = []
        day_meals = raw.get("meals") or output.get("meals") or []
        for item in day_meals:
            if not isinstance(item, dict):
                continue
            try:
                food_id = int(item["food_id"])
            except (TypeError, ValueError, KeyError):
                continue
            meal_type = str(item.get("meal_type") or "lunch")
            why = _clamp_why(item.get("why_vi")) or _meal_why_fallback(item, target_cal=target_cal)
            meal_insights.append({"food_id": food_id, "meal_type": meal_type, "why_vi": why})

        days_out.append(
            {
                "day_number": day_number,
                "split_role": split_role,
                "section_notes": section_notes,
                "meal_notes": meal_notes,
                "exercises": ex_insights,
                "meals": meal_insights,
            }
        )

    return {
        "overview": overview,
        "advice_vi": advice,
        "days": days_out,
    }
