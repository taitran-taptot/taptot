"""Assemble PlanDayIn from frame days + picked exercise ids."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.schemas.plans import PlanDayIn, PlanExerciseIn
from app.services.exercise_prescription import get_prescription
from app.services.workout_generation.coach_notes import (
    PRIMER_NOTE_BW_VI,
    PRIMER_NOTE_LOADED_VI,
    PRIMER_TIMED_NOTE_VI,
    hold_note_vi,
    load_kind_for_item,
    looks_loaded,
    working_note_vi,
)
from app.services.session_blocks import BlockSpec, get_master_session_recipe
from app.core.exceptions import BadRequestError
from app.services.workout_generation.fb_rotation import is_full_body_role
from app.services.workout_generation.dose_bounds import (
    clamp_openai_dose,
    default_reps_label,
    dose_bounds_for_item,
    half_working_reps_label,
    primer_reps_from_baseline,
)
from app.services.workout_generation.effort_mode import exercise_effort_mode
from app.services.workout_generation.openai_picker import DOSE_PICKS_KEY
from app.services.workout_generation.muscle_quotas import reorder_main_section_exercises
from app.services.workout_generation.repair import repair_block_picks
from app.services.workout_generation.session_duration import fill_session_to_target
from app.services.workout_generation.shortlist import (
    ShortlistItem,
    build_shortlist,
    query_filtered_exercises,
    shortlist_to_prompt_dicts,
)
from app.services.workout_generation.split_map import normalize_split_role
from app.services.workout_rest import default_rest_seconds, timed_block_prescription
from app.services.workout_generation.free_home_curriculum import free_home_session_dose

_STRENGTH_BLOCK_KEYS = frozenset({"compound", "accessory", "resistance", "conditioning"})


def _target_count(block: BlockSpec) -> int:
    if block.count_max <= 0:
        return 0
    return block.count_max


def _is_timed_prescription(reps: str | int | None) -> bool:
    s = str(reps or "").strip().lower()
    return any(tok in s for tok in ("phút", "phut", "min", "giây", "giay", "sec"))


def inject_main_primer_warmup(
    day: PlanDayIn,
    *,
    meta_by_id: dict[int, Any] | None = None,
    no_equipment: bool = False,
    fitness_baseline: dict[str, Any] | None = None,
    home_session: bool = False,
    experience_level: int | None = None,
    free_home: bool = False,
    session_minutes: int | None = None,
) -> PlanDayIn:
    """Warmup is exactly 2 slots: 1 stretch + first main lift as primer (1–2 sets)."""
    warmup = [ex for ex in day.exercises if (ex.section or "") == "warmup"]
    mains = [ex for ex in day.exercises if (ex.section or "main") == "main"]
    rest = [ex for ex in day.exercises if (ex.section or "") != "warmup"]
    if not mains:
        return day
    first = mains[0]
    # This function is called before and after duration filling; replace an existing
    # primer instead of appending a duplicate on the second pass.
    warmup = [
        ex for ex in warmup if int(ex.exercise_id) != int(first.exercise_id)
    ]
    timed = _is_timed_prescription(first.reps)
    meta = meta_by_id.get(int(first.exercise_id)) if meta_by_id else None
    loaded = looks_loaded(meta, no_equipment=no_equipment)
    if home_session:
        half = half_working_reps_label(first.reps)
        if half is not None:
            primer_reps = half
        elif timed:
            primer_reps = half_working_reps_label("30 giây") or "15 giây"
        else:
            scaled = primer_reps_from_baseline(
                meta or {},
                fitness_baseline,
                no_equipment=no_equipment,
                home_session=home_session,
                experience_level=experience_level,
            )
            primer_reps = str(scaled) if scaled is not None else "4"
    elif timed:
        primer_reps = "20–30 giây"
    elif loaded:
        primer_reps = "4"
    else:
        scaled = primer_reps_from_baseline(
            meta or {},
            fitness_baseline,
            no_equipment=no_equipment,
            home_session=home_session,
            experience_level=experience_level,
        )
        primer_reps = str(scaled) if scaled is not None else "4"
    primer_sets = 2
    if free_home:
        primer_sets = int(
            free_home_session_dose(session_minutes or 45).get("primer_sets") or 2
        )
    primer_rest = 60 if home_session else (30 if timed else 45)
    primer = PlanExerciseIn(
        exercise_id=int(first.exercise_id),
        sets=primer_sets,
        reps=primer_reps,
        rest_seconds=primer_rest,
        section="warmup",
        notes_vi=(
            PRIMER_TIMED_NOTE_VI
            if timed
            else (PRIMER_NOTE_LOADED_VI if loaded else PRIMER_NOTE_BW_VI)
        ),
        sort_order=0,
    )
    if not warmup:
        new_wu = [primer]
    else:
        if home_session:
            for ex in warmup:
                if int(getattr(ex, "rest_seconds", 0) or 0) < 60:
                    ex.rest_seconds = 60
        new_wu = [*warmup, primer]
    day.exercises = new_wu + rest
    for i, ex in enumerate(day.exercises, start=1):
        ex.sort_order = i
    return day


def _recipe_for_day(
    *,
    location: str | None,
    session_minutes: int,
    split_role: str | None,
    experience_level: int | None = None,
    cardio_on_lift_days: bool = True,
    liss_finisher: bool = False,
    no_equipment: bool = False,
) -> list[BlockSpec]:
    loc = (location or "gym").strip().lower()
    return get_master_session_recipe(
        location=loc,
        session_minutes=session_minutes,
        split_role=split_role,
        experience_level=experience_level,
        cardio_on_lift_days=cardio_on_lift_days,
        liss_finisher=liss_finisher,
        no_equipment=no_equipment,
    )


def _build_day_shortlists(
    db: Session,
    *,
    recipe: list[BlockSpec],
    role: str | None,
    experience_level: int,
    equipment_slugs: list[str],
    no_equipment: bool,
    ai_suggest_equipment: bool,
    exclude_ids: set[int],
    location: str | None,
    focus_slugs: frozenset[str] | None,
    goal: str | None,
    injury: Any,
    pushups_max: int | None = None,
    fitness_baseline: dict[str, Any] | None = None,
) -> dict[str, list[ShortlistItem]]:
    shortlists: dict[str, list[ShortlistItem]] = {}
    for block in recipe:
        if block.count_max <= 0:
            shortlists[block.block_key] = []
            continue
        shortlists[block.block_key] = build_shortlist(
            db,
            block=block,
            split_role=role,
            experience_level=experience_level,
            equipment_slugs=equipment_slugs,
            no_equipment=no_equipment,
            ai_suggest_equipment=ai_suggest_equipment,
            exclude_ids=exclude_ids,
            location=location,
            focus_slugs=focus_slugs,
            goal=goal,
            injury=injury,
            pushups_max=pushups_max,
            fitness_baseline=fitness_baseline,
        )
    return shortlists


def assemble_day(
    db: Session,
    *,
    frame_day: Any,
    day_number: int,
    experience_level: int,
    session_minutes: int,
    equipment_slugs: list[str],
    no_equipment: bool,
    ai_suggest_equipment: bool,
    picks_by_block: dict[str, list[int]] | None,
    location: str | None = None,
    focus_slugs: frozenset[str] | None = None,
    goal: str | None = None,
    extra_goals: list[str] | None = None,
    cardio_on_lift_days: bool = True,
    liss_finisher: bool = False,
    split_role: str | None = None,
    exclude_ids: set[int] | None = None,
    title_override: str | None = None,
    injury: Any = None,
    strict_openai_picks: bool = False,
    precomputed_shortlists: dict[str, list[ShortlistItem]] | None = None,
    pushups_max: int | None = None,
    fitness_baseline: dict[str, Any] | None = None,
    free_home: bool = False,
) -> PlanDayIn:
    role = split_role or getattr(frame_day, "split_role", None)
    home_session = str(location or "").strip().lower() == "home"
    interval_cardio = home_session
    free_home_on = bool(free_home)
    fh_dose = free_home_session_dose(session_minutes) if free_home_on else None
    recipe = _recipe_for_day(
        location=location,
        session_minutes=session_minutes,
        split_role=role,
        experience_level=experience_level,
        cardio_on_lift_days=cardio_on_lift_days,
        liss_finisher=liss_finisher,
        no_equipment=no_equipment,
    )
    used: set[int] = set(exclude_ids or ())
    exercises: list[PlanExerciseIn] = []
    sort = 0
    ramp_applied = False
    picks_by_block = picks_by_block or {}
    dose_by_exercise = dict(picks_by_block.get(DOSE_PICKS_KEY) or {})

    shortlists = precomputed_shortlists or _build_day_shortlists(
        db,
        recipe=recipe,
        role=role,
        experience_level=experience_level,
        equipment_slugs=equipment_slugs,
        no_equipment=no_equipment,
        ai_suggest_equipment=ai_suggest_equipment,
        exclude_ids=used,
        location=location,
        focus_slugs=focus_slugs,
        goal=goal,
        injury=injury,
        pushups_max=pushups_max,
        fitness_baseline=fitness_baseline,
    )
    meta_by_id: dict[int, ShortlistItem] = {}
    from app.services.workout_generation.home_gear_priority import (
        home_gear_active,
        user_gear_set,
    )

    user_gear: set[str] | None = (
        user_gear_set(equipment_slugs)
        if home_gear_active(location, no_equipment=no_equipment, equipment_slugs=equipment_slugs)
        else None
    )

    for block in recipe:
        raw = list(picks_by_block.get(block.block_key) or [])
        loc_home = (location or "").strip().lower() == "home"
        home_bw = loc_home and bool(no_equipment)
        strength_block = block.block_key in {"compound", "accessory", "resistance"}
        chosen = repair_block_picks(
            block=block,
            picked_ids=raw,
            shortlist=shortlists.get(block.block_key, []),
            used_ids=used,
            fill_missing=(not strict_openai_picks) or home_bw,
            user_gear=user_gear if strength_block else None,
        )
        if not chosen and not block.is_optional and _target_count(block) > 0:
            if home_bw:
                raise BadRequestError(
                    "Kho bài bodyweight không đủ cho buổi này. Thử tạo lại."
                )
            if strict_openai_picks:
                raise BadRequestError(
                    f"OpenAI không chọn đủ bài cho block `{block.block_key}`. Thử tạo lại."
                )
            chosen = repair_block_picks(
                block=block,
                picked_ids=[],
                shortlist=shortlists.get(block.block_key, []),
                used_ids=used,
                fill_missing=True,
                user_gear=user_gear if strength_block else None,
            )

        item_by_id = {i.id: i for i in shortlists.get(block.block_key, [])}
        meta_by_id.update(item_by_id)
        for eid in chosen:
            meta = item_by_id.get(eid)
            move_role = meta.movement_role if meta else block.movement_role
            effort_mode = exercise_effort_mode(
                meta,
                movement_role=move_role,
                plan_section=block.plan_section,
            )
            rx = get_prescription(
                db, experience_level, move_role, goal=goal, extra_goals=extra_goals
            )
            working = (block.plan_section or "") == "main" and (move_role or "") in {
                "compound",
                "isolation",
                "resistance",
            }
            timed = timed_block_prescription(
                block_key=block.block_key,
                plan_section=block.plan_section,
                movement_role=move_role,
                duration_min=block.duration_min_minutes,
                duration_max=block.duration_max_minutes,
                interval_cardio=interval_cardio,
                experience_level=experience_level,
                mobility_sets=(
                    int(fh_dose["stretch_sets"])
                    if fh_dose and (block.plan_section or "") == "warmup"
                    else (
                        int(fh_dose["cooldown_sets"])
                        if fh_dose and (block.plan_section or "") == "cooldown"
                        else None
                    )
                ),
            )
            extra_rest: int | None = None
            timed_notes: str | None = None
            if timed:
                sets, reps, extra_rest, timed_notes = timed
                rpe = 0
            elif effort_mode == "hold":
                bounds = dose_bounds_for_item(
                    meta or {},
                    experience_level=experience_level,
                    fitness_baseline=fitness_baseline,
                    plan_section=block.plan_section,
                    no_equipment=no_equipment,
                    home_session=home_session,
                )
                hold_default = int(
                    round((int(bounds["seconds_min"]) + int(bounds["seconds_max"])) / 10) * 5
                )
                sets, reps, extra_rest, timed_notes = (
                    3,
                    f"{hold_default} giây",
                    45 if experience_level <= 1 else 60,
                    hold_note_vi(f"{hold_default} giây"),
                )
                rpe = 0
                timed = (sets, reps, extra_rest, timed_notes)
            elif home_session:
                # Home main work: fitness / presets via dose_bounds — skip gym seed tables.
                sets, reps, rpe = 3, "12", 0
                if fh_dose:
                    sets = int(fh_dose["main_sets"])
                    extra_rest = int(fh_dose["main_rest"])
            elif rx and working:
                sets, reps, rpe = rx
            elif rx:
                sets, reps, rpe = rx.sets, rx.reps, 0
            else:
                sets, reps, rpe = 3, "12", 0

            if not timed:
                bounds = dose_bounds_for_item(
                    meta or {
                        "movement_role": move_role,
                    },
                    experience_level=experience_level,
                    fitness_baseline=fitness_baseline,
                    plan_section=block.plan_section,
                    no_equipment=no_equipment,
                    home_session=home_session,
                )
                default_reps = (
                    default_reps_label(bounds)
                    if home_session and str(bounds.get("work_mode")) == "reps"
                    else str(reps)
                )
                # Home: always use fitness/preset dose, never OpenAI under/over-shoot.
                proposal = None if home_session else dose_by_exercise.get(str(eid))
                sets, reps = clamp_openai_dose(
                    proposal,
                    bounds,
                    default_sets=int(sets),
                    default_reps=default_reps,
                )
                if fh_dose and working:
                    sets = int(fh_dose["main_sets"])

            kind = load_kind_for_item(meta, no_equipment=no_equipment)
            notes_parts: list[str] = []
            if timed and timed_notes:
                notes_parts.append(timed_notes)
            elif effort_mode == "hold":
                notes_parts.append(hold_note_vi(reps))
            elif working:
                notes_parts.append(
                    working_note_vi(
                        reps,
                        kind=kind,
                        include_progress=(
                            block.block_key in {"compound", "resistance"}
                            and not ramp_applied
                        ),
                        rpe=rpe or 7,
                    )
                )
                if block.block_key in {"compound", "resistance"}:
                    ramp_applied = True
            notes = (
                ". ".join(part.strip().rstrip(".") for part in notes_parts) + "."
                if notes_parts
                else None
            )

            sort += 1
            exercises.append(
                PlanExerciseIn(
                    exercise_id=eid,
                    sets=sets if isinstance(sets, int) else 3,
                    reps=reps,
                    rest_seconds=(
                        extra_rest
                        if extra_rest is not None
                        else default_rest_seconds(
                            move_role, experience_level=experience_level
                        )
                    ),
                    section=block.plan_section,  # type: ignore[arg-type]
                    notes_vi=notes,
                    sort_order=sort,
                )
            )
            used.add(eid)

    exercises = reorder_main_section_exercises(
        role,
        exercises,
        meta_by_id,
        focus_slugs=focus_slugs,
    )
    for i, ex in enumerate(exercises, start=1):
        ex.sort_order = i

    stored_role = getattr(frame_day, "split_role", None)
    if is_full_body_role(stored_role):
        stored_role = "fb"
    day = PlanDayIn(
        day_number=day_number,
        title_vi=title_override or frame_day.label_vi,
        notes_vi=getattr(frame_day, "notes_vi", None),
        split_role=stored_role,
        exercises=exercises,
        meals=[],
    )
    inject_main_primer_warmup(
        day,
        meta_by_id=meta_by_id,
        no_equipment=no_equipment,
        fitness_baseline=fitness_baseline,
        home_session=home_session,
        experience_level=experience_level,
        free_home=free_home_on,
        session_minutes=session_minutes,
    )
    day = fill_session_to_target(
        day,
        session_minutes=session_minutes,
        recipe=recipe,
        shortlists=shortlists,
        meta_by_id=meta_by_id,
        used_ids=used,
        db=db,
        experience_level=experience_level,
        goal=goal,
        extra_goals=extra_goals,
        fitness_baseline=fitness_baseline,
        no_equipment=no_equipment,
        home_session=home_session,
    )
    day.exercises = reorder_main_section_exercises(
        role,
        day.exercises,
        meta_by_id,
        focus_slugs=focus_slugs,
    )
    inject_main_primer_warmup(
        day,
        meta_by_id=meta_by_id,
        no_equipment=no_equipment,
        fitness_baseline=fitness_baseline,
        home_session=home_session,
        experience_level=experience_level,
        free_home=free_home_on,
        session_minutes=session_minutes,
    )
    for i, ex in enumerate(day.exercises, start=1):
        ex.sort_order = i
    return day


_STRENGTH_SLOT_ROLES = frozenset({"compound", "isolation", "resistance"})
_SLOT_COVERED_BLOCKS = frozenset({"compound", "accessory", "resistance"})
_GPT_BLOCK_KEYS = frozenset(
    {"compound", "accessory", "resistance", "conditioning", "core", "cardio"}
)


def _slot_counts_from_blocks(
    blocks: list[dict],
    *,
    location: str | None,
) -> tuple[int, int]:
    by = {str(b.get("block_key")): b for b in blocks}
    loc = (location or "gym").strip().lower()
    if loc == "home" or "resistance" in by:
        n = int((by.get("resistance") or {}).get("count_max") or 0)
        if n <= 1:
            return n, 0
        if n == 2:
            return 1, 1
        return 2, n - 2
    compound_n = int((by.get("compound") or {}).get("count_max") or 0)
    accessory_n = int((by.get("accessory") or {}).get("count_max") or 0)
    return compound_n, accessory_n


def _shortlist_item_from_pool_row(row: dict[str, Any]) -> ShortlistItem | None:
    try:
        eid = int(row.get("id"))
    except (TypeError, ValueError):
        return None
    return ShortlistItem(
        id=eid,
        name_vi=str(row.get("name_vi") or ""),
        movement_role=row.get("movement_role"),
        movement_pattern=row.get("pattern") or row.get("movement_pattern"),
        muscle_slug=str(row.get("muscle") or row.get("muscle_slug") or ""),
        difficulty=int(row.get("difficulty") or 0),
        name_en=row.get("name_en"),
        equipment_slugs=frozenset(
            str(s).strip().lower() for s in (row.get("equipment_slugs") or ()) if str(s).strip()
        ),
    )


def collect_day_shortlists_for_prompt(
    db: Session,
    *,
    frame_day: Any,
    experience_level: int,
    session_minutes: int,
    equipment_slugs: list[str],
    no_equipment: bool,
    ai_suggest_equipment: bool,
    location: str | None = None,
    focus_slugs: frozenset[str] | None = None,
    cardio_on_lift_days: bool = True,
    liss_finisher: bool = False,
    goal: str | None = None,
    extra_goals: list[str] | None = None,
    split_role: str | None = None,
    exclude_ids: set[int] | None = None,
    injury: Any = None,
    out_shortlists: dict[str, list[ShortlistItem]] | None = None,
    out_slots: list[dict] | None = None,
    pushups_max: int | None = None,
    fitness_baseline: dict[str, Any] | None = None,
    week_role_count: int = 1,
    pick_variants: int = 1,
    out_gear_meta: dict[str, dict[str, int]] | None = None,
) -> list[dict]:
    """Recipe blocks + slot pools for OpenAI pick.

    Home + gear: slot pools are gear-first (``home_gear_priority.tier_slot_pool``);
    bodyweight rows only top up when the slot has fewer than
    ``min_gear_pool(week_role_count, pick_variants)`` gear options.
    """
    from app.services.exercise_catalog_classify import roles_for_block
    from app.services.workout_generation.home_gear_priority import (
        home_gear_active,
        min_gear_pool,
        sort_gear_first,
        tier_slot_pool,
        user_gear_set,
    )
    from app.services.workout_generation.openai_picker import clamp_pick_count
    from app.services.workout_generation.session_templates import (
        pools_for_slots,
        slot_prefer_rank,
        slots_for_session,
        slots_to_prompt,
        uses_session_templates,
    )

    role = split_role or getattr(frame_day, "split_role", None)
    gear_on = home_gear_active(
        location, no_equipment=no_equipment, equipment_slugs=equipment_slugs
    )
    user_gear = user_gear_set(equipment_slugs) if gear_on else set()
    gear_need = min_gear_pool(week_role_count, pick_variants)
    recipe = _recipe_for_day(
        location=location,
        session_minutes=session_minutes,
        split_role=role,
        experience_level=experience_level,
        cardio_on_lift_days=cardio_on_lift_days,
        liss_finisher=liss_finisher,
        no_equipment=no_equipment,
    )
    used: set[int] = set(exclude_ids or ())
    shortlists = _build_day_shortlists(
        db,
        recipe=recipe,
        role=role,
        experience_level=experience_level,
        equipment_slugs=equipment_slugs,
        no_equipment=no_equipment,
        ai_suggest_equipment=ai_suggest_equipment,
        exclude_ids=used,
        location=location,
        focus_slugs=focus_slugs,
        goal=goal,
        injury=injury,
        pushups_max=pushups_max,
        fitness_baseline=fitness_baseline,
    )
    loc = (location or "gym").strip().lower()

    def _uncapped_block(block: BlockSpec) -> list[ShortlistItem]:
        try:
            items = query_filtered_exercises(
                db,
                split_role=role,
                experience_level=experience_level,
                equipment_slugs=equipment_slugs,
                no_equipment=no_equipment,
                ai_suggest_equipment=ai_suggest_equipment,
                exclude_ids=used,
                location=location,
                injury=injury,
                pushups_max=pushups_max,
                fitness_baseline=fitness_baseline,
                movement_roles=roles_for_block(
                    block.movement_role, location=loc or location
                ),
                block_key=block.block_key,
                count_max=int(block.count_max or 0),
            )
        except (TypeError, AttributeError, ValueError):
            return list(shortlists.get(block.block_key) or [])
        return items or list(shortlists.get(block.block_key) or [])

    for block in recipe:
        if block.block_key in {"core", "cardio", "conditioning"} and block.count_max > 0:
            shortlists[block.block_key] = _uncapped_block(block)

    prompt_slots: list[dict] = []
    if uses_session_templates(role):
        candidates: list[ShortlistItem] = []
        try:
            candidates = query_filtered_exercises(
                db,
                split_role=role,
                experience_level=experience_level,
                equipment_slugs=equipment_slugs,
                no_equipment=no_equipment,
                ai_suggest_equipment=ai_suggest_equipment,
                exclude_ids=used,
                location=location,
                injury=injury,
                pushups_max=pushups_max,
                fitness_baseline=fitness_baseline,
                movement_roles=_STRENGTH_SLOT_ROLES,
                block_key="compound" if loc != "home" else "resistance",
                count_max=4,
            )
        except (TypeError, AttributeError, ValueError):
            candidates = []
        if not candidates:
            for key in ("compound", "accessory", "resistance"):
                candidates.extend(shortlists.get(key) or [])
        compound_n, accessory_n = _slot_counts_from_blocks(
            [
                {
                    "block_key": b.block_key,
                    "count_max": b.count_max,
                }
                for b in recipe
            ],
            location=loc,
        )
        # Prefer clamped recipe counts after we know shortlist sizes.
        by_key_counts = {
            b.block_key: clamp_pick_count(
                int(b.count_max or 0),
                max(1, len(shortlists.get(b.block_key) or [])),
            )
            if (shortlists.get(b.block_key) and b.count_max > 0)
            else int(b.count_max or 0)
            for b in recipe
        }
        if loc == "home" or "resistance" in by_key_counts:
            n = int(by_key_counts.get("resistance") or 0)
            if n <= 1:
                compound_n, accessory_n = n, 0
            elif n == 2:
                compound_n, accessory_n = 1, 1
            else:
                compound_n, accessory_n = 2, n - 2
        else:
            compound_n = int(by_key_counts.get("compound") or compound_n)
            accessory_n = int(by_key_counts.get("accessory") or accessory_n)

        session_slots = slots_for_session(
            role,
            compound_n=compound_n,
            accessory_n=accessory_n,
            location=loc if loc in {"home", "gym"} else "gym",
            focus_slugs=focus_slugs,
            day_index=int(getattr(frame_day, "day_index", 0) or 0),
            allow_bar_moves=loc != "home" and not no_equipment,
            experience_level=experience_level,
            no_equipment=no_equipment,
        )
        pools = pools_for_slots(
            candidates, session_slots, split_role=role, experience_level=experience_level
        )
        if gear_on:
            for slot in session_slots:
                tiered, tier_meta = tier_slot_pool(
                    pools.get(slot.key) or [],
                    user_expanded=user_gear,
                    need=gear_need,
                    bw_key=lambda r, s=slot: slot_prefer_rank(s, r),
                )
                pools[slot.key] = tiered
                if out_gear_meta is not None:
                    out_gear_meta[slot.key] = tier_meta
        kept: list[dict] = []
        for spec in slots_to_prompt(session_slots, pools, mark_bw=gear_on):
            pool = spec.get("pool") or []
            if not pool:
                continue
            kept.append(spec)
            dest = str(spec.get("block_key") or "")
            if not dest:
                continue
            merged = list(shortlists.get(dest) or [])
            seen = {int(it.id) for it in merged}
            for row in pools.get(str(spec.get("key") or "")) or pool:
                item = _shortlist_item_from_pool_row(row)
                if item is None or item.id in seen:
                    continue
                merged.append(item)
                seen.add(item.id)
            shortlists[dest] = merged
        prompt_slots = kept

    if gear_on:
        # Leftover strength blocks (no slot): gear rows first so PROMPT_SHORTLIST_CAP keeps them.
        for key in _SLOT_COVERED_BLOCKS:
            if shortlists.get(key):
                shortlists[key] = sort_gear_first(list(shortlists[key]), user_gear)

    for block in recipe:
        if block.block_key in _SLOT_COVERED_BLOCKS:
            continue
        if block.block_key not in _GPT_BLOCK_KEYS or block.count_max <= 0:
            continue
        items = shortlists.get(block.block_key) or []
        if not items and block.is_optional:
            continue
        prompt_slots.append(
            {
                "key": block.block_key,
                "block_key": block.block_key,
                "label": block.label_vi or block.block_key,
                "pick": clamp_pick_count(int(block.count_max), max(1, len(items)))
                if items
                else int(block.count_max),
                "required": not block.is_optional,
                "pool": shortlist_to_prompt_dicts(items),
            }
        )

    if out_shortlists is not None:
        out_shortlists.clear()
        out_shortlists.update(shortlists)
    if out_slots is not None:
        out_slots.clear()
        out_slots.extend(prompt_slots)

    out = []
    for block in recipe:
        if block.count_max <= 0:
            out.append(
                {
                    "block_key": block.block_key,
                    "label_vi": block.label_vi,
                    "count_min": block.count_min,
                    "count_max": block.count_max,
                    "pick": False,
                    "shortlist": [],
                }
            )
            continue
        items = shortlists.get(block.block_key, [])
        count_max = int(block.count_max)
        count_min = int(block.count_min)
        if not items:
            if not block.is_optional:
                raise BadRequestError(
                    f"Kho bài không đủ cho block `{block.block_key}` (cần {count_max}, có 0)."
                )
            count_max = 0
            count_min = 0
        else:
            count_max = clamp_pick_count(count_max, len(items))
            count_min = min(count_min, count_max)
        out.append(
            {
                "block_key": block.block_key,
                "label_vi": block.label_vi,
                "count_min": count_min,
                "count_max": count_max,
                "is_optional": block.is_optional,
                "pick": True,
                "shortlist": shortlist_to_prompt_dicts(
                    items, mark_bw=gear_on and block.block_key in _SLOT_COVERED_BLOCKS
                ),
            }
        )
    return out
