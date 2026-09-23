"""Wizard recap + nutrition/preview helpers for workout generation."""

from __future__ import annotations

from typing import Any

from app.schemas.plans import PlanDayIn
from app.services.workout_generation.coach_advice import GOAL_VI as GOAL_LABEL
from app.services.workout_generation.nutrition_targets import NutritionTargets

_ACTIVITY_VI = {
    "sedentary": "Ngồi nhiều",
    "light": "Đứng / đi nhẹ",
    "moderate": "Đi lại nhiều",
    "active": "Lao động chân tay",
    "very_active": "Lao động nặng",
}
_LEVEL_VI = {
    1: "Người mới (0–1 tháng)",
    2: "1–6 tháng",
    3: "6–12 tháng",
}
_EQUIPMENT_VI = {
    "dumbbell": "Tạ đơn",
    "kettlebell": "Kettlebell",
    "resistance-band": "Dây kháng lực",
    "resistance-band-1": "Dây kháng lực",
    "resistance-band-2": "Dây kháng lực",
    "pull-up-bar": "Xà đơn",
    "parallel-bars": "Xà kép",
    "gymnastic-rings": "Vòng treo",
    "yoga-mat-exercise-mat": "Thảm yoga",
    "swiss-ball-stability-ball": "Bóng yoga",
    "jump-rope": "Dây nhảy",
    "plate": "Bánh tạ",
}

def _equipment_label_vi(slug: str) -> str:
    key = str(slug or "").strip().lower()
    return _EQUIPMENT_VI.get(key) or key.replace("-", " ")


def build_wizard_inputs(
    payload: dict[str, Any],
    *,
    goal: str,
    location: str,
    sessions: int,
    session_minutes: int,
    duration_weeks: int,
    experience_level: int,
    no_equipment: bool,
    equipment_list: list[str],
    focus_labels: list[str],
) -> dict[str, Any]:
    """Structured recap of wizard answers — not engine/coach notes."""
    gender = str(payload.get("gender") or "").strip().lower()
    gender_vi = {"male": "Nam", "female": "Nữ"}.get(gender)
    activity = str(payload.get("activity") or "").strip().lower()
    loc_home = location == "home"
    if loc_home and no_equipment:
        equipment_vi = "Không dụng cụ"
        location_vi = "Nhà"
    elif loc_home:
        names: list[str] = []
        seen: set[str] = set()
        for s in equipment_list:
            if not str(s).strip():
                continue
            label = _equipment_label_vi(s)
            if label in seen:
                continue
            seen.add(label)
            names.append(label)
        equipment_vi = ", ".join(names) if names else "Có dụng cụ"
        location_vi = "Nhà"
    else:
        equipment_vi = None
        location_vi = "Phòng gym"

    age = payload.get("age")
    height_cm = payload.get("height_cm")
    weight_kg = payload.get("weight_kg")
    try:
        age_i = int(age) if age is not None else None
    except (TypeError, ValueError):
        age_i = None

    chips: list[str] = []
    if GOAL_LABEL.get(goal):
        chips.append(GOAL_LABEL[goal])
    chips.append(location_vi)
    if loc_home and equipment_vi:
        chips.append(equipment_vi)
    chips.append(f"{sessions} buổi/tuần")
    chips.append(f"{session_minutes} phút/buổi")
    if duration_weeks:
        chips.append(f"{duration_weeks} tuần")
    level_vi = _LEVEL_VI.get(int(experience_level), None)
    if level_vi:
        chips.append(level_vi)
    if payload.get("challenge_100_days") or payload.get("curriculum_12_weeks"):
        chips.append("Thử thách 100 ngày")
    elif str(payload.get("generation_mode") or "").strip().lower() == "free_home":
        chips.append("Xây nền thể lực tại nhà")
    chips.extend(focus_labels)

    who_bits: list[str] = []
    if gender_vi:
        who_bits.append(gender_vi)
    if age_i:
        who_bits.append(f"{age_i} tuổi")
    try:
        if height_cm is not None:
            who_bits.append(f"{int(float(height_cm))} cm")
    except (TypeError, ValueError):
        pass
    try:
        if weight_kg is not None:
            w = float(weight_kg)
            who_bits.append(f"{int(w) if w == int(w) else w} kg")
    except (TypeError, ValueError):
        pass
    recap_parts: list[str] = []
    if who_bits:
        recap_parts.append(" · ".join(who_bits))
    line2 = [location_vi]
    if loc_home and equipment_vi:
        line2.append(equipment_vi.lower() if equipment_vi != "Không dụng cụ" else "không dụng cụ")
    line2.append(f"{sessions} buổi/tuần × {session_minutes} phút")
    if duration_weeks:
        line2.append(f"{duration_weeks} tuần")
    if level_vi:
        line2.append(level_vi)
    recap_parts.append(" · ".join(line2))
    if focus_labels:
        recap_parts.append("Ưu tiên: " + ", ".join(focus_labels))

    return {
        "goal": goal,
        "goal_vi": GOAL_LABEL.get(goal, goal),
        "gender_vi": gender_vi,
        "age": age_i,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "activity_vi": _ACTIVITY_VI.get(activity),
        "location": location,
        "location_vi": location_vi,
        "no_equipment": bool(no_equipment),
        "equipment_list": list(equipment_list),
        "equipment_vi": equipment_vi,
        "sessions_per_week": sessions,
        "session_minutes": session_minutes,
        "duration_weeks": duration_weeks,
        "experience_level": experience_level,
        "experience_vi": level_vi,
        "focus_vi": list(focus_labels),
        "challenge_100_days": bool(
            payload.get("challenge_100_days") or payload.get("curriculum_12_weeks")
        ),
        "curriculum_12_weeks": False,
        "generation_mode": (
            "free_home"
            if str(payload.get("generation_mode") or "").strip().lower() == "free_home"
            else None
        ),
        "chips": chips,
        "recap_vi": "\n".join(recap_parts),
    }


def _knowledge_nutrition_note_vi(experience_level: int | None, goal: str) -> str:
    if experience_level is None:
        return ""
    from app.services.workout_generation.phase_knowledge import flags_for_phase

    goal_n = (goal or "").strip().lower()
    flags = [flags_for_phase(experience_level, month) for month in (1, 2, 3)]
    bits: list[str] = []
    if any(f.want_carb_cycle for f in flags):
        if goal_n in {"gain_weight", "gain_muscle"}:
            bits.append(
                "Carb cycling nhẹ: ngày tập tinh bột hơi cao, ngày nghỉ không cắt sâu."
            )
        else:
            bits.append(
                "Carb cycling: ngày tập tinh bột cao hơn, ngày nghỉ thấp hơn; đạm gần như cố."
            )
    elif int(experience_level) <= 1:
        bits.append("Macro ổn định theo block — không carb cycling.")
    if any(f.want_refeed for f in flags) and goal_n == "lose_weight":
        bits.append("Pha 3: 1 ngày refeed ~TDEE.")
    return (" " + " ".join(bits)) if bits else ""


def _nutrition_insight_vi(
    nutrition: NutritionTargets | None,
    *,
    goal: str,
    experience_level: int | None = None,
) -> str | None:
    if nutrition is None:
        return None
    goal_vi = GOAL_LABEL.get(goal, goal)
    delta = nutrition.delta_kcal
    tdee = f"{nutrition.tdee:,}".replace(",", ".")
    target = f"{nutrition.target_calories:,}".replace(",", ".")
    protein = str(nutrition.protein_g).replace(".", ",")
    base = f"TDEE (~{tdee} kcal) · mục tiêu {goal_vi} → ~{target} kcal trung bình/ngày · đạm {protein}g."
    if abs(delta) >= 50:
        kind = "thiếu" if delta < 0 else "dư"
        base += f" ({kind} ~{abs(delta)} kcal)."
    base += " Calo cao hơn ngày tập strength, thấp hơn ngày nghỉ; theo dõi cân trung bình 7 ngày."
    base += _knowledge_nutrition_note_vi(experience_level, goal)
    return base


def _nutrition_insight_vi_blocks(
    blocks: list[dict[str, Any]],
    goal: str,
    experience_level: int | None = None,
) -> str | None:
    if not blocks:
        return None
    if len(blocks) <= 1:
        return None
    parts: list[str] = []
    for b in blocks:
        weeks = b.get("weeks") or []
        avg = b.get("avg_target_calories")
        if not weeks or avg is None:
            continue
        wlabel = f"tuần {weeks[0]}" if len(weeks) == 1 else f"tuần {weeks[0]}–{weeks[-1]}"
        parts.append(f"{wlabel}: ~{int(avg):,}".replace(",", ".") + " kcal TB/ngày")
    if not parts:
        return None
    goal_vi = GOAL_LABEL.get(goal, goal)
    return (
        f"Mục tiêu {goal_vi}: calo dự kiến điều chỉnh theo block dinh dưỡng nếu đạt tốc độ cân mục tiêu — "
        + "; ".join(parts)
        + ". Cân thực tế có thể khác; cập nhật cân để TAPTOT điều chỉnh (khi đã lưu lịch)."
        + _knowledge_nutrition_note_vi(experience_level, goal)
    )


def _home_plan_has_load_selection(
    plan_days: list[PlanDayIn],
    meta_by_id: dict[int, dict[str, Any]],
    *,
    no_equipment: bool,
) -> bool:
    """True when a home plan includes free-weight or band mains (need load-pick cue)."""
    from app.services.workout_generation.coach_notes import load_kind_for_item

    for day in plan_days or []:
        for ex in day.exercises or []:
            if str(ex.section or "main") != "main":
                continue
            meta = meta_by_id.get(int(ex.exercise_id)) or {}
            kind = load_kind_for_item(meta, no_equipment=no_equipment)
            if kind in {"loaded", "band"}:
                return True
    return False


def _meal_day_insights(plan_days: list[PlanDayIn]) -> list[dict[str, Any]]:
    days_out: list[dict[str, Any]] = []
    for day in plan_days:
        meals = []
        for meal in day.meals or []:
            meals.append(
                {
                    "food_id": meal.food_id,
                    "meal_type": meal.meal_type,
                    "why_vi": meal.notes_vi,
                }
            )
        days_out.append(
            {
                "day_number": day.day_number,
                "split_role": day.split_role,
                "meal_notes": day.meal_notes or {},
                "meals": meals,
            }
        )
    return days_out


def _preview_plan_days(plan_days: list[PlanDayIn], name_map: dict[int, str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for day in plan_days:
        exercises = []
        for ex in day.exercises:
            row = ex.model_dump()
            eid = int(ex.exercise_id)
            name = name_map.get(eid)
            if not name or str(name).strip().lower() in {"", "none"}:
                name = f"#{eid}"
            row["name_vi"] = name
            exercises.append(row)
        dumped = day.model_dump()
        dumped["exercises"] = exercises
        out.append(dumped)
    return out

