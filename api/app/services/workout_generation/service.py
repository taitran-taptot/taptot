"""Orchestrate hybrid AI workout plan generation."""

from __future__ import annotations

from collections import Counter
from types import SimpleNamespace
from typing import Any

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError
from app.models.entities import Exercise, Food, MuscleGroup
from app.schemas.plans import CreatePlanRequest, PlanDayIn
from app.services.exercise_prescription import clamp_experience_level
from app.services.plan_service import PlanService
from app.services.periodization import periodization_advice_vi, resolve_overload_profile
from app.services.workout_generation.assemble import (
    assemble_day,
    collect_day_shortlists_for_prompt,
    inject_main_primer_warmup,
)
from app.services.workout_generation.capacity import resolve_capacity
from app.services.workout_generation.coach_advice import (
    GOAL_VI as GOAL_LABEL,
    apply_duration_tweaks,
    apply_schedule_swaps,
    build_schedule_summary,
    generate_coach_advice,
)
from app.services.workout_generation.fb_rotation import (
    effective_pick_role,
    fb_session_title,
    is_full_body_role,
)
from app.services.workout_generation.focus import (
    focus_labels_vi,
    focus_muscle_slugs,
)
from app.services.workout_generation.injury_filters import parse_injury_constraints
from app.services.workout_generation.weekly_volume import (
    apply_weekly_dose,
    prefer_knee_pushups,
    recap_l1_session_sets,
)
from app.services.workout_generation.frame_picker import pick_master_frame
from app.services.workout_generation.openai_picker import (
    OpenAIPickError,
    deterministic_picks,
    merge_week_b_isolation_picks,
    pick_challenge_phase_with_openai,
    pick_with_openai,
    picks_from_llm_day,
    stems_from_picks,
    strength_ids_from_picks,
)
from app.services.workout_generation.shortlist import (
    expand_selected_equipment,
    is_home_denied_exercise,
)
from app.services.workout_generation.coverage import repair_plan_day_upper_pull
from app.services.workout_generation.session_policy import resolve_session_policy
from app.services.workout_generation.muscle_quotas import reorder_main_section_exercises
from app.services.workout_generation.session_duration import (
    clamp_session_to_target,
    refill_thin_days,
    top_up_session_minutes,
)
from app.services.workout_generation.split_score import pick_week_code
from app.services.workout_generation.meal_engine import (
    apply_meals_to_days,
    apply_meals_with_schedule,
    apply_nutrition_blocks_to_expanded_days,
    generate_meals,
    generate_meals_with_blocks,
)
from app.services.workout_generation.nutrition_targets import (
    BLOCK_SIZE_WEEKS,
    NutritionTargets,
    build_nutrition_blocks,
    estimate_targets,
    parse_kg_per_week,
)
from app.services.workout_generation.phase_templates import (
    MESOCYCLE_PHASES,
    apply_phase_rpe,
    curriculum_insight_payload,
)
from app.services.workout_generation.session_policy import (
    CHALLENGE_DELOAD_WEEKS,
    CHALLENGE_PHASE_RANGES,
)
from app.services.workout_generation.free_home_curriculum import (
    FREE_HOME_WEEKS,
    apply_free_home_finishes,
    motive_focus_slugs,
    normalize_foundation_motive,
    periodization_vi as free_home_periodization_vi,
    pick_nutrition_copy,
    plan_title_vi as free_home_plan_title_vi,
)
from app.services.schedule_spec_master import lookup_week_split, experience_to_master_key

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

def _nutrition_insight_vi(nutrition: NutritionTargets | None, *, goal: str) -> str | None:
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
    return base


def _nutrition_insight_vi_blocks(blocks: list[dict[str, Any]], goal: str) -> str | None:
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


def _merge_exercise_meta(
    db: Session,
    plan_days: list[PlanDayIn],
    name_map: dict[int, str],
    meta_by_id: dict[int, dict[str, Any]],
) -> tuple[dict[int, str], dict[int, dict[str, Any]]]:
    all_ids: set[int] = set()
    for day in plan_days:
        for ex in day.exercises:
            all_ids.add(int(ex.exercise_id))
    missing = [eid for eid in all_ids if eid not in meta_by_id]
    if not missing:
        return name_map, meta_by_id
    rows = (
        db.query(Exercise, MuscleGroup)
        .join(MuscleGroup, MuscleGroup.id == Exercise.muscle_group_id)
        .filter(Exercise.id.in_(missing))
        .all()
    )
    from app.services.workout_generation.shortlist import _equipment_slugs_by_exercise

    eq_map = _equipment_slugs_by_exercise(db, [int(ex.id) for ex, _mg in rows])
    for ex, mg in rows:
        raw_name = str(ex.name_vi or "").strip()
        if not raw_name or raw_name.lower() == "none":
            raw_name = str(ex.name_en or "").strip() or f"#{int(ex.id)}"
        name_map[int(ex.id)] = raw_name
        meta_by_id[int(ex.id)] = {
            "movement_role": ex.movement_role,
            "movement_pattern": ex.movement_pattern,
            "muscle_slug": mg.slug,
            "name_vi": raw_name,
            "name_en": str(ex.name_en or "").strip() or None,
            "equipment_slugs": sorted(eq_map.get(int(ex.id), set())),
        }
    return name_map, meta_by_id


def _drop_home_denied_mains(
    plan_days: list[PlanDayIn],
    *,
    meta_by_id: dict[int, dict[str, Any]],
    location: str,
    no_equipment: bool,
    equipment_slugs: list[str] | None,
    experience_level: int | None = None,
    fitness_baseline: dict[str, Any] | None = None,
) -> None:
    for day in plan_days:
        kept: list[Any] = []
        for ex in list(getattr(day, "exercises", None) or []):
            section = str(getattr(ex, "section", None) or "main")
            if section != "main":
                kept.append(ex)
                continue
            meta = meta_by_id.get(int(ex.exercise_id)) or {}
            if is_home_denied_exercise(
                name_vi=meta.get("name_vi"),
                name_en=meta.get("name_en"),
                location=location,
                no_equipment=no_equipment,
                user_slugs=equipment_slugs,
                experience_level=experience_level,
                exercise_slugs=meta.get("equipment_slugs"),
                fitness_baseline=fitness_baseline,
            ):
                continue
            kept.append(ex)
        day.exercises = kept


def _finish_generated_week(
    db: Session,
    plan_days: list[PlanDayIn],
    *,
    day_contexts: list[dict[str, Any]],
    session_minutes: int,
    location: str,
    level: int,
    capacity: Any,
    focus_slugs: frozenset[str] | set[str],
    goal: str,
    extra_goals: list[str],
    policy: Any,
    name_map: dict[int, str],
    meta_by_id: dict[int, dict[str, Any]],
    no_equipment: bool = False,
    equipment_list: list[str] | None = None,
    fitness_baseline: dict[str, Any] | None = None,
    gear_insight: dict[str, Any] | None = None,
    free_home: bool = False,
) -> tuple[list[PlanDayIn], str | None, dict[int, str], dict[int, dict[str, Any]]]:
    name_map, meta_by_id = _merge_exercise_meta(db, plan_days, name_map, meta_by_id)
    _drop_home_denied_mains(
        plan_days,
        meta_by_id=meta_by_id,
        location=location,
        no_equipment=no_equipment,
        equipment_slugs=equipment_list,
        experience_level=level,
        fitness_baseline=fitness_baseline,
    )
    plan_days, volume_note = apply_weekly_dose(
        plan_days,
        meta_by_id=meta_by_id,
        effective_level=level,
        strength_tier=capacity.strength_tier,
        focus_slugs=focus_slugs,
        session_minutes=session_minutes,
        conservative_volume=capacity.conservative_volume,
        location=location,
    )
    refilled = refill_thin_days(
        plan_days,
        day_contexts=day_contexts,
        session_minutes=session_minutes,
        location=location,
        experience_level=level,
        db=db,
        goal=goal,
        extra_goals=extra_goals,
        cardio_on_lift_days=policy.cardio_on_lift_days,
        liss_finisher=policy.liss_finisher,
        meta_by_id=meta_by_id,
    )
    if refilled:
        name_map, meta_by_id = _merge_exercise_meta(db, plan_days, name_map, meta_by_id)
        _drop_home_denied_mains(
            plan_days,
            meta_by_id=meta_by_id,
            location=location,
            no_equipment=no_equipment,
            equipment_slugs=equipment_list,
            experience_level=level,
            fitness_baseline=fitness_baseline,
        )
        plan_days, volume_note = apply_weekly_dose(
            plan_days,
            meta_by_id=meta_by_id,
            effective_level=level,
            strength_tier=capacity.strength_tier,
            focus_slugs=focus_slugs,
            session_minutes=session_minutes,
            conservative_volume=capacity.conservative_volume,
            drop_exercises=False,
            location=location,
        )
    plan_days = top_up_session_minutes(
        plan_days,
        session_minutes=session_minutes,
        meta_by_id=meta_by_id,
        experience_level=level,
        home_session=(str(location or "").strip().lower() == "home"),
    )
    if level <= 1:
        recap_l1_session_sets(
            plan_days,
            meta_by_id=meta_by_id,
            session_minutes=session_minutes,
        )
    plan_days = clamp_session_to_target(
        plan_days,
        session_minutes=session_minutes,
        meta_by_id=meta_by_id,
        location=location,
    )
    from app.services.workout_generation.home_implements import apply_home_implement_coverage

    pools_by_day: dict[int, list[Any]] = {}
    for ctx in day_contexts:
        idx = int(ctx["frame_day"].day_index)
        sl = ctx.get("shortlists") or {}
        items: list[Any] = []
        for key in ("resistance", "compound", "accessory", "conditioning", "cardio"):
            items.extend(sl.get(key) or [])
        pools_by_day[idx + 1] = items
        for it in items:
            eid = int(getattr(it, "id", 0) or 0)
            if not eid:
                continue
            m = meta_by_id.setdefault(eid, {})
            if getattr(it, "name_vi", None):
                m.setdefault("name_vi", it.name_vi)
            if getattr(it, "name_en", None):
                m.setdefault("name_en", it.name_en)
            if getattr(it, "movement_role", None):
                m.setdefault("movement_role", it.movement_role)
            if getattr(it, "movement_pattern", None):
                m.setdefault("movement_pattern", it.movement_pattern)
            if getattr(it, "muscle_slug", None):
                m.setdefault("muscle_slug", it.muscle_slug)
            if hasattr(it, "equipment_slugs"):
                m.setdefault("equipment_slugs", sorted(it.equipment_slugs or ()))
    from app.services.workout_generation.home_gear_priority import (
        enforce_home_gear_variety,
    )

    variety = enforce_home_gear_variety(
        plan_days,
        pools_by_day=pools_by_day,
        meta_by_id=meta_by_id,
        user_slugs=equipment_list,
        experience_level=level,
        location=location,
        no_equipment=no_equipment,
    )
    if gear_insight is not None:
        gear_insight.setdefault("replaced", []).extend(variety.get("replaced") or [])
        gear_insight.setdefault("unchanged_no_alternative", []).extend(
            variety.get("unchanged_no_alternative") or []
        )
        if variety.get("gear_share") is not None:
            gear_insight["gear_share"] = variety["gear_share"]
    plan_days = apply_home_implement_coverage(
        plan_days,
        user_slugs=equipment_list,
        meta_by_id=meta_by_id,
        pools_by_day=pools_by_day,
        location=location,
        no_equipment=no_equipment,
        experience_level=level,
    )
    focus_frozen = frozenset(focus_slugs) if focus_slugs else None
    for day in plan_days:
        if not day.exercises:
            continue
        repair_plan_day_upper_pull(
            day,
            candidates=pools_by_day.get(int(day.day_number or 0), []),
            meta_by_id=meta_by_id,
        )
        day.exercises = reorder_main_section_exercises(
            day.split_role,
            list(day.exercises),
            meta_by_id,
            focus_slugs=focus_frozen,
        )
        inject_main_primer_warmup(
            day,
            meta_by_id=meta_by_id,
            no_equipment=no_equipment,
            fitness_baseline=fitness_baseline,
            home_session=str(location or "").strip().lower() == "home",
            experience_level=level,
            free_home=free_home,
            session_minutes=session_minutes,
        )
        for i, ex in enumerate(day.exercises, start=1):
            ex.sort_order = i
    if str(location or "").strip().lower() == "home":
        from app.services.workout_generation.dose_bounds import apply_home_fitness_doses
        from app.services.workout_generation.free_home_curriculum import (
            free_home_session_dose,
        )

        primer_sets = None
        if free_home:
            primer_sets = int(free_home_session_dose(session_minutes).get("primer_sets") or 2)
        apply_home_fitness_doses(
            plan_days,
            fitness_baseline=fitness_baseline,
            meta_by_id=meta_by_id,
            experience_level=level,
            no_equipment=no_equipment,
            home_session=True,
            primer_sets=primer_sets,
        )
        for day in plan_days:
            for i, ex in enumerate(day.exercises or [], start=1):
                ex.sort_order = i
    return plan_days, volume_note, name_map, meta_by_id


def _assemble_week_from_picks(
    db: Session,
    day_contexts: list[dict[str, Any]],
    picks_by_day: dict[int, dict[str, list[int]]],
    *,
    level: int,
    session_minutes: int,
    equipment_list: list[str],
    no_equipment: bool,
    ai_suggest_equipment: bool,
    location: str,
    focus_slugs: frozenset[str] | set[str],
    goal: str,
    extra_goals: list[str],
    policy: Any,
    injury: Any,
    pushups_max: int | None = None,
    fitness_baseline: dict[str, Any] | None = None,
    free_home: bool = False,
) -> list[PlanDayIn]:
    plan_days: list[PlanDayIn] = []
    for ctx in day_contexts:
        fd = ctx["frame_day"]
        pick_role = ctx["pick_role"]
        picks = picks_by_day.get(int(fd.day_index)) or {}
        day = assemble_day(
            db,
            frame_day=fd,
            day_number=fd.day_index + 1,
            experience_level=level,
            session_minutes=session_minutes,
            equipment_slugs=equipment_list,
            no_equipment=no_equipment,
            ai_suggest_equipment=ai_suggest_equipment,
            picks_by_block=picks,
            location=location,
            focus_slugs=focus_slugs,
            goal=goal,
            extra_goals=extra_goals,
            cardio_on_lift_days=policy.cardio_on_lift_days,
            liss_finisher=policy.liss_finisher,
            split_role=pick_role,
            exclude_ids=set(),
            title_override=ctx["title_override"],
            injury=injury,
            strict_openai_picks=True,
            precomputed_shortlists=ctx.get("shortlists") or None,
            pushups_max=pushups_max,
            fitness_baseline=fitness_baseline,
            free_home=free_home,
        )
        plan_days.append(day)
    return plan_days


def generate_workout(
    db: Session,
    user_id: str | None,
    payload: dict[str, Any],
    *,
    persist: bool = True,
) -> dict[str, Any]:
    level = clamp_experience_level(payload.get("experience_level"))
    raw_level = payload.get("experience_level")
    try:
        if raw_level is not None and int(raw_level) >= 4:
            raise BadRequestError(
                "Mức kinh nghiệm trên 12 tháng đang được phát triển. Vui lòng chọn mức khác."
            )
    except (TypeError, ValueError):
        pass

    sessions = int(payload.get("sessions_per_week") or 3)
    session_minutes = int(payload.get("session_minutes") or 45)
    duration_weeks = int(payload.get("duration_weeks") or 4)
    free_home = str(payload.get("generation_mode") or "").strip().lower() == "free_home"
    curriculum = bool(
        (payload.get("curriculum_12_weeks") or payload.get("challenge_100_days"))
        and not free_home
    )
    challenge = curriculum  # DB/TTL flag for long plans

    no_equipment = bool(payload.get("no_equipment"))
    ai_suggest_equipment = bool(payload.get("ai_suggest_equipment"))
    equipment_list = expand_selected_equipment(payload.get("equipment_list") or [])
    location = str(payload.get("location") or "home").strip().lower()
    if location not in {"gym", "home"}:
        location = "home"
    if free_home:
        location = "home"
        no_equipment = True
        ai_suggest_equipment = False
        equipment_list = []
        duration_weeks = FREE_HOME_WEEKS
        payload = {
            **payload,
            "generation_mode": "free_home",
            "challenge_100_days": False,
            "curriculum_12_weeks": False,
            "location": "home",
            "no_equipment": True,
            "ai_suggest_equipment": False,
            "equipment_list": [],
            "duration_weeks": FREE_HOME_WEEKS,
            "food_ids": [],
            "ai_suggest_foods": False,
            "foundation_motive": normalize_foundation_motive(payload.get("foundation_motive")),
        }
    foundation_motive = (
        normalize_foundation_motive(payload.get("foundation_motive")) if free_home else None
    )
    gender = str(payload.get("gender") or "male").strip().lower()
    capacity = resolve_capacity(
        payload.get("experience_level"),
        payload.get("fitness_baseline"),
        sessions_per_week=sessions,
    )
    baseline = payload.get("fitness_baseline") or {}
    try:
        pushups_max = int(baseline["pushups_max"]) if baseline.get("pushups_max") is not None else None
    except (TypeError, ValueError):
        pushups_max = None
    level = capacity.effective_level
    extra_goals = [str(x) for x in (payload.get("extra_goals") or []) if str(x).strip()]
    injury = parse_injury_constraints(payload.get("health_note"), age=payload.get("age"))
    policy = resolve_session_policy(
        capacity,
        goal=str(payload.get("goal") or "maintain"),
        session_minutes=session_minutes,
        extra_goals=extra_goals,
        no_equipment=no_equipment,
        location=location,
    )
    requested_sessions = max(2, min(6, sessions))
    sessions_clamped = policy.clamp_sessions(sessions)
    session_minutes = policy.clamp_minutes(session_minutes)
    duration_weeks = policy.clamp_weeks(
        duration_weeks, challenge=challenge, curriculum=curriculum
    )
    focus_slugs = focus_muscle_slugs(list(payload.get("focus_areas") or []))
    if free_home and foundation_motive:
        focus_slugs = frozenset(focus_slugs | motive_focus_slugs(foundation_motive))
    goal = str(payload.get("goal") or "maintain")
    default_week = lookup_week_split(
        experience=experience_to_master_key(level),
        sessions=sessions_clamped,
        gender=gender,
        location=location,
        home_equip="no_equip" if no_equipment else "with_equip",
    )
    split_choice = pick_week_code(
        default_week or "",
        sessions=sessions_clamped,
        capacity=capacity,
        goal=goal,
        focus_areas=list(payload.get("focus_areas") or []),
        no_equipment=no_equipment,
    )

    try:
        frame, frame_days = pick_master_frame(
            db,
            experience_level=level,
            sessions_per_week=sessions_clamped,
            gender=gender,
            location=location,
            no_equipment=no_equipment,
            week_code=split_choice.week_code or None,
        )
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc
    if not frame_days:
        raise BadRequestError("Khung lịch tập chưa có ngày. Liên hệ admin.")

    day_contexts: list[dict[str, Any]] = []
    week_payload: list[dict[str, Any]] = []
    # Home + gear: how many sessions share a split role decides how many distinct gear
    # options a slot needs before bodyweight rows are allowed to top up the pool.
    _pick_roles: list[str] = []
    _fb_probe = 0
    for fd in frame_days:
        if is_full_body_role(fd.split_role):
            _pick_roles.append(str(effective_pick_role(fd.split_role, fb_offset=_fb_probe)))
            _fb_probe += 1
        else:
            _pick_roles.append(str(fd.split_role))
    role_counts = Counter(_pick_roles)
    pick_variants = 3 if curriculum else 1
    fb_offset = 0
    for fd in frame_days:
        if is_full_body_role(fd.split_role):
            pick_role = effective_pick_role(fd.split_role, fb_offset=fb_offset)
            fb_offset += 1
            title_override = fb_session_title(pick_role, day_number=fd.day_index + 1)
        else:
            pick_role = fd.split_role
            title_override = None
        stored_shortlists: dict[str, list] = {}
        stored_slots: list[dict[str, Any]] = []
        stored_gear_meta: dict[str, dict[str, int]] = {}
        day_blocks = collect_day_shortlists_for_prompt(
            db,
            frame_day=fd,
            experience_level=level,
            session_minutes=session_minutes,
            equipment_slugs=equipment_list,
            no_equipment=no_equipment,
            ai_suggest_equipment=ai_suggest_equipment,
            location=location,
            focus_slugs=focus_slugs,
            cardio_on_lift_days=policy.cardio_on_lift_days,
            liss_finisher=policy.liss_finisher,
            goal=goal,
            extra_goals=extra_goals,
            split_role=pick_role,
            exclude_ids=set(),
            injury=injury,
            out_shortlists=stored_shortlists,
            out_slots=stored_slots,
            pushups_max=pushups_max,
            fitness_baseline=baseline,
            week_role_count=int(role_counts.get(str(pick_role), 1) or 1),
            pick_variants=pick_variants,
            out_gear_meta=stored_gear_meta,
        )
        week_payload.append(
            {
                "day_index": fd.day_index,
                "split_role": pick_role,
                "label_vi": getattr(fd, "label_vi", None) or f"Buổi {fd.day_index + 1}",
                "blocks": day_blocks,
                "slots": list(stored_slots),
            }
        )
        day_contexts.append(
            {
                "frame_day": fd,
                "pick_role": pick_role,
                "title_override": title_override,
                "day_blocks": day_blocks,
                "shortlists": stored_shortlists,
                "slots": list(stored_slots),
                "gear_meta": stored_gear_meta,
            }
        )

    from app.services.workout_generation.dose_bounds import annotate_week_dose_bounds

    annotate_week_dose_bounds(
        week_payload,
        experience_level=level,
        fitness_baseline=baseline,
        no_equipment=no_equipment,
        home_session=location == "home",
    )
    profile_for_pick = {
        "goal": goal,
        "gender": gender,
        "experience_level": level,
        "strength_tier": capacity.strength_tier,
        "fitness_baseline": baseline,
        "sessions_per_week": sessions_clamped,
        "session_minutes": session_minutes,
        "location": location,
        "no_equipment": no_equipment,
        "focus_areas": list(payload.get("focus_areas") or []),
        "extra_goals": extra_goals,
        "health_note": payload.get("health_note"),
        "injury_notes_vi": list(injury.notes_vi or []),
        "week_code": frame.week_code,
        "chest_compound_hint": (
            "Ngực nhà: chống đẩy / tạ đơn / dây. Chỉ nằm và dốc lên, không dốc xuống. "
            "Dùng mix dụng cụ đã chọn — đừng chỉ tạ đơn nếu pool còn dây."
            if location == "home"
            else (
                "Ngực compound: L1 máy; L2+ tạ đòn/tạ đơn. Chỉ nằm và dốc lên, không dốc xuống. "
                "Slot ngực 1 nằm, slot 2 (nếu có) dốc lên."
            )
        ),
        "home_no_equip_hint": (
            "Ngày Pull không dụng cụ là Lưng · core (BW): Superman, bird-dog, Y-T-W — "
            "không hít xà hay chèo phòng gym. Upper không đồ là Thân trên (BW)."
            if location == "home" and no_equipment
            else None
        ),
        "home_l1_bar_hint": (
            "L1 tại nhà: không pick hít xà / chin-up / dip / muscle-up trần. "
            "Ưu tiên assisted, scapular pull, inverted/australian row, chèo dây, chống đẩy gối."
            if location == "home" and level <= 1
            else None
        ),
        "home_finisher_hint": (
            "Cardio cuối buổi nhà: Zone 2 nhẹ (đi bộ, march). Không burpee / gối cao / jumping jack. "
            "Nếu user chọn dây nhảy thì một bout nhảy dây nhẹ, không HIIT."
            if location == "home"
            else None
        ),
    }
    assemble_kwargs: dict[str, Any] = {
        "level": level,
        "session_minutes": session_minutes,
        "equipment_list": equipment_list,
        "no_equipment": no_equipment,
        "ai_suggest_equipment": ai_suggest_equipment,
        "location": location,
        "focus_slugs": focus_slugs,
        "goal": goal,
        "extra_goals": extra_goals,
        "policy": policy,
        "injury": injury,
        "pushups_max": pushups_max,
        "fitness_baseline": baseline,
        "free_home": free_home,
    }
    finish_kwargs: dict[str, Any] = {
        "day_contexts": day_contexts,
        "session_minutes": session_minutes,
        "location": location,
        "level": level,
        "capacity": capacity,
        "focus_slugs": focus_slugs,
        "goal": goal,
        "extra_goals": extra_goals,
        "policy": policy,
        "no_equipment": no_equipment,
        "equipment_list": equipment_list,
        "fitness_baseline": baseline,
        "free_home": free_home,
    }
    from app.services.workout_generation.home_gear_priority import home_gear_active

    home_gear_insight: dict[str, Any] | None = None
    if home_gear_active(location, no_equipment=no_equipment, equipment_slugs=equipment_list):
        thin_pools: list[dict[str, Any]] = []
        for ctx in day_contexts:
            for slot_key, gm in (ctx.get("gear_meta") or {}).items():
                if int(gm.get("bw_kept") or 0) > 0:
                    thin_pools.append(
                        {
                            "day_number": int(ctx["frame_day"].day_index) + 1,
                            "slot": slot_key,
                            "gear_n": int(gm.get("gear_n") or 0),
                            "need": int(gm.get("need") or 0),
                            "bw_kept": int(gm.get("bw_kept") or 0),
                        }
                    )
        home_gear_insight = {
            "equipment": list(equipment_list),
            "gear_share": None,
            "thin_pools": thin_pools,
            "replaced": [],
            "unchanged_no_alternative": [],
        }
        finish_kwargs["gear_insight"] = home_gear_insight
    name_map: dict[int, str] = {}
    meta_by_id: dict[int, dict[str, Any]] = {}
    volume_note: str | None = None
    week_templates_dump: list[Any] | None = None
    challenge_variation_insight: dict[str, Any] | None = None
    phase_rationales: list[str] = []

    if curriculum:
        avoid_ids: list[int] = []
        avoid_stems: list[str] = []
        want_knee = prefer_knee_pushups(
            location=location,
            no_equipment=no_equipment,
            pushups_max=pushups_max,
        )
        phase_ab: list[dict[str, list[PlanDayIn]]] = []
        challenge_variation_insight = {
            "changed_days": 0,
            "unchanged_no_alternative": [],
        }
        for phase_i, phase_meta in enumerate(MESOCYCLE_PHASES):
            lo, hi = CHALLENGE_PHASE_RANGES[phase_i]
            phase_avoid_ids = list(dict.fromkeys(avoid_ids))
            phase_avoid_stems = [
                s for s in dict.fromkeys(avoid_stems) if not (want_knee and s == "pushup")
            ]
            try:
                phase_out = pick_challenge_phase_with_openai(
                    week_payload,
                    profile=profile_for_pick,
                    phase={
                        "key": phase_meta.get("key"),
                        "label_vi": phase_meta.get("label_vi"),
                        "rpe_vi": phase_meta.get("rpe_vi"),
                        "month": phase_i + 1,
                        "weeks": list(range(lo, hi + 1)),
                    },
                    avoid_ids=phase_avoid_ids,
                    avoid_stems=phase_avoid_stems,
                )
            except OpenAIPickError as exc:
                raise BadRequestError(exc.message) from exc

            llm_a_by: dict[int, dict[str, Any]] = {}
            for d in phase_out.get("days") or []:
                try:
                    llm_a_by[int(d.get("day_index"))] = d
                except (TypeError, ValueError):
                    continue
            llm_b_by: dict[int, dict[str, Any]] = {}
            for d in phase_out.get("week_b") or []:
                try:
                    llm_b_by[int(d.get("day_index"))] = d
                except (TypeError, ValueError):
                    continue

            picks_a_by: dict[int, dict[str, list[int]]] = {}
            picks_b_by: dict[int, dict[str, list[int]]] = {}
            for ctx in day_contexts:
                idx = int(ctx["frame_day"].day_index)
                try:
                    picks_a = picks_from_llm_day(
                        llm_a_by.get(idx),
                        ctx["day_blocks"],
                        split_role=ctx["pick_role"],
                        focus_slugs=focus_slugs,
                        avoid_ids=phase_avoid_ids,
                        avoid_stems=phase_avoid_stems,
                        slots=ctx.get("slots"),
                        experience_level=level,
                    )
                except OpenAIPickError as exc:
                    raise BadRequestError(exc.message) from exc
                picks_b = merge_week_b_isolation_picks(
                    picks_a,
                    llm_b_by.get(idx),
                    ctx["day_blocks"],
                    split_role=ctx["pick_role"],
                    focus_slugs=focus_slugs,
                    avoid_ids=phase_avoid_ids,
                    avoid_stems=phase_avoid_stems,
                    slots=ctx.get("slots"),
                )
                picks_a_by[idx] = picks_a
                picks_b_by[idx] = picks_b
                if picks_b != picks_a:
                    challenge_variation_insight["changed_days"] += 1
                else:
                    from app.services.workout_generation.session_templates import (
                        slot_allows_week_b_swap,
                    )

                    a_slots = dict(picks_a.get("_slot_picks") or {})
                    swap_slots = [
                        spec
                        for spec in (ctx.get("slots") or [])
                        if slot_allows_week_b_swap(spec)
                    ]
                    has_alternative = False
                    for spec in swap_slots:
                        a_ids = {
                            int(x)
                            for x in a_slots.get(str(spec.get("key") or ""), [])
                        }
                        for raw in spec.get("pool") or []:
                            try:
                                eid = int(
                                    raw.get("id")
                                    if isinstance(raw, dict)
                                    else raw.id
                                )
                            except (TypeError, ValueError, AttributeError):
                                continue
                            if eid not in a_ids:
                                has_alternative = True
                                break
                        if has_alternative:
                            break
                    if swap_slots and not has_alternative:
                        challenge_variation_insight[
                            "unchanged_no_alternative"
                        ].append(
                            {
                                "phase": phase_i + 1,
                                "day_number": idx + 1,
                                "reason": "no_accessory_alternative",
                            }
                        )

            for ctx in day_contexts:
                idx = int(ctx["frame_day"].day_index)
                blocks = ctx["day_blocks"]
                avoid_ids.extend(strength_ids_from_picks(picks_a_by.get(idx)))
                avoid_ids.extend(strength_ids_from_picks(picks_b_by.get(idx)))
                for stem in stems_from_picks(picks_a_by.get(idx), blocks):
                    if want_knee and stem == "pushup":
                        continue
                    avoid_stems.append(stem)
                for stem in stems_from_picks(picks_b_by.get(idx), blocks):
                    if want_knee and stem == "pushup":
                        continue
                    avoid_stems.append(stem)

            days_a = _assemble_week_from_picks(
                db, day_contexts, picks_a_by, **assemble_kwargs
            )
            days_a, vnote, name_map, meta_by_id = _finish_generated_week(
                db, days_a, name_map=name_map, meta_by_id=meta_by_id, **finish_kwargs
            )
            if vnote:
                volume_note = vnote
            b_differs = any(picks_b_by[i] != picks_a_by[i] for i in picks_a_by)
            if b_differs:
                days_b = _assemble_week_from_picks(
                    db, day_contexts, picks_b_by, **assemble_kwargs
                )
                days_b, vnote, name_map, meta_by_id = _finish_generated_week(
                    db, days_b, name_map=name_map, meta_by_id=meta_by_id, **finish_kwargs
                )
                if vnote:
                    volume_note = vnote
            else:
                days_b = [d.model_copy(deep=True) for d in days_a]
            days_a = apply_phase_rpe(
                days_a, phase_i, meta_by_id=meta_by_id, focus_slugs=focus_slugs
            )
            days_b = apply_phase_rpe(
                days_b, phase_i, meta_by_id=meta_by_id, focus_slugs=focus_slugs
            )
            days_a = clamp_session_to_target(
                days_a,
                session_minutes=session_minutes,
                meta_by_id=meta_by_id,
                location=location,
            )
            days_b = clamp_session_to_target(
                days_b,
                session_minutes=session_minutes,
                meta_by_id=meta_by_id,
                location=location,
            )
            phase_ab.append({"a": days_a, "b": days_b})
            phase_rationales.append(str(phase_out.get("rationale_vi") or "").strip())

        plan_days = [d.model_copy(deep=True) for d in phase_ab[0]["a"]]
        week_templates_dump = [
            {
                "a": [d.model_dump() for d in p["a"]],
                "b": [d.model_dump() for d in p["b"]],
            }
            for p in phase_ab
        ]
    elif free_home:
        want_knee = prefer_knee_pushups(
            location=location,
            no_equipment=no_equipment,
            pushups_max=pushups_max,
        )
        used_ids: set[int] = set()
        picks_by_day: dict[int, dict[str, list[int]]] = {}
        for ctx in day_contexts:
            idx = int(ctx["frame_day"].day_index)
            picks = deterministic_picks(
                ctx["day_blocks"],
                split_role=ctx["pick_role"],
                focus_slugs=focus_slugs,
                used_ids=used_ids,
                day_index=idx,
                prefer_knee=want_knee,
            )
            picks_by_day[idx] = picks
            used_ids.update(strength_ids_from_picks(picks))
        plan_days = _assemble_week_from_picks(
            db, day_contexts, picks_by_day, **assemble_kwargs
        )
        plan_days, volume_note, name_map, meta_by_id = _finish_generated_week(
            db, plan_days, name_map=name_map, meta_by_id=meta_by_id, **finish_kwargs
        )
        apply_free_home_finishes(
            plan_days,
            day_contexts=day_contexts,
            meta_by_id=meta_by_id,
            motive=foundation_motive or "build_habit",
            session_minutes=session_minutes,
            experience_level=level,
        )
    else:
        try:
            llm_days = pick_with_openai(week_payload, profile=profile_for_pick)
        except OpenAIPickError as exc:
            raise BadRequestError(exc.message) from exc

        llm_by_index: dict[int, dict[str, Any]] = {}
        for d in llm_days:
            try:
                llm_by_index[int(d.get("day_index"))] = d
            except (TypeError, ValueError):
                continue

        picks_by_day: dict[int, dict[str, list[int]]] = {}
        for ctx in day_contexts:
            idx = int(ctx["frame_day"].day_index)
            try:
                picks_by_day[idx] = picks_from_llm_day(
                    llm_by_index.get(idx),
                    ctx["day_blocks"],
                    split_role=ctx["pick_role"],
                    focus_slugs=focus_slugs,
                    slots=ctx.get("slots"),
                    experience_level=level,
                )
            except OpenAIPickError as exc:
                raise BadRequestError(exc.message) from exc
        plan_days = _assemble_week_from_picks(
            db, day_contexts, picks_by_day, **assemble_kwargs
        )
        plan_days, volume_note, name_map, meta_by_id = _finish_generated_week(
            db, plan_days, name_map=name_map, meta_by_id=meta_by_id, **finish_kwargs
        )

    nutrition = estimate_targets(payload)
    # Challenge uses 3 phase-aligned nutrition blocks (not fixed size-4 on 14 weeks).
    nutrition_block_size = BLOCK_SIZE_WEEKS

    if persist and not free_home:
        split_roles = [d.split_role for d in plan_days]
        blocks = (
            build_nutrition_blocks(
                payload,
                goal=str(goal),
                duration_weeks=duration_weeks,
                split_roles=split_roles,
                block_size=nutrition_block_size,
                week_ranges=CHALLENGE_PHASE_RANGES if curriculum else None,
            )
            if nutrition
            else []
        )
        if blocks and nutrition:
            meal_result = generate_meals_with_blocks(
                db,
                payload,
                blocks,
                plan_days,
                goal=str(goal),
                block_size=4 if curriculum else nutrition_block_size,
                include_deload_meals=curriculum,
            )
            plan_days = apply_nutrition_blocks_to_expanded_days(
                plan_days,
                meal_result.nutrition_blocks,
                sessions_per_week=len(plan_days),
                block_size=4 if curriculum else nutrition_block_size,
                deload_weeks=CHALLENGE_DELOAD_WEEKS if curriculum else None,
            )
        else:
            meal_result = generate_meals(
                db,
                payload,
                nutrition,
                plan_days=plan_days,
                goal=str(goal),
            )
            if meal_result.schedule and meal_result.templates_by_kind:
                plan_days = apply_meals_with_schedule(
                    plan_days,
                    meal_result.schedule,
                    meal_result.templates_by_kind,
                    foods_by_id=meal_result.foods_by_id,
                )
            else:
                plan_days = apply_meals_to_days(plan_days, meal_result.templates)
    else:
        meal_result = SimpleNamespace(
            warning_vi=None,
            nutrition_blocks=None,
            rest_day_template=None,
            schedule=None,
            templates_by_kind=None,
            templates=None,
            foods_by_id={},
        )
        if free_home:
            split_roles = [d.split_role for d in plan_days]

    schedule_summary = build_schedule_summary(
        frame,
        plan_days,
        session_minutes=session_minutes,
        location=location,
    )
    allowed_ids_by_day: dict[int, set[int]] = {}
    for ctx, day in zip(day_contexts, plan_days):
        ids: set[int] = set()
        for items in (ctx.get("shortlists") or {}).values():
            for item in items or []:
                try:
                    ids.add(int(item.id))
                except (TypeError, ValueError, AttributeError):
                    continue
        allowed_ids_by_day[int(day.day_number)] = ids
    schedule_summary["allowed_ids_by_day"] = {
        str(k): sorted(v)[:40] for k, v in allowed_ids_by_day.items()
    }
    schedule_summary["equipment_slugs"] = list(equipment_list)
    coach = (
        generate_coach_advice(payload, schedule_summary, exercise_names=name_map)
        if persist and not curriculum and not free_home
        else {"advice_vi": [], "used_openai": False, "swaps": []}
    )
    if persist and not curriculum and not free_home:
        plan_days = apply_schedule_swaps(
            plan_days, coach.get("swaps"), allowed_ids_by_day
        )
        plan_days = apply_duration_tweaks(
            plan_days, coach.get("duration_tweaks"), allowed_ids_by_day
        )
        plan_days = clamp_session_to_target(
            plan_days,
            session_minutes=session_minutes,
            meta_by_id=meta_by_id,
            location=location,
        )

    kcal = nutrition.target_calories if nutrition else None
    p = nutrition.protein_g if nutrition else None
    c = nutrition.carbs_g if nutrition else None
    f = nutrition.fat_g if nutrition else None
    title_goal = {
        "lose_weight": "giảm cân",
        "maintain": "giữ cân",
        "gain_weight": "tăng cân",
        "gain_muscle": "tăng cân",
    }.get(str(goal), str(GOAL_LABEL.get(str(goal), goal) or goal).lower())
    stamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    title = free_home_plan_title_vi(stamp) if free_home else f"Lịch tập {title_goal} {stamp}"
    labels = focus_labels_vi(list(payload.get("focus_areas") or []))
    wizard = build_wizard_inputs(
        payload,
        goal=str(goal),
        location=location,
        sessions=sessions_clamped,
        session_minutes=session_minutes,
        duration_weeks=duration_weeks,
        experience_level=level,
        no_equipment=no_equipment,
        equipment_list=equipment_list,
        focus_labels=labels,
    )
    desc = wizard["recap_vi"]

    extra_notes: list[str] = []
    if sessions_clamped < requested_sessions:
        extra_notes.append(
            f"Đã hạ {requested_sessions} buổi xuống {sessions_clamped} buổi/tuần theo sức phục hồi."
        )
    if session_minutes >= 90:
        extra_notes.append(
            f"Buổi {session_minutes} phút: đủ compound/isolation theo bảng phút + LISS cuối buổi "
            "(không nhồi thêm press/lateral)."
        )
    if policy.reason_vi:
        extra_notes.append(policy.reason_vi)
    if split_choice.reason_vi:
        extra_notes.append(split_choice.reason_vi)
    if capacity.reason_vi:
        extra_notes.append(capacity.reason_vi)
    extra_notes.extend(injury.notes_vi)
    if volume_note:
        extra_notes.append(volume_note)
    if location == "home" and _home_plan_has_load_selection(
        plan_days, meta_by_id, no_equipment=no_equipment
    ):
        from app.services.workout_generation.coach_notes import HOME_LOAD_INSIGHT_VI

        if HOME_LOAD_INSIGHT_VI not in extra_notes:
            extra_notes.append(HOME_LOAD_INSIGHT_VI)
    if nutrition and nutrition.notes_vi and not free_home:
        extra_notes.extend(nutrition.notes_vi)
    if meal_result.warning_vi:
        extra_notes.append(meal_result.warning_vi)

    food_body, food_tips = (
        pick_nutrition_copy(foundation_motive or "build_habit", seed=str(user_id or "") + stamp)
        if free_home
        else (None, [])
    )
    advice = list(coach.get("advice_vi") or [])
    if free_home:
        foundation_tips = [
            "Ít lần một hiệp không phải lịch yếu — lịch đang tôn trọng sức nền của bạn.",
            "Tháng đầu làm quen; tháng hai dày hơn một chút. Cứ xuất hiện đủ buổi là đang thắng.",
        ]
        for tip in reversed(foundation_tips):
            if tip not in advice:
                advice.insert(0, tip)
        for tip in reversed(food_tips):
            if tip and tip not in advice:
                advice.insert(0, tip)
    for note in reversed(extra_notes):
        if note and note not in advice:
            advice.insert(0, note)

    create = CreatePlanRequest(
        title_vi=title[:255],
        description_vi=desc,
        target_calories=kcal,
        target_protein_g=p,
        target_carbs_g=c,
        target_fat_g=f,
        source="ai",
        duration_weeks=duration_weeks,
        experience_level=level,
        strength_tier=capacity.strength_tier,
        challenge_100_days=challenge,
        days=plan_days,
    )
    settings = get_settings()
    checkin_days = 28 if curriculum else 14
    insights = {
        "overview": {
            "schedule_vi": (
                f"{sessions_clamped} buổi/tuần · {session_minutes} phút/buổi"
                + (
                    " · xây nền từ số 0 · 8 tuần (tháng 1 làm quen, tháng 2 tập chắc hơn)"
                    if free_home
                    else (
                        f" · Master `{frame.week_code}`"
                        + (" · thử thách 100 ngày" if curriculum else "")
                    )
                )
            ),
            "summary_vi": wizard.get("recap_vi") or f"Lịch {GOAL_LABEL.get(str(goal), goal)}.",
            "periodization_vi": (
                free_home_periodization_vi()
                if free_home
                else periodization_advice_vi(
                    resolve_overload_profile(level, strength_tier=capacity.strength_tier),
                    duration_weeks,
                    curriculum=curriculum,
                )
            ),
            "nutrition_vi": (
                food_body
                if free_home and food_body
                else (
                    _nutrition_insight_vi(nutrition, goal=str(goal))
                    if not meal_result.nutrition_blocks
                    else (
                        _nutrition_insight_vi_blocks(meal_result.nutrition_blocks, str(goal))
                        or _nutrition_insight_vi(nutrition, goal=str(goal))
                    )
                )
            ),
        },
        "advice_vi": advice,
        "inputs": wizard,
        "days": _meal_day_insights(plan_days),
        "nutrition": (
            {
                "tdee": nutrition.tdee,
                "target_calories": nutrition.target_calories,
                "protein_g": nutrition.protein_g,
                "carbs_g": nutrition.carbs_g,
                "fat_g": nutrition.fat_g,
                "goal_vi": GOAL_LABEL.get(str(goal), goal),
            }
            if nutrition
            else None
        ),
        "generator": (
            "free_home_bw_v1"
            if free_home
            else ("master_v1_14_challenge100" if curriculum else "master_v1_11_openai_pick")
        ),
        "frame_code": frame.code,
        "week_code": frame.week_code,
        "split_reason_vi": split_choice.reason_vi,
        "strength_tier": capacity.strength_tier,
        "effective_level": level,
        "conservative_volume": bool(capacity.conservative_volume),
        "focus_slugs": sorted(focus_slugs),
        "volume_meta": {str(k): v for k, v in meta_by_id.items()},
        "used_openai": bool(coach.get("used_openai")),
        "used_openai_pick": bool(not free_home),
        "challenge_100_days": challenge,
        "curriculum_12_weeks": False,
        "challenge_kind": "home_foundation" if free_home else ("challenge_100" if challenge else None),
        "generation_mode": "free_home" if free_home else None,
        "foundation_motive": foundation_motive if free_home else None,
        "kg_per_week": (
            parse_kg_per_week(payload, goal=str(goal))
            if str(goal) in {"lose_weight", "gain_weight"}
            else None
        ),
        "session_minutes": session_minutes,
    }
    if curriculum:
        insights["curriculum"] = curriculum_insight_payload(rationale_vi=phase_rationales)
        if week_templates_dump:
            insights["week_templates"] = week_templates_dump
        if challenge_variation_insight:
            insights["challenge_variation"] = challenge_variation_insight
    if home_gear_insight is not None:
        insights["home_gear"] = home_gear_insight
    if meal_result.nutrition_blocks:
        insights["nutrition_blocks"] = meal_result.nutrition_blocks
        insights["sessions_per_week"] = len(split_roles)
        # Challenge has uneven blocks; store marker for overview + check-in.
        insights["nutrition_block_size"] = 4 if curriculum else nutrition_block_size
        insights["nutrition_payload"] = {
            "gender": payload.get("gender"),
            "height_cm": payload.get("height_cm"),
            "age": payload.get("age"),
            "activity": payload.get("activity"),
            "goal": str(goal),
            "weight_kg": payload.get("weight_kg"),
            "kg_per_week": insights.get("kg_per_week"),
            "food_ids": list(payload.get("food_ids") or []),
            "ai_suggest_foods": payload.get("ai_suggest_foods"),
        }
        b0 = meal_result.nutrition_blocks[0]
        if b0.get("rest_day_nutrition"):
            insights["rest_day_nutrition"] = b0["rest_day_nutrition"]
        if b0.get("rest_day_meals"):
            insights["rest_day_meals"] = b0["rest_day_meals"]
        insights["next_nutrition_checkin_due"] = (
            date.today() + timedelta(days=checkin_days)
        ).isoformat()
        insights["nutrition_checkin_interval_days"] = checkin_days
    elif meal_result.rest_day_template and meal_result.schedule:
        rest = meal_result.schedule.rest
        insights["rest_day_nutrition"] = {
            "target_calories": rest.target_calories,
            "protein_g": rest.protein_g,
            "carbs_g": rest.carbs_g,
            "fat_g": rest.fat_g,
        }
        rest_food_ids = [m.food_id for m in meal_result.rest_day_template.meals]
        rest_foods: dict[int, Food] = {}
        if rest_food_ids:
            rest_foods = {
                int(f.id): f
                for f in db.query(Food).filter(Food.id.in_(rest_food_ids)).all()
            }
        insights["rest_day_meals"] = []
        for m in meal_result.rest_day_template.meals:
            food = rest_foods.get(int(m.food_id))
            servings = float(m.servings or 1)
            insights["rest_day_meals"].append(
                {
                    "food_id": m.food_id,
                    "name_vi": food.name_vi if food else None,
                    "meal_type": m.meal_type,
                    "servings": servings,
                    "calories": int(round((food.calories or 0) * servings)) if food else None,
                    "protein_g": (food.protein_g * servings) if food and food.protein_g else None,
                    "carbs_g": (food.carbs_g * servings) if food and food.carbs_g else None,
                    "fat_g": (food.fat_g * servings) if food and food.fat_g else None,
                    "notes_vi": m.notes_vi,
                }
            )
    preview_days = _preview_plan_days(plan_days, name_map)
    usage = {
        "month": "",
        "generation_count": 0,
        "qa_message_count": 0,
        "limit": None,
        "remaining": None,
        "unlimited": True,
        "price_vnd": 0,
        "model": settings.openai_model,
        "openai_configured": bool((settings.openai_api_key or "").strip()),
    }
    if not persist:
        return {
            "plan": None,
            "plan_id": None,
            "share_token": None,
            "share_url_path": None,
            "days": preview_days,
            "week_code": frame.week_code,
            "frame_code": frame.code,
            "sessions_requested": requested_sessions,
            "sessions_actual": sessions_clamped,
            "session_minutes": session_minutes,
            "split_overridden": split_choice.overridden,
            "split_reason_vi": split_choice.reason_vi,
            "insights": insights,
            "usage": usage,
        }
    detail = PlanService(db).create_plan(
        user_id,
        create,
        insights_json=insights,
    )
    token = detail.get("share_token")
    return {
        "plan": detail,
        "plan_id": detail.get("id"),
        "share_token": token,
        "share_url_path": f"/lich/{token}" if token else None,
        "usage": usage,
    }
