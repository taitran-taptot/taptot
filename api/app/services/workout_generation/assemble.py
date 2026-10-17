"""Assemble PlanDayIn from frame days + picked exercise ids."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.schemas.plans import PlanDayIn, PlanExerciseIn, PlanSetPrescription
from app.services.exercise_prescription import get_prescription
from app.services.workout_generation.coach_notes import (
    COOLDOWN_NOTE_VI,
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
    clamp_challenge_rest_seconds,
    clamp_openai_dose,
    default_reps_label,
    dose_bounds_for_item,
    half_working_reps_label,
    primer_reps_from_baseline,
    coerce_working_reps_label,
    snap_rep_to_five_band,
)
from app.services.workout_generation.effort_mode import exercise_effort_mode
from app.services.workout_generation.openai_picker import DOSE_PICKS_KEY, OPENAI_PICK_FAIL_VI
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
from app.services.workout_rest import (
    REST_ISOLATION_FLOOR_SEC,
    default_rest_seconds,
    timed_block_prescription,
)

_STRENGTH_BLOCK_KEYS = frozenset({"compound", "accessory", "resistance", "conditioning"})


def cardio_plank_set_split(cardio_sets: int) -> tuple[int, int]:
    """Keep most interval cardio; convert the rest into plank holds (7 → 4 + 3)."""
    n = max(0, int(cardio_sets or 0))
    if n <= 0:
        return 0, 2
    plank = min(3, max(1, int(round(n * 3 / 7.0))))
    keep = n - plank
    if keep < 1:
        keep = n
        plank = 2
    elif keep < 2 and n >= 3:
        keep = 2
        plank = n - keep
    return keep, max(1, plank)


def plank_finisher_reps(fitness_baseline: dict[str, Any] | None) -> str:
    """80% of plank test, snapped to a 5-second band (40s test → 30-35 giây)."""
    raw = None
    if fitness_baseline:
        try:
            raw = int(fitness_baseline.get("plank_seconds"))
        except (TypeError, ValueError):
            raw = None
    if not raw or raw <= 0:
        return "20-30 giây"
    mid = int(round(0.8 * raw))
    lo = 5 * (mid // 5)
    if lo < 5:
        lo = 5
    return f"{lo}-{lo + 5} giây"


def _is_elbow_plank_item(item: Any) -> bool:
    blob = f"{getattr(item, 'name_en', None) or ''} {getattr(item, 'name_vi', None) or ''}".lower()
    if "side" in blob or "bên" in blob:
        return False
    needles = (
        "front plank on elbow",
        "plank on elbow",
        "chống khuỷu",
        "chong khuyu",
        "chống người chống khuỷu",
    )
    return "plank" in blob and any(n in blob for n in needles)


def _is_any_front_plank(item: Any) -> bool:
    blob = f"{getattr(item, 'name_en', None) or ''} {getattr(item, 'name_vi', None) or ''}".lower()
    if "side" in blob or "bên" in blob:
        return False
    return "plank" in blob


def _lookup_elbow_plank(
    *,
    shortlists: dict[str, list[ShortlistItem]] | None,
    used_ids: set[int],
    db: Session | None = None,
) -> ShortlistItem | None:
    pick: ShortlistItem | None = None
    fallback: ShortlistItem | None = None
    for items in (shortlists or {}).values():
        for item in items:
            if int(item.id) in used_ids and not _is_any_front_plank(item):
                continue
            if _is_elbow_plank_item(item):
                pick = item
                break
            if fallback is None and _is_any_front_plank(item):
                fallback = item
        if pick:
            break
    if pick or fallback:
        return pick or fallback
    if db is None:
        return None
    from app.models.entities import Exercise

    row = (
        db.query(Exercise)
        .filter(Exercise.name_en.ilike("%Front Plank on Elbows%"))
        .first()
    )
    if row is None:
        return None
    return ShortlistItem(
        id=int(row.id),
        name_vi=str(row.name_vi or "Plank chống khuỷu"),
        name_en=row.name_en,
        movement_role=row.movement_role or "isolation",
        movement_pattern=row.movement_pattern or "core",
        muscle_slug="core",
        difficulty=int(row.difficulty or 1),
    )


def ensure_cooldown_stretches(
    day: PlanDayIn,
    *,
    shortlists: dict[str, list[ShortlistItem]] | None,
    used_ids: set[int],
    meta_by_id: dict[int, ShortlistItem],
) -> None:
    if any((ex.section or "").strip().lower() == "cooldown" for ex in day.exercises):
        return
    picks: list[ShortlistItem] = []
    for item in (shortlists or {}).get("cooldown") or []:
        if int(item.id) in used_ids:
            continue
        picks.append(item)
        if len(picks) >= 2:
            break
    for item in picks:
        day.exercises.append(
            PlanExerciseIn(
                exercise_id=int(item.id),
                sets=2,
                reps="30 giây",
                rest_seconds=20,
                section="cooldown",
                notes_vi=COOLDOWN_NOTE_VI,
                sort_order=len(day.exercises) + 1,
            )
        )
        used_ids.add(int(item.id))
        meta_by_id[int(item.id)] = item


def inject_legs_plank_finisher(
    day: PlanDayIn,
    *,
    meta_by_id: dict[int, ShortlistItem],
    shortlists: dict[str, list[ShortlistItem]] | None,
    used_ids: set[int],
    fitness_baseline: dict[str, Any] | None,
    experience_level: int | None = None,
    db: Session | None = None,
) -> PlanDayIn:
    """Required elbow plank after the legs block; extra interval cardio sets become plank."""
    role = normalize_split_role(getattr(day, "split_role", None))
    if role not in {"legs", "lower"}:
        return day
    interval = [
        ex
        for ex in day.exercises
        if (ex.section or "").strip().lower() == "cardio"
        and "phút" not in str(ex.reps or "").lower()
        and "phut" not in str(ex.reps or "").lower()
    ]
    cardio_sets = sum(max(1, int(ex.sets or 1)) for ex in interval)
    keep, plank_sets = cardio_plank_set_split(cardio_sets)
    leftover = keep
    for ex in interval:
        cur = max(1, int(ex.sets or 1))
        if leftover <= 0:
            ex.sets = 0
            continue
        take = min(cur, leftover)
        ex.sets = take
        leftover -= take
    if interval:
        first_keep = next((ex for ex in interval if int(ex.sets or 0) > 0), interval[0])
        if int(first_keep.sets or 0) <= 0:
            first_keep.sets = max(1, keep)
        day.exercises = [
            ex
            for ex in day.exercises
            if ex not in interval or int(ex.sets or 0) > 0
        ]

    existing = None
    for ex in day.exercises:
        meta = meta_by_id.get(int(ex.exercise_id))
        if meta and _is_any_front_plank(meta) and (ex.section or "main") == "main":
            existing = ex
            break
    reps = plank_finisher_reps(fitness_baseline)
    if existing is not None:
        existing.sets = plank_sets
        existing.reps = reps
        if int(getattr(existing, "rest_seconds", 0) or 0) < REST_ISOLATION_FLOOR_SEC:
            existing.rest_seconds = REST_ISOLATION_FLOOR_SEC
        return day
    pick = _lookup_elbow_plank(shortlists=shortlists, used_ids=used_ids, db=db)
    if pick is None:
        return day
    insert_at = next(
        (
            i
            for i, ex in enumerate(day.exercises)
            if (ex.section or "").strip().lower() in {"cardio", "cooldown"}
        ),
        len(day.exercises),
    )
    row = PlanExerciseIn(
        exercise_id=int(pick.id),
        sets=plank_sets,
        reps=reps,
        rest_seconds=REST_ISOLATION_FLOOR_SEC,
        section="main",
        notes_vi=hold_note_vi(reps),
        sort_order=insert_at + 1,
    )
    day.exercises = [*day.exercises[:insert_at], row, *day.exercises[insert_at:]]
    used_ids.add(int(pick.id))
    meta_by_id[int(pick.id)] = pick
    return day


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
    if meta_by_id:
        from app.services.workout_generation.skill_gate import is_warmup_strength_leak

        warmup = [
            ex
            for ex in warmup
            if not is_warmup_strength_leak(meta_by_id.get(int(ex.exercise_id)) or {})
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
    challenge: bool = False,
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
            challenge=challenge,
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
    honor_openai_dose: bool = False,
) -> PlanDayIn:
    role = split_role or getattr(frame_day, "split_role", None)
    home_session = str(location or "").strip().lower() == "home"
    interval_cardio = home_session
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
        strength_block = block.block_key in {"compound", "accessory", "resistance"}
        chosen = repair_block_picks(
            block=block,
            picked_ids=raw,
            shortlist=shortlists.get(block.block_key, []),
            used_ids=used,
            fill_missing=(not strict_openai_picks),
            user_gear=user_gear if strength_block else None,
        )
        if not chosen and not block.is_optional and _target_count(block) > 0:
            if strict_openai_picks:
                raise BadRequestError(
                    OPENAI_PICK_FAIL_VI
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
                mobility_sets=None,
                name_vi=getattr(meta, "name_vi", None) if meta else None,
                name_en=getattr(meta, "name_en", None) if meta else None,
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
                    REST_ISOLATION_FLOOR_SEC,
                    hold_note_vi(f"{hold_default} giây"),
                )
                rpe = 0
                timed = (sets, reps, extra_rest, timed_notes)
            elif home_session:
                # Home main work: fitness / presets via dose_bounds — skip gym seed tables.
                sets, reps, rpe = 3, "12", 0
            elif rx and working:
                sets, reps, rpe = rx
            elif rx:
                sets, reps, rpe = rx.sets, rx.reps, 0
            else:
                sets, reps, rpe = 3, "12", 0

            proposal = (
                dose_by_exercise.get(str(eid))
                if (honor_openai_dose or not home_session)
                else None
            )
            apply_llm_dose = (not timed) or bool(
                honor_openai_dose and proposal and effort_mode == "hold"
            )
            if apply_llm_dose:
                bounds = dose_bounds_for_item(
                    meta or {
                        "movement_role": move_role,
                    },
                    experience_level=experience_level,
                    fitness_baseline=fitness_baseline,
                    plan_section=block.plan_section,
                    no_equipment=no_equipment,
                    home_session=home_session,
                    challenge=honor_openai_dose,
                )
                default_reps = (
                    default_reps_label(bounds)
                    if home_session and str(bounds.get("work_mode")) == "reps"
                    else str(reps)
                )
                from app.services.workout_generation.dose_bounds import is_hard_bw_skill_item

                sets, reps = clamp_openai_dose(
                    proposal,
                    bounds,
                    default_sets=int(sets),
                    default_reps=default_reps,
                    prefer_proposal_reps=bool(
                        honor_openai_dose
                        and proposal
                        and not is_hard_bw_skill_item(meta)
                    ),
                )
                from app.services.workout_generation.bar_rings_dose import is_bar_rings_item

                if str(bounds.get("work_mode") or "") == "reps":
                    hint_lo = bounds.get("hint_reps_min")
                    hint_hi = bounds.get("hint_reps_max")
                    if (
                        is_bar_rings_item(meta)
                        and not proposal
                        and hint_lo is not None
                        and hint_hi is not None
                    ):
                        reps = (
                            f"{int(hint_lo)}-{int(hint_hi)}"
                            if int(hint_lo) != int(hint_hi)
                            else str(int(hint_lo))
                        )
                    reps = coerce_working_reps_label(
                        reps, work_mode="reps", item=meta
                    )
                    reps = snap_rep_to_five_band(reps, item=meta)

            if effort_mode == "reps":
                reps = coerce_working_reps_label(reps, work_mode="reps", item=meta)
                reps = snap_rep_to_five_band(reps, item=meta)

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
                            honor_openai_dose
                            or (
                                block.block_key in {"compound", "resistance"}
                                and not ramp_applied
                            )
                        ),
                        rpe=rpe or 7,
                    )
                )
                if block.block_key in {"compound", "resistance"}:
                    ramp_applied = True

            rest_seconds = (
                extra_rest
                if extra_rest is not None
                else default_rest_seconds(move_role, experience_level=experience_level)
            )
            if honor_openai_dose and proposal and proposal.get("rest_seconds") is not None:
                rest_seconds = clamp_challenge_rest_seconds(
                    proposal.get("rest_seconds"),
                    rest_seconds,
                    movement_role=move_role,
                )

            set_rx = None
            if honor_openai_dose and proposal:
                from app.services.workout_generation.load_estimate import (
                    is_band_exercise,
                    is_dumbbell_exercise,
                    prescription_rpe,
                    suggest_load_note_vi,
                )

                band_move = is_band_exercise(meta)
                db_move = is_dumbbell_exercise(meta)
                load_kg = proposal.get("load_kg")
                load_note = str(proposal.get("load_note_vi") or "").strip()
                kgf = 0.0
                if load_kg is not None and not band_move:
                    try:
                        kgf = float(load_kg)
                    except (TypeError, ValueError):
                        kgf = 0.0
                rpe_out = prescription_rpe(rpe)
                if db_move or (kind == "loaded" and not band_move):
                    if kgf > 0:
                        notes_parts.append(f"Gợi ý tạ ~{kgf:g}kg")
                        label = suggest_load_note_vi(f"{kgf:g}kg") or load_note
                        if label:
                            set_rx = [
                                PlanSetPrescription(
                                    reps=reps if reps is not None else "12",
                                    rest_seconds=rest_seconds,
                                    rpe=rpe_out,
                                    load_note_vi=label,
                                )
                                for _ in range(max(1, int(sets) if isinstance(sets, int) else 1))
                            ]
                    elif load_note:
                        notes_parts.append(load_note.rstrip("."))
                elif band_move and load_note:
                    notes_parts.append(load_note.rstrip("."))
                    set_rx = [
                        PlanSetPrescription(
                            reps=reps if reps is not None else "12",
                            rest_seconds=rest_seconds,
                            rpe=rpe_out,
                            load_note_vi=load_note[:64],
                        )
                        for _ in range(max(1, int(sets) if isinstance(sets, int) else 1))
                    ]

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
                    rest_seconds=rest_seconds,
                    section=block.plan_section,  # type: ignore[arg-type]
                    notes_vi=notes,
                    sort_order=sort,
                    set_prescriptions=set_rx,
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
        session_minutes=session_minutes,
    )
    for i, ex in enumerate(day.exercises, start=1):
        ex.sort_order = i
    from app.services.workout_generation.load_estimate import (
        attach_band_set_prescriptions,
        attach_db_set_prescriptions,
    )

    attach_band_set_prescriptions(
        day, meta_by_id=meta_by_id, fitness_baseline=fitness_baseline
    )
    attach_db_set_prescriptions(
        day, meta_by_id=meta_by_id, fitness_baseline=fitness_baseline
    )
    inject_legs_plank_finisher(
        day,
        meta_by_id=meta_by_id,
        shortlists=shortlists,
        used_ids=used,
        fitness_baseline=fitness_baseline,
        experience_level=experience_level,
        db=db,
    )
    ensure_cooldown_stretches(
        day,
        shortlists=shortlists,
        used_ids=used,
        meta_by_id=meta_by_id,
    )
    day.exercises = reorder_main_section_exercises(
        role,
        day.exercises,
        meta_by_id,
        focus_slugs=focus_slugs,
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
    challenge: bool = False,
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
        challenge=challenge,
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
                challenge=challenge,
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
                challenge=challenge,
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
            location="home",
            focus_slugs=focus_slugs,
            day_index=int(getattr(frame_day, "day_index", 0) or 0),
            allow_bar_moves="pull-up-bar" in {
                str(s).strip().lower() for s in (equipment_slugs or [])
            },
            experience_level=experience_level,
            no_equipment=no_equipment,
        )
        pools = pools_for_slots(
            candidates, session_slots, split_role=role, experience_level=experience_level
        )
        from app.services.workout_generation.weekly_volume import (
            drop_pushups_keep_fallback,
            exclude_pushups_for_loaded_home,
        )

        drop_pu = exclude_pushups_for_loaded_home(
            location=location,
            no_equipment=no_equipment,
            equipment_slugs=list(equipment_slugs or []),
            fitness_baseline=fitness_baseline,
        )
        if drop_pu:
            for slot in session_slots:
                pools[slot.key] = drop_pushups_keep_fallback(list(pools.get(slot.key) or []))
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
