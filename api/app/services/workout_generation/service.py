"""Orchestrate rule-based workout plan generation."""

from __future__ import annotations

from collections import Counter
from types import SimpleNamespace
from typing import Any

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError
from app.models.entities import Food
from app.schemas.plans import CreatePlanRequest, PlanDayIn
from app.services.exercise_prescription import clamp_experience_level
from app.services.plan_service import PlanService
from app.services.periodization import periodization_advice_vi, resolve_overload_profile
from app.services.workout_generation.assemble import (
    collect_day_shortlists_for_prompt,
)
from app.services.workout_generation.capacity import resolve_capacity
from app.services.workout_generation.coach_advice import GOAL_VI as GOAL_LABEL
from app.services.workout_generation.fb_rotation import (
    effective_pick_role,
    fb_session_title,
    is_full_body_role,
)
from app.services.workout_generation.focus import (
    focus_labels_vi,
    focus_muscle_slugs,
    normalize_focus_areas,
)
from app.services.workout_generation.injury_filters import parse_injury_constraints
from app.services.workout_generation.frame_picker import pick_master_frame
from app.services.workout_generation.rule_picker import (
    deterministic_picks,
    merge_week_b_isolation_picks,
    stems_from_picks,
    strength_ids_from_picks,
)
from app.services.workout_generation.shortlist import (
    ShortlistItem,
    coerce_wizard_gen_equipment,
)
from app.services.workout_generation.session_duration import clamp_session_to_target
from app.services.workout_generation.session_policy import resolve_session_policy
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
    build_nutrition_blocks,
    estimate_targets,
    parse_kg_per_week,
)
from app.services.workout_generation.week_pipeline import (
    _assemble_week_from_picks,
    _finish_generated_week,
)
from app.services.workout_generation.wizard_inputs import (
    _home_plan_has_load_selection,
    _meal_day_insights,
    _nutrition_insight_vi,
    _nutrition_insight_vi_blocks,
    _preview_plan_days,
    build_wizard_inputs,
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
from app.services.schedule_spec_master import lookup_week_split, experience_to_master_key
























def generate_workout(
    db: Session,
    user_id: str | None,
    payload: dict[str, Any],
    *,
    persist: bool = True,
    commit: bool = True,
) -> dict[str, Any]:
    generation_mode = str(payload.get("generation_mode") or "").strip().lower()
    if generation_mode == "familiarization":
        from app.services.workout_generation.familiarization_curriculum import (
            generate_familiarization_workout,
        )

        return generate_familiarization_workout(
            db, user_id, payload, persist=persist, commit=commit
        )

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
    duration_weeks = int(payload.get("duration_weeks") or 14)
    curriculum = bool(
        payload.get("curriculum_12_weeks") or payload.get("challenge_100_days")
    )

    no_equipment = False
    ai_suggest_equipment = False
    try:
        equipment_list = coerce_wizard_gen_equipment(payload.get("equipment_list") or [])
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc
    if not equipment_list:
        raise BadRequestError(
            "Cần chọn dụng cụ: dây kháng lực, tạ đơn, hoặc xà đơn và vòng treo."
        )
    if not curriculum:
        raise BadRequestError("Chỉ tạo lịch Nhập môn hoặc Thử thách 100 ngày.")
    challenge = True
    location = "home"
    gender = str(payload.get("gender") or "male").strip().lower()
    baseline = payload.get("fitness_baseline") or {}
    if hasattr(baseline, "model_dump"):
        baseline = baseline.model_dump()
    if not isinstance(baseline, dict):
        baseline = {}
    if curriculum:
        from app.services.workout_generation.load_estimate import apply_challenge_load

        baseline = apply_challenge_load(
            baseline,
            weight_kg=payload.get("weight_kg"),
            gender=gender,
            experience_level=payload.get("experience_level"),
            equipment_list=equipment_list,
        )
    capacity = resolve_capacity(
        payload.get("experience_level"),
        baseline,
        sessions_per_week=sessions,
        gender=gender,
        weight_kg=payload.get("weight_kg"),
    )
    if curriculum and (
        capacity.effective_level <= 1 or capacity.strength_tier == "weak"
    ):
        from app.services.workout_generation.load_estimate import apply_challenge_load

        baseline = apply_challenge_load(
            baseline,
            weight_kg=payload.get("weight_kg"),
            gender=gender,
            experience_level=payload.get("experience_level"),
            equipment_list=equipment_list,
            easy=True,
        )
    try:
        pushups_max = int(baseline["pushups_max"]) if baseline.get("pushups_max") is not None else None
    except (TypeError, ValueError):
        pushups_max = None
    from app.services.workout_generation.skill_gate import resolve_skill_signals

    skill_signals = resolve_skill_signals(
        baseline,
        location=location,
        no_equipment=no_equipment,
        pushups_max=pushups_max,
    )
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
    focus_areas = normalize_focus_areas(list(payload.get("focus_areas") or []))
    payload["focus_areas"] = focus_areas
    focus_slugs = focus_muscle_slugs(focus_areas)
    goal = str(payload.get("goal") or "maintain")
    default_week = lookup_week_split(
        experience=experience_to_master_key(level),
        sessions=sessions_clamped,
        gender=gender,
        location=location,
        home_equip="with_equip",
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
            focus_areas=list(payload.get("focus_areas") or []),
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
            challenge=curriculum,
            focus_areas=focus_areas,
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
        challenge=curriculum,
    )
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
        "challenge_session": curriculum,
        "focus_areas": focus_areas,
    }
    finish_kwargs: dict[str, Any] = {
        "day_contexts": day_contexts,
        "session_minutes": session_minutes,
        "location": location,
        "level": level,
        "capacity": capacity,
        "focus_slugs": focus_slugs,
        "focus_areas": focus_areas,
        "goal": goal,
        "extra_goals": extra_goals,
        "policy": policy,
        "no_equipment": no_equipment,
        "equipment_list": equipment_list,
        "fitness_baseline": baseline,
        "challenge_session": curriculum,
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
    if curriculum:
        from app.services.workout_generation.skill_gate import (
            apply_skill_gate_to_week,
            exempt_stems,
        )

        avoid_ids: list[int] = []
        avoid_stems: list[str] = []
        phase_ab: list[dict[str, list[PlanDayIn]]] = []
        challenge_variation_insight = {
            "changed_days": 0,
            "unchanged_no_alternative": [],
        }
        for phase_i, phase_meta in enumerate(MESOCYCLE_PHASES):
            lo, hi = CHALLENGE_PHASE_RANGES[phase_i]
            skip_stems = exempt_stems(phase_i, skill_signals)
            phase_avoid_ids = list(dict.fromkeys(avoid_ids))
            phase_avoid_stems = [
                s for s in dict.fromkeys(avoid_stems) if s not in skip_stems
            ]
            phase_week = apply_skill_gate_to_week(week_payload, phase_i, skill_signals)
            gated_by_idx = {}
            for d in phase_week:
                try:
                    gated_by_idx[int(d.get("day_index"))] = d
                except (TypeError, ValueError):
                    continue
            picks_a_by: dict[int, dict[str, list[int]]] = {}
            picks_b_by: dict[int, dict[str, list[int]]] = {}
            week_used: set[int] = set()
            for ctx in day_contexts:
                idx = int(ctx["frame_day"].day_index)
                gated_day = gated_by_idx.get(idx) or {}
                gated_blocks = gated_day.get("blocks") or ctx["day_blocks"]
                gated_slots = gated_day.get("slots") or ctx.get("slots")
                picks_a = deterministic_picks(
                    gated_blocks,
                    split_role=ctx["pick_role"],
                    focus_slugs=focus_slugs,
                    used_ids=week_used,
                    avoid_ids=set(phase_avoid_ids),
                    avoid_stems=set(phase_avoid_stems),
                    day_index=idx,
                    session_minutes=session_minutes,
                    experience_level=level,
                    focus_areas=focus_areas,
                )
                week_used.update(strength_ids_from_picks(picks_a))
                picks_b = merge_week_b_isolation_picks(
                    picks_a,
                    None,
                    gated_blocks,
                    split_role=ctx["pick_role"],
                    focus_slugs=focus_slugs,
                    avoid_ids=phase_avoid_ids,
                    avoid_stems=phase_avoid_stems,
                    slots=gated_slots,
                )
                picks_a_by[idx] = picks_a
                picks_b_by[idx] = picks_b
                if picks_b != picks_a:
                    challenge_variation_insight["changed_days"] += 1
                else:
                    from app.services.workout_generation.session_templates import (
                        slot_allows_week_b_swap,
                    )

                    raw_slots = picks_a.get("_slot_picks") or {}
                    a_slots = dict(raw_slots) if isinstance(raw_slots, dict) else {}
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
                blocks = (gated_by_idx.get(idx) or {}).get("blocks") or ctx["day_blocks"]
                avoid_ids.extend(strength_ids_from_picks(picks_a_by.get(idx)))
                avoid_ids.extend(strength_ids_from_picks(picks_b_by.get(idx)))
                for stem in stems_from_picks(picks_a_by.get(idx), blocks):
                    if stem in skip_stems:
                        continue
                    avoid_stems.append(stem)
                for stem in stems_from_picks(picks_b_by.get(idx), blocks):
                    if stem in skip_stems:
                        continue
                    avoid_stems.append(stem)

            days_a = _assemble_week_from_picks(
                db, day_contexts, picks_a_by, **assemble_kwargs
            )
            days_a, vnote, name_map, meta_by_id = _finish_generated_week(
                db,
                days_a,
                name_map=name_map,
                meta_by_id=meta_by_id,
                **finish_kwargs,
                phase_index=phase_i,
            )
            if vnote:
                volume_note = vnote
            b_differs = any(picks_b_by[i] != picks_a_by[i] for i in picks_a_by)
            if b_differs:
                days_b = _assemble_week_from_picks(
                    db, day_contexts, picks_b_by, **assemble_kwargs
                )
                days_b, vnote, name_map, meta_by_id = _finish_generated_week(
                    db,
                    days_b,
                    name_map=name_map,
                    meta_by_id=meta_by_id,
                    **finish_kwargs,
                    phase_index=phase_i,
                )
                if vnote:
                    volume_note = vnote
            else:
                days_b = [d.model_copy(deep=True) for d in days_a]
            days_a = apply_phase_rpe(
                days_a,
                phase_i,
                meta_by_id=meta_by_id,
                focus_slugs=focus_slugs,
                experience_level=level,
            )
            days_b = apply_phase_rpe(
                days_b,
                phase_i,
                meta_by_id=meta_by_id,
                focus_slugs=focus_slugs,
                experience_level=level,
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

        plan_days = [d.model_copy(deep=True) for d in phase_ab[0]["a"]]
        week_templates_dump = [
            {
                "a": [d.model_dump() for d in p["a"]],
                "b": [d.model_dump() for d in p["b"]],
            }
            for p in phase_ab
        ]

    payload["sessions_per_week"] = sessions_clamped
    payload["session_minutes"] = session_minutes
    nutrition = estimate_targets(payload)
    nutrition_block_size = BLOCK_SIZE_WEEKS

    if persist:
        split_roles = [d.split_role for d in plan_days]
        blocks = (
            build_nutrition_blocks(
                payload,
                goal=str(goal),
                duration_weeks=duration_weeks,
                split_roles=split_roles,
                block_size=nutrition_block_size,
                week_ranges=CHALLENGE_PHASE_RANGES,
                experience_level=level,
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
    title = f"Lịch tập {title_goal} {stamp}"
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
    if nutrition and nutrition.notes_vi:
        extra_notes.extend(nutrition.notes_vi)
    if meal_result.warning_vi:
        extra_notes.append(meal_result.warning_vi)

    advice: list[str] = []
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
    checkin_days = 28 if curriculum else 14
    insights = {
        "overview": {
            "schedule_vi": (
                f"{sessions_clamped} buổi/tuần · {session_minutes} phút/buổi"
                + (
                    f" · Master `{frame.week_code}`"
                    + (" · thử thách 100 ngày" if curriculum else "")
                )
            ),
            "summary_vi": wizard.get("recap_vi") or f"Lịch {GOAL_LABEL.get(str(goal), goal)}.",
            "periodization_vi": periodization_advice_vi(
                resolve_overload_profile(level, strength_tier=capacity.strength_tier),
                duration_weeks,
                curriculum=curriculum,
                experience_level=level,
                goal=str(goal) if goal else None,
            ),
            "nutrition_vi": (
                _nutrition_insight_vi(
                    nutrition,
                    goal=str(goal),
                    experience_level=level if curriculum else None,
                )
                if not meal_result.nutrition_blocks
                else (
                    _nutrition_insight_vi_blocks(
                        meal_result.nutrition_blocks,
                        str(goal),
                        experience_level=level if curriculum else None,
                    )
                    or _nutrition_insight_vi(
                        nutrition,
                        goal=str(goal),
                        experience_level=level if curriculum else None,
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
            "master_v1_14_challenge100"
        ),
        "frame_code": frame.code,
        "week_code": frame.week_code,
        "split_reason_vi": split_choice.reason_vi,
        "strength_tier": capacity.strength_tier,
        "effective_level": level,
        "conservative_volume": bool(capacity.conservative_volume),
        "focus_slugs": sorted(focus_slugs),
        "volume_meta": {
            str(k): (v.as_insight_dict() if isinstance(v, ShortlistItem) else v)
            for k, v in meta_by_id.items()
        },
        "challenge_100_days": challenge,
        "curriculum_12_weeks": False,
        "challenge_kind": "challenge_100" if challenge else None,
        "generation_mode": None,
        "foundation_motive": None,
        "kg_per_week": (
            parse_kg_per_week(payload, goal=str(goal))
            if str(goal) in {"lose_weight", "gain_weight"}
            else None
        ),
        "session_minutes": session_minutes,
    }
    if curriculum:
        from app.services.workout_generation.phase_comments import challenge_phase_copy

        phase_copy = challenge_phase_copy(wizard)
        insights["curriculum"] = curriculum_insight_payload(
            rationale_vi=[row["rationale_vi"] for row in phase_copy],
            blurb_vi=[row["blurb_vi"] for row in phase_copy],
            label_vi=[row["label_vi"] for row in phase_copy],
            knowledge_refs=[row["knowledge_refs"] for row in phase_copy],
        )
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
                    "image_url": getattr(food, "image_url", None) if food else None,
                    "serving_size": food.serving_size if food else None,
                    "serving_grams": food.serving_grams if food else None,
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
        commit=commit,
    )
    token = detail.get("share_token")
    return {
        "plan": detail,
        "plan_id": detail.get("id"),
        "share_token": token,
        "share_url_path": f"/lich/{token}" if token else None,
        "usage": usage,
    }
