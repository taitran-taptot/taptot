"""Assemble + finish a generated training week."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import Exercise, MuscleGroup
from app.schemas.plans import PlanDayIn
from app.services.workout_generation.assemble import assemble_day, inject_main_primer_warmup
from app.services.workout_generation.coverage import repair_plan_day_upper_pull
from app.services.workout_generation.muscle_quotas import reorder_main_section_exercises
from app.services.workout_generation.session_duration import (
    clamp_session_to_target,
    refill_thin_days,
    top_up_session_minutes,
)
from app.services.workout_generation.shortlist import is_home_denied_exercise
from app.services.workout_generation.weekly_volume import apply_weekly_dose, recap_l1_session_sets

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

