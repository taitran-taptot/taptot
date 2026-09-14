"""Estimate and fill workout session duration (work + rest + station changes)."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.plans import PlanDayIn, PlanExerciseIn
from app.services.workout_generation.coach_notes import (
    hold_note_vi,
    load_kind_for_item,
    working_note_vi,
)
from app.services.exercise_prescription import get_prescription
from app.services.workout_generation.dose_bounds import (
    clamp_openai_dose,
    default_reps_label,
    dose_bounds_for_item,
)
from app.services.workout_generation.effort_mode import exercise_effort_mode
from app.services.workout_rest import (
    INTERVAL_CARDIO_MAX_BOUTS,
    INTERVAL_CARDIO_MIN_BOUTS,
    INTERVAL_CARDIO_REST_MAX,
    INTERVAL_CARDIO_REST_MIN,
    INTERVAL_CARDIO_WORK_MAX,
    INTERVAL_CARDIO_WORK_MIN,
    default_rest_seconds,
    interval_cardio_piece_count,
    interval_cardio_prescription,
    snap_rest_seconds,
    timed_block_prescription,
)
from app.services.session_blocks import BlockSpec
from app.services.workout_generation.muscle_quotas import CORE_SLUGS, quota_would_exceed_max
from app.services.workout_generation.repair import repair_block_picks
from app.services.workout_generation.shortlist import ShortlistItem
from app.services.workout_generation.split_map import normalize_split_role
from app.services.workout_generation.weekly_volume import (
    is_pushup_name,
    l1_session_set_cap,
    main_exercise_count,
    main_lift_floor,
    pushup_cap_for_minutes,
)

FILL_MIN_RATIO = 0.90
FILL_MAX_RATIO = 1.00
GAP_OK_MINUTES = 2
# Walk / set up the next machine. Skip when the next row is the same exercise_id
# (warmup primer → working sets at the same station).
TRANSITION_MINUTES = 1.0
_SECTION_ORDER = ("warmup", "main", "cardio", "cooldown")
MAX_FILL_ROUNDS = 24
MAX_COMPOUND_SETS = 5
MAX_ISOLATION_SETS = 4
MAX_CONDITIONING_SETS = 4
MAX_RESISTANCE_FILL_SETS = 3
MAX_CARDIO_MINUTES = 25
MAX_SINGLE_CARDIO_MINUTES = 30
# Home lift days: prefer adding main sets until leftover cardio ≤ this many minutes.
HOME_CARDIO_SURPLUS_CAP_MINUTES = 15
_CARDIO_BLOCK_KEYS = frozenset({"cardio", "conditioning"})

_FILL_BLOCK_ORDER = ("accessory", "core", "resistance", "compound", "conditioning")


def parse_reps_minutes(reps: str | int | None) -> int | None:
    if reps is None or isinstance(reps, int):
        return None
    s = str(reps).strip().lower()
    m = re.search(r"(\d+)\s*(?:phút|phut|min)", s)
    if m:
        return max(1, int(m.group(1)))
    return None


def parse_reps_seconds(reps: str | int | None) -> int | None:
    if reps is None or isinstance(reps, int):
        return None
    match = re.search(r"(\d+)\s*(?:giây|giay|sec|secs|s)\b", str(reps).strip().lower())
    return max(1, int(match.group(1))) if match else None


def _is_cardio_row(
    ex: PlanExerciseIn,
    meta_by_id: dict[int, ShortlistItem] | None = None,
) -> bool:
    section = (ex.section or "").strip().lower()
    if section == "cardio":
        return True
    if not meta_by_id:
        return False
    meta = meta_by_id.get(int(ex.exercise_id))
    role = ((meta.movement_role if meta else None) or "").strip().lower()
    return role in {"cardio", "conditioning"}


def interval_cardio_wall_minutes(ex: PlanExerciseIn) -> float | None:
    """Wall-clock minutes for 30–45s interval cardio; None if continuous minutes."""
    if parse_reps_minutes(ex.reps) is not None:
        return None
    work = parse_reps_seconds(ex.reps)
    if work is None:
        return None
    sets = max(1, int(getattr(ex, "sets", 1) or 1))
    rest = max(0, int(getattr(ex, "rest_seconds", 0) or 0))
    return float((sets * work + max(0, sets - 1) * rest) / 60.0)


def _round_half_up(n: float) -> int:
    """Match JavaScript Math.round (half away from zero for positives)."""
    if n < 0:
        return -int(-n + 0.5)
    return int(n + 0.5)


def estimate_exercise_minutes_raw(ex: PlanExerciseIn) -> float:
    """Unrounded work + between-set rest. Day totals round once after transitions."""
    rest_sec = int(getattr(ex, "rest_seconds", 0) or 0)
    sets = int(getattr(ex, "sets", 1) or 1)
    reps = getattr(ex, "reps", None)
    rep_min = parse_reps_minutes(reps)
    if rep_min is not None:
        rest_min = max(0.0, rest_sec / 60.0)
        return float(sets * rep_min + max(0, sets - 1) * rest_min)
    rep_sec = parse_reps_seconds(reps)
    if rep_sec is not None:
        return float((sets * rep_sec + max(0, sets - 1) * rest_sec) / 60.0)
    if rest_sec > 0:
        rest_min = rest_sec / 60.0
    else:
        rest_min = 2.0
    return float(sets * 1.0 + max(0, sets - 1) * rest_min)


def estimate_exercise_minutes(ex: PlanExerciseIn) -> float:
    """Mirror frontend estimatePlanExerciseMinutes (round each exercise)."""
    return float(max(1, _round_half_up(estimate_exercise_minutes_raw(ex))))


def _section_of(ex: PlanExerciseIn) -> str:
    return (getattr(ex, "section", None) or "main") or "main"


def ordered_plan_exercises(exercises: list[PlanExerciseIn]) -> list[PlanExerciseIn]:
    buckets: dict[str, list[PlanExerciseIn]] = {s: [] for s in _SECTION_ORDER}
    other: list[PlanExerciseIn] = []
    for ex in exercises:
        sec = _section_of(ex)
        if sec in buckets:
            buckets[sec].append(ex)
        else:
            other.append(ex)
    out: list[PlanExerciseIn] = []
    for sec in _SECTION_ORDER:
        out.extend(buckets[sec])
    out.extend(other)
    return out


def estimate_transition_minutes(exercises: list[PlanExerciseIn]) -> float:
    ordered = ordered_plan_exercises(exercises)
    extra = 0.0
    for i in range(len(ordered) - 1):
        a = ordered[i]
        b = ordered[i + 1]
        aid = int(getattr(a, "exercise_id", 0) or 0)
        bid = int(getattr(b, "exercise_id", 0) or 0)
        if aid and bid and aid == bid:
            continue
        sa = _section_of(a)
        sb = _section_of(b)
        # Stretch in place — do not add a station-change minute onto/off cooldown.
        if sa == "cooldown" or sb == "cooldown":
            continue
        extra += TRANSITION_MINUTES
    return extra


def estimate_day_minutes(day: PlanDayIn) -> float:
    return estimate_exercises_minutes(day.exercises)


def estimate_exercises_minutes(exercises: list[PlanExerciseIn]) -> float:
    ordered = ordered_plan_exercises(exercises)
    work = float(sum(estimate_exercise_minutes_raw(ex) for ex in ordered))
    return float(_round_half_up(work + estimate_transition_minutes(ordered)))


def _block_counts(
    day: PlanDayIn,
    meta_by_id: dict[int, ShortlistItem],
    recipe: list[BlockSpec] | None = None,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    warmup_exs: list[PlanExerciseIn] = []
    for ex in day.exercises:
        meta = meta_by_id.get(int(ex.exercise_id))
        role = (meta.movement_role if meta else None) or ""
        section = ex.section or "main"
        slug = (meta.muscle_slug if meta else "") or ""
        pattern = (meta.movement_pattern if meta else "") or ""
        if section == "warmup":
            warmup_exs.append(ex)
        elif section == "cardio" or role in {"cardio", "conditioning"}:
            if role == "conditioning":
                counts["conditioning"] = counts.get("conditioning", 0) + 1
            else:
                counts["cardio"] = counts.get("cardio", 0) + 1
        elif role == "compound":
            counts["compound"] = counts.get("compound", 0) + 1
        elif role == "isolation" and section == "main":
            if slug in CORE_SLUGS or pattern == "core":
                counts["core"] = counts.get("core", 0) + 1
            else:
                counts["accessory"] = counts.get("accessory", 0) + 1
        elif role == "resistance":
            counts["resistance"] = counts.get("resistance", 0) + 1
    gen_max = 0
    if recipe:
        for b in recipe:
            if b.block_key == "general_warmup":
                gen_max = int(b.count_max or 0)
                break
    for i, _ex in enumerate(warmup_exs):
        key = "general_warmup" if (not recipe or i < gen_max) else "dynamic_mobility"
        counts[key] = counts.get(key, 0) + 1
    return counts


def _append_picked_exercise(
    *,
    exercises: list[PlanExerciseIn],
    eid: int,
    block: BlockSpec,
    meta: ShortlistItem | None,
    db: Session,
    experience_level: int,
    goal: str | None,
    extra_goals: list[str] | None,
    sort_order: int,
    fitness_baseline: dict[str, Any] | None = None,
    no_equipment: bool = False,
    home_session: bool = False,
) -> PlanExerciseIn:
    move_role = meta.movement_role if meta else block.movement_role
    working = (block.plan_section or "") == "main" and (move_role or "") in {
        "compound",
        "isolation",
        "resistance",
    }
    rx = get_prescription(db, experience_level, move_role, goal=goal, extra_goals=extra_goals)
    timed = timed_block_prescription(
        block_key=block.block_key,
        plan_section=block.plan_section,
        movement_role=move_role,
        duration_min=block.duration_min_minutes,
        duration_max=block.duration_max_minutes,
        interval_cardio=home_session,
        experience_level=experience_level,
    )
    extra_rest: int | None = None
    notes = None
    effort_mode = exercise_effort_mode(
        meta,
        movement_role=move_role,
        plan_section=block.plan_section,
    )
    if timed:
        sets, reps, extra_rest, notes = timed
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
        sets, reps, extra_rest, notes, rpe = (
            3,
            f"{hold_default} giây",
            45 if experience_level <= 1 else 60,
            hold_note_vi(f"{hold_default} giây"),
            0,
        )
    elif home_session:
        sets, reps, rpe = (3, "12", 0)
    elif rx and working:
        sets, reps, rpe = rx
    elif rx:
        sets, reps, rpe = rx.sets, rx.reps, 0
    else:
        sets, reps, rpe = (3, "12", 0)

    if not timed and effort_mode != "hold":
        bounds = dose_bounds_for_item(
            meta or {"movement_role": move_role},
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
        sets, reps = clamp_openai_dose(
            None,
            bounds,
            default_sets=int(sets) if isinstance(sets, int) else 3,
            default_reps=default_reps,
        )

    if not notes and working:
        kind = load_kind_for_item(meta, no_equipment=no_equipment)
        notes = working_note_vi(
            reps,
            kind=kind,
            include_progress=False,
            rpe=rpe or 7,
        )

    ex = PlanExerciseIn(
        exercise_id=eid,
        sets=sets if isinstance(sets, int) else 3,
        reps=reps,
        rest_seconds=(
            extra_rest
            if extra_rest is not None
            else default_rest_seconds(move_role, experience_level=experience_level)
        ),
        section=block.plan_section,  # type: ignore[arg-type]
        notes_vi=notes,
        sort_order=sort_order,
    )
    dest = str(block.plan_section or "") or "main"
    if dest == "main":
        insert_at = next(
            (
                i
                for i, existing in enumerate(exercises)
                if str(existing.section or "") in {"cardio", "cooldown"}
            ),
            len(exercises),
        )
        exercises.insert(insert_at, ex)
    else:
        exercises.append(ex)
    return ex


def _cardio_piece_count(exercises: list[PlanExerciseIn]) -> int:
    return sum(1 for ex in exercises if (ex.section or "") == "cardio")


def _extend_cardio(
    exercises: list[PlanExerciseIn],
    add_min: int,
    meta_by_id: dict[int, ShortlistItem] | None = None,
    *,
    cap_minutes: int | None = None,
) -> bool:
    cap = (
        max(1, int(cap_minutes))
        if cap_minutes is not None
        else (
            MAX_SINGLE_CARDIO_MINUTES
            if _cardio_piece_count(exercises) <= 1
            else MAX_CARDIO_MINUTES
        )
    )
    add = max(1, int(add_min or 1))
    for ex in reversed(exercises):
        section = ex.section or ""
        if section in {"warmup", "cooldown"}:
            continue
        if not _is_cardio_row(ex, meta_by_id):
            continue
        wall = interval_cardio_wall_minutes(ex)
        if wall is not None:
            # Prefer longer rest, then work, then +1 set — never explode bout count.
            work = parse_reps_seconds(ex.reps) or 30
            rest = max(0, int(getattr(ex, "rest_seconds", 0) or 0))
            if rest < INTERVAL_CARDIO_REST_MAX:
                new_rest = min(
                    INTERVAL_CARDIO_REST_MAX,
                    rest + max(15, add * 15),
                )
                snapped = snap_rest_seconds(new_rest)
                if snapped > rest:
                    preview = PlanExerciseIn(
                        exercise_id=ex.exercise_id,
                        sets=ex.sets,
                        reps=ex.reps,
                        rest_seconds=snapped,
                        section=ex.section,
                    )
                    if (interval_cardio_wall_minutes(preview) or 0) <= cap + 0.25:
                        ex.rest_seconds = snapped
                        return True
            # Do not lengthen 30s beginner bouts to 60s — add sets instead.
            if INTERVAL_CARDIO_WORK_MIN < work < INTERVAL_CARDIO_WORK_MAX:
                preview = PlanExerciseIn(
                    exercise_id=ex.exercise_id,
                    sets=ex.sets,
                    reps=f"{INTERVAL_CARDIO_WORK_MAX} giây",
                    rest_seconds=ex.rest_seconds,
                    section=ex.section,
                )
                if (interval_cardio_wall_minutes(preview) or 0) <= cap + 0.25:
                    ex.reps = f"{INTERVAL_CARDIO_WORK_MAX} giây"
                    return True
            if int(ex.sets or 1) < INTERVAL_CARDIO_MAX_BOUTS:
                new_sets = int(ex.sets or 1) + 1
                preview = PlanExerciseIn(
                    exercise_id=ex.exercise_id,
                    sets=new_sets,
                    reps=ex.reps,
                    rest_seconds=ex.rest_seconds,
                    section=ex.section,
                )
                if (interval_cardio_wall_minutes(preview) or 0) <= cap + 0.25:
                    ex.sets = new_sets
                    return True
            continue
        if parse_reps_minutes(ex.reps) is None:
            continue
        cur = parse_reps_minutes(ex.reps) or 10
        new_val = min(cap, cur + add)
        if new_val <= cur:
            continue
        ex.reps = f"{new_val} phút"
        return True
    return False


def _bump_sets(ex: PlanExerciseIn, *, max_sets: int) -> bool:
    if parse_reps_minutes(ex.reps) is not None:
        return False
    if ex.sets >= max_sets:
        return False
    ex.sets += 1
    return True


def _main_hard_sets(exercises: list[PlanExerciseIn]) -> int:
    total = 0
    for ex in exercises:
        if (ex.section or "main") != "main":
            continue
        if parse_reps_minutes(ex.reps) is not None:
            continue
        total += int(ex.sets or 0)
    return total


def _pick_fill_action(
    exercises: list[PlanExerciseIn],
    meta_by_id: dict[int, ShortlistItem],
    gap: float,
    *,
    hard_set_cap: int | None = None,
    max_minutes: float | None = None,
) -> bool:
    """Add time via isolation sets first, then cardio. Does not bump compound Rx."""
    if gap <= GAP_OK_MINUTES:
        return False

    def _fits() -> bool:
        if max_minutes is None:
            return True
        return estimate_exercises_minutes(exercises) <= max_minutes

    under_set_cap = hard_set_cap is None or _main_hard_sets(exercises) < hard_set_cap
    if under_set_cap:
        for ex in reversed(exercises):
            meta = meta_by_id.get(int(ex.exercise_id))
            role = (meta.movement_role if meta else None) or ""
            section = ex.section or "main"
            if section != "main":
                continue
            if role != "isolation":
                continue
            if not _bump_sets(ex, max_sets=MAX_ISOLATION_SETS):
                continue
            if _fits():
                return True
            ex.sets -= 1
        for ex in reversed(exercises):
            meta = meta_by_id.get(int(ex.exercise_id))
            role = (meta.movement_role if meta else None) or ""
            section = ex.section or "main"
            if section != "main":
                continue
            if role != "resistance":
                continue
            if parse_reps_seconds(ex.reps) is not None:
                continue
            if not _bump_sets(ex, max_sets=MAX_RESISTANCE_FILL_SETS):
                continue
            if _fits():
                return True
            ex.sets -= 1

    def _restore(snapshot: list[tuple[str, int]]) -> None:
        for ex, (prev_reps, prev_sets) in zip(exercises, snapshot):
            ex.reps = prev_reps
            ex.sets = prev_sets

    if gap >= 4:
        snapshot = [(str(ex.reps), int(ex.sets or 1)) for ex in exercises]
        if _extend_cardio(exercises, min(5, int(round(gap))), meta_by_id) and _fits():
            return True
        _restore(snapshot)
    if gap >= 3:
        snapshot = [(str(ex.reps), int(ex.sets or 1)) for ex in exercises]
        if _extend_cardio(exercises, 2, meta_by_id) and _fits():
            return True
        _restore(snapshot)
    return False


def _pick_core_fill_action(
    exercises: list[PlanExerciseIn],
    meta_by_id: dict[int, ShortlistItem],
    *,
    target: int,
) -> bool:
    """Fill Cardio-Core with timed cardio only; never add abdominal hard sets."""
    if estimate_exercises_minutes(exercises) >= target:
        return False
    snapshot = [(str(ex.reps), int(ex.sets or 1)) for ex in exercises]
    if not _extend_cardio(
        exercises,
        1,
        meta_by_id,
        cap_minutes=target,
    ):
        return False
    if estimate_exercises_minutes(exercises) <= target:
        return True
    for ex, (prev_reps, prev_sets) in zip(exercises, snapshot):
        ex.reps = prev_reps
        ex.sets = prev_sets
    return False


def _add_exercises_from_blocks(
    day: PlanDayIn,
    *,
    recipe: list[BlockSpec],
    shortlists: dict[str, list[ShortlistItem]],
    meta_by_id: dict[int, ShortlistItem],
    used_ids: set[int],
    db: Session,
    experience_level: int,
    goal: str | None,
    extra_goals: list[str] | None,
    session_minutes: int | None = None,
    allow_extra_core: bool = False,
    skip_cardio: bool = False,
    fitness_baseline: dict[str, Any] | None = None,
    no_equipment: bool = False,
    home_session: bool = False,
) -> bool:
    block_by_key = {b.block_key: b for b in recipe}
    counts = _block_counts(day, meta_by_id, recipe)
    changed = False
    sort = max((ex.sort_order or 0 for ex in day.exercises), default=0)

    cardio_slots = sum(
        int(b.count_max or 0)
        for b in recipe
        if b.block_key in _CARDIO_BLOCK_KEYS
    )
    cardio_cap = max(1, cardio_slots) if cardio_slots else 0
    home_bw_lift = (
        bool(home_session)
        and bool(no_equipment)
        and normalize_split_role(getattr(day, "split_role", None)) != "core"
    )
    if (
        not home_bw_lift
        and normalize_split_role(getattr(day, "split_role", None)) != "core"
        and cardio_cap > 1
    ):
        cardio_cap = 1
    pu_cap = pushup_cap_for_minutes(session_minutes)

    def _main_pushups() -> int:
        n = 0
        for ex in day.exercises:
            if (ex.section or "main") != "main":
                continue
            item = meta_by_id.get(int(ex.exercise_id))
            name = item.name_vi if item else ""
            if is_pushup_name(name):
                n += 1
        return n

    for key in _FILL_BLOCK_ORDER:
        block = block_by_key.get(key)
        if not block or block.count_max <= 0:
            continue
        if key in _CARDIO_BLOCK_KEYS:
            if skip_cardio:
                continue
            if cardio_cap <= 0 or _cardio_piece_count(day.exercises) >= cardio_cap:
                continue
        have = counts.get(key, 0)
        max_n = int(block.count_max or 0)
        if allow_extra_core and key == "core":
            max_n = max_n + 1
        if have >= max_n:
            continue
        shortlist = shortlists.get(key, [])
        if not shortlist:
            continue
        picked = repair_block_picks(
            block=block,
            picked_ids=[],
            shortlist=shortlist,
            used_ids=used_ids,
        )
        if not picked:
            continue
        picked_meta = []
        for ex in day.exercises:
            if (ex.section or "main") != "main":
                continue
            existing = meta_by_id.get(int(ex.exercise_id))
            if existing is not None:
                picked_meta.append(existing)
        for eid in picked:
            if counts.get(key, 0) >= max_n:
                break
            meta = next((i for i in shortlist if i.id == eid), None)
            if meta and is_pushup_name(meta.name_vi) and _main_pushups() >= pu_cap:
                used_ids.add(eid)
                continue
            if meta and quota_would_exceed_max(
                getattr(day, "split_role", None), picked_meta, meta
            ):
                used_ids.add(eid)
                continue
            if meta:
                meta_by_id[eid] = meta
                picked_meta.append(meta)
            sort += 1
            _append_picked_exercise(
                exercises=day.exercises,
                eid=eid,
                block=block,
                meta=meta,
                db=db,
                experience_level=experience_level,
                goal=goal,
                extra_goals=extra_goals,
                sort_order=sort,
                fitness_baseline=fitness_baseline,
                no_equipment=no_equipment,
                home_session=home_session,
            )
            used_ids.add(eid)
            counts[key] = counts.get(key, 0) + 1
            changed = True
    return changed


def _non_cardio_exercises(day: PlanDayIn) -> list[PlanExerciseIn]:
    return [ex for ex in day.exercises if (ex.section or "") != "cardio"]


def _cardio_exercises(day: PlanDayIn) -> list[PlanExerciseIn]:
    return [ex for ex in day.exercises if (ex.section or "") == "cardio"]


def _home_cardio_budget_minutes(day: PlanDayIn, session_minutes: int) -> float:
    target = max(30, int(session_minutes or 45))
    non_cardio = _non_cardio_exercises(day)
    return max(0.0, float(target) - float(estimate_exercises_minutes(non_cardio)))


def _max_sets_for_home_main_role(role: str) -> int:
    r = (role or "").strip().lower()
    if r == "isolation":
        return MAX_ISOLATION_SETS
    if r == "resistance":
        # Absorb surplus needs more headroom than the light fill path (cap 3).
        return MAX_COMPOUND_SETS
    if r in {"compound", "accessory"}:
        return MAX_COMPOUND_SETS
    return MAX_ISOLATION_SETS


def absorb_home_cardio_surplus_into_main_sets(
    day: PlanDayIn,
    *,
    session_minutes: int,
    meta_by_id: dict[int, ShortlistItem] | dict[int, dict[str, Any]],
) -> bool:
    """While leftover >15 min on home lift days, +1 main set (isolation → resistance → compound)."""
    if normalize_split_role(getattr(day, "split_role", None)) == "core":
        return False
    slim = _slim_meta_by_id(meta_by_id)
    changed = False
    role_order = ("isolation", "resistance", "compound", "accessory")

    for _ in range(24):
        budget = _home_cardio_budget_minutes(day, session_minutes)
        if budget <= float(HOME_CARDIO_SURPLUS_CAP_MINUTES) + 0.05:
            break
        bumped = False
        for want_role in role_order:
            for ex in reversed(day.exercises):
                if (ex.section or "main") != "main":
                    continue
                if parse_reps_minutes(ex.reps) is not None:
                    continue
                meta = slim.get(int(ex.exercise_id))
                role = ((meta.movement_role if meta else None) or "").strip().lower()
                effective = role or ("resistance" if want_role == "resistance" else "")
                if effective != want_role:
                    continue
                cap = _max_sets_for_home_main_role(effective)
                if not _bump_sets(ex, max_sets=cap):
                    continue
                if estimate_day_minutes(day) > max(30, int(session_minutes or 45)) + 0.5:
                    ex.sets -= 1
                    continue
                bumped = True
                changed = True
                break
            if bumped:
                break
        if not bumped:
            break
    return changed


def rebalance_home_bw_interval_cardio(
    day: PlanDayIn,
    *,
    session_minutes: int,
    recipe: list[BlockSpec],
    shortlists: dict[str, list[ShortlistItem]],
    meta_by_id: dict[int, ShortlistItem],
    used_ids: set[int],
    db: Session,
    experience_level: int,
    goal: str | None = None,
    extra_goals: list[str] | None = None,
    fitness_baseline: dict[str, Any] | None = None,
) -> None:
    """Home BW lift days: 1 interval if surplus ≤10p, else 2 sharing budget (~5 sets each)."""
    if normalize_split_role(getattr(day, "split_role", None)) == "core":
        return

    target = max(30, int(session_minutes or 45))
    non_cardio = _non_cardio_exercises(day)
    non_cardio_min = estimate_exercises_minutes(non_cardio)
    budget = max(0.0, float(target) - float(non_cardio_min))
    want = interval_cardio_piece_count(budget)
    if want <= 0:
        day.exercises = list(non_cardio)
        return

    cardios = list(_cardio_exercises(day))
    # Grow to `want` pieces from conditioning/cardio shortlists.
    while len(cardios) < want:
        pool: list[ShortlistItem] = []
        for key in ("conditioning", "cardio"):
            pool.extend(shortlists.get(key) or [])
        block = next(
            (b for b in recipe if b.block_key in _CARDIO_BLOCK_KEYS),
            None,
        )
        if block is None:
            from app.services.session_blocks import _spec_block

            block = _spec_block(
                sort_order=30,
                block_key="conditioning",
                label_vi="Cardio nhẹ cuối buổi",
                plan_section="cardio",
                movement_role="conditioning",
                count=want,
            )
        picked = repair_block_picks(
            block=block,
            picked_ids=[],
            shortlist=pool,
            used_ids=used_ids,
            fill_missing=True,
        )
        if not picked:
            break
        eid = int(picked[0])
        meta = next((i for i in pool if int(i.id) == eid), None)
        if meta:
            meta_by_id[eid] = meta
        sort = max((ex.sort_order or 0 for ex in day.exercises), default=0) + 1
        ex = _append_picked_exercise(
            exercises=day.exercises,
            eid=eid,
            block=block,
            meta=meta,
            db=db,
            experience_level=experience_level,
            goal=goal,
            extra_goals=extra_goals,
            sort_order=sort,
            fitness_baseline=fitness_baseline,
            no_equipment=True,
            home_session=True,
        )
        used_ids.add(eid)
        cardios.append(ex)

    cardios = [ex for ex in day.exercises if (ex.section or "") == "cardio"]
    if not cardios:
        return

    # Drop extras when budget only warrants one piece.
    if len(cardios) > want:
        keep_ids = {id(ex) for ex in cardios[:want]}
        day.exercises = [
            ex
            for ex in day.exercises
            if (ex.section or "") != "cardio" or id(ex) in keep_ids
        ]
        cardios = [ex for ex in day.exercises if (ex.section or "") == "cardio"]

    per = budget / max(1, len(cardios))
    for ex in cardios:
        sets, reps, rest, notes = interval_cardio_prescription(
            per, experience_level=experience_level
        )
        ex.sets = sets
        ex.reps = reps
        ex.rest_seconds = rest
        if not (ex.notes_vi or "").strip():
            ex.notes_vi = notes
        elif "phút" in (ex.notes_vi or "") and "giây" not in (ex.notes_vi or ""):
            ex.notes_vi = notes


def fill_session_to_target(
    day: PlanDayIn,
    *,
    session_minutes: int,
    recipe: list[BlockSpec],
    shortlists: dict[str, list[ShortlistItem]],
    meta_by_id: dict[int, ShortlistItem],
    used_ids: set[int],
    db: Session,
    experience_level: int,
    goal: str | None = None,
    extra_goals: list[str] | None = None,
    fitness_baseline: dict[str, Any] | None = None,
    no_equipment: bool = False,
    home_session: bool = False,
) -> PlanDayIn:
    """Extend exercises/rest/cardio until the day reaches ~90–100% of session_minutes."""
    target = max(30, int(session_minutes or 45))
    min_target = target * FILL_MIN_RATIO
    hard_cap = l1_session_set_cap(target) if int(experience_level or 2) <= 1 else None

    add_kw = dict(
        recipe=recipe,
        shortlists=shortlists,
        meta_by_id=meta_by_id,
        used_ids=used_ids,
        db=db,
        experience_level=experience_level,
        goal=goal,
        extra_goals=extra_goals,
        session_minutes=session_minutes,
        fitness_baseline=fitness_baseline,
        no_equipment=no_equipment,
        home_session=home_session,
    )

    _add_exercises_from_blocks(day, **add_kw)
    if estimate_day_minutes(day) > target:
        _trim_day_over_target(day, target, meta_by_id=meta_by_id)

    core_day = normalize_split_role(getattr(day, "split_role", None)) == "core"
    for _ in range(MAX_FILL_ROUNDS):
        used = estimate_day_minutes(day)
        if used >= min_target:
            break
        if core_day:
            if not _pick_core_fill_action(
                day.exercises,
                meta_by_id,
                target=target,
            ):
                break
            continue
        gap = target - used
        if not _pick_fill_action(
            day.exercises,
            meta_by_id,
            gap,
            hard_set_cap=hard_cap,
            max_minutes=float(target),
        ):
            before_n = len(day.exercises)
            added = _add_exercises_from_blocks(day, skip_cardio=True, **add_kw)
            if added and estimate_day_minutes(day) > target:
                day.exercises = day.exercises[:before_n]
                added = False
            if not added:
                break

    _trim_day_over_target(day, target, meta_by_id=meta_by_id)

    if home_session and not core_day:
        absorb_home_cardio_surplus_into_main_sets(
            day,
            session_minutes=session_minutes,
            meta_by_id=meta_by_id,
        )
        rebalance_home_bw_interval_cardio(
            day,
            session_minutes=session_minutes,
            recipe=recipe,
            shortlists=shortlists,
            meta_by_id=meta_by_id,
            used_ids=used_ids,
            db=db,
            experience_level=experience_level,
            goal=goal,
            extra_goals=extra_goals,
            fitness_baseline=fitness_baseline,
        )
        if estimate_day_minutes(day) > target:
            _trim_day_over_target(day, target, meta_by_id=meta_by_id)

    for i, ex in enumerate(day.exercises, start=1):
        ex.sort_order = i
    return day


def _cap_continuous_home_cardio_to_budget(day: PlanDayIn, session_minutes: int) -> None:
    """Shrink continuous phút cardio so leftover matches post-absorb budget."""
    budget = _home_cardio_budget_minutes(day, session_minutes)
    cardios = [
        ex
        for ex in day.exercises
        if (ex.section or "") == "cardio" and parse_reps_minutes(ex.reps) is not None
    ]
    if not cardios:
        return
    if budget < 1:
        day.exercises = [ex for ex in day.exercises if (ex.section or "") != "cardio"]
        return
    per = max(5, int(round(budget / len(cardios))))
    for ex in cardios:
        ex.reps = f"{per} phút"
        ex.sets = 1
        ex.rest_seconds = 0


def _slim_meta_by_id(
    meta_by_id: dict[int, dict[str, Any]] | dict[int, ShortlistItem],
) -> dict[int, ShortlistItem]:
    slim: dict[int, ShortlistItem] = {}
    for eid, raw in meta_by_id.items():
        if isinstance(raw, ShortlistItem):
            slim[int(eid)] = raw
        elif isinstance(raw, dict):
            slim[int(eid)] = ShortlistItem(
                id=int(eid),
                name_vi=str(raw.get("name_vi") or ""),
                movement_role=raw.get("movement_role"),
                movement_pattern=raw.get("movement_pattern"),
                muscle_slug=str(raw.get("muscle_slug") or ""),
                difficulty=int(raw.get("difficulty") or 2),
            )
    return slim


def _cardio_minute_floor(split_role: str | None, target_minutes: int | None = None) -> int:
    if normalize_split_role(split_role) == "core":
        return 12
    m = int(target_minutes or 45)
    if m <= 30:
        return 5
    if m <= 45:
        return 8
    if m <= 60:
        return 10
    return 12


def _ex_move_role(
    ex: PlanExerciseIn, meta_by_id: dict[int, ShortlistItem] | None
) -> str:
    if not meta_by_id:
        return ""
    meta = meta_by_id.get(int(ex.exercise_id))
    return ((meta.movement_role if meta else None) or "").strip().lower()


def _trim_day_over_target(
    day: PlanDayIn,
    target: int,
    *,
    meta_by_id: dict[int, ShortlistItem] | None = None,
    location: str | None = "gym",
    drop_exercises: bool = False,
) -> None:
    """Cut cardio → rest/sets on main lifts. Never trims warmup (primer)."""
    cap = int(target)
    cardio_floor = _cardio_minute_floor(getattr(day, "split_role", None), cap)
    recipe_floor = main_lift_floor(
        cap, location, getattr(day, "split_role", None)
    )
    first_main = next(
        (ex for ex in day.exercises if (ex.section or "main") == "main"),
        None,
    )

    def over() -> bool:
        return estimate_day_minutes(day) > cap

    while over():
        trimmed = False
        for ex in reversed(day.exercises):
            if (ex.section or "") in {"warmup", "cooldown"}:
                continue
            if not _is_cardio_row(ex, meta_by_id):
                continue
            wall = interval_cardio_wall_minutes(ex)
            if wall is not None:
                if wall <= float(cardio_floor):
                    continue
                cur_rest = max(0, int(getattr(ex, "rest_seconds", 0) or 0))
                if cur_rest > INTERVAL_CARDIO_REST_MIN:
                    new_rest = max(INTERVAL_CARDIO_REST_MIN, cur_rest - 15)
                    snapped = snap_rest_seconds(new_rest)
                    if snapped >= INTERVAL_CARDIO_REST_MIN and snapped < cur_rest:
                        new_rest = snapped
                    if new_rest < cur_rest:
                        ex.rest_seconds = new_rest
                        trimmed = True
                        break
                if int(ex.sets or 1) > INTERVAL_CARDIO_MIN_BOUTS:
                    ex.sets = int(ex.sets or 1) - 1
                    trimmed = True
                    break
                continue
            cur = parse_reps_minutes(ex.reps)
            if cur is None:
                continue
            if cur > cardio_floor:
                ex.reps = f"{cur - 1} phút"
                trimmed = True
                break
        if trimmed:
            continue

        for ex in reversed(day.exercises):
            if (ex.section or "main") != "main":
                continue
            if _ex_move_role(ex, meta_by_id) != "isolation":
                continue
            if (ex.rest_seconds or 0) > 60:
                ex.rest_seconds = 60
                trimmed = True
                break
        if trimmed:
            continue

        for ex in reversed(day.exercises):
            if (ex.section or "main") != "main":
                continue
            if parse_reps_minutes(ex.reps) is not None:
                continue
            role = _ex_move_role(ex, meta_by_id)
            if role == "isolation":
                pass
            elif role == "resistance" and ex is not first_main:
                pass
            else:
                continue
            if ex.sets > 2:
                ex.sets -= 1
                trimmed = True
                break
        if trimmed:
            continue

        for ex in reversed(day.exercises):
            if (ex.section or "main") != "main":
                continue
            if _ex_move_role(ex, meta_by_id) not in {"compound", "resistance"}:
                continue
            if (ex.rest_seconds or 0) > 120:
                ex.rest_seconds = 120
                trimmed = True
                break
        if trimmed:
            continue

        # Primer 2×4 adds ~2 min; shave rest before dropping lifts or warmup.
        for ex in reversed(day.exercises):
            if (ex.section or "main") != "main":
                continue
            if _ex_move_role(ex, meta_by_id) != "isolation":
                continue
            if (ex.rest_seconds or 0) > 45:
                ex.rest_seconds = 45
                trimmed = True
                break
        if trimmed:
            continue

        for ex in reversed(day.exercises):
            if (ex.section or "main") != "main":
                continue
            if _ex_move_role(ex, meta_by_id) not in {"compound", "resistance"}:
                continue
            if (ex.rest_seconds or 0) > 90:
                ex.rest_seconds = 90
                trimmed = True
                break
        if trimmed:
            continue

        for ex in reversed(day.exercises):
            if (ex.section or "main") != "main":
                continue
            if parse_reps_minutes(ex.reps) is not None:
                continue
            if _ex_move_role(ex, meta_by_id) not in {"compound", "resistance"}:
                continue
            if ex is first_main:
                continue
            if ex.sets > 2:
                ex.sets -= 1
                trimmed = True
                break
        if trimmed:
            continue

        if drop_exercises and main_exercise_count(day) > recipe_floor:
            for ex in reversed(day.exercises):
                if (ex.section or "main") != "main":
                    continue
                role = _ex_move_role(ex, meta_by_id)
                if role == "isolation":
                    pass
                elif role == "resistance" and ex is not first_main:
                    pass
                else:
                    continue
                day.exercises = [x for x in day.exercises if x is not ex]
                trimmed = True
                break
            if trimmed:
                continue

        # Last resort: one extra isolation even at recipe floor (keep ≥3 gym / ≥2).
        abs_floor = 2 if recipe_floor <= 3 else max(3, recipe_floor - 1)
        if drop_exercises and main_exercise_count(day) > abs_floor:
            for ex in reversed(day.exercises):
                if (ex.section or "main") != "main":
                    continue
                if _ex_move_role(ex, meta_by_id) != "isolation":
                    continue
                day.exercises = [x for x in day.exercises if x is not ex]
                trimmed = True
                break
        if not trimmed:
            break


def clamp_session_to_target(
    plan_days: list[PlanDayIn],
    *,
    session_minutes: int,
    meta_by_id: dict[int, dict[str, Any]] | dict[int, ShortlistItem],
    location: str | None = "gym",
) -> list[PlanDayIn]:
    """Hard cap every day at session_minutes after volume/top-up passes."""
    target = max(30, int(session_minutes or 45))
    cap = max(30, int(round(target * FILL_MAX_RATIO)))
    slim = _slim_meta_by_id(meta_by_id)
    home = (location or "").strip().lower() == "home"
    for day in plan_days:
        _trim_day_over_target(
            day,
            cap,
            meta_by_id=slim,
            location=location,
            drop_exercises=True,
        )
        if home and normalize_split_role(getattr(day, "split_role", None)) != "core":
            if any((ex.section or "") == "cardio" for ex in day.exercises):
                _rescale_interval_cardios_on_day(
                    day, target, convert_continuous=True
                )
                if estimate_day_minutes(day) > cap:
                    _trim_day_over_target(
                        day,
                        cap,
                        meta_by_id=slim,
                        location=location,
                        drop_exercises=True,
                    )
        for i, ex in enumerate(day.exercises, start=1):
            ex.sort_order = i
    return plan_days


def _rescale_interval_cardios_on_day(
    day: PlanDayIn,
    target: int,
    *,
    experience_level: int | None = None,
    convert_continuous: bool = False,
) -> None:
    """Re-split / re-prescribe cardio to leftover minutes (interval giây; optional phút→interval)."""
    if normalize_split_role(getattr(day, "split_role", None)) == "core":
        return
    cardios: list[PlanExerciseIn] = []
    for ex in day.exercises:
        if (ex.section or "") != "cardio":
            continue
        if interval_cardio_wall_minutes(ex) is not None:
            cardios.append(ex)
        elif convert_continuous and parse_reps_minutes(ex.reps) is not None:
            cardios.append(ex)
    if not cardios:
        return
    non_cardio = _non_cardio_exercises(day)
    budget = max(0.0, float(target) - float(estimate_exercises_minutes(non_cardio)))
    want = interval_cardio_piece_count(budget)
    if want <= 0:
        day.exercises = list(non_cardio)
        return
    if len(cardios) > want:
        keep = {id(ex) for ex in cardios[:want]}
        day.exercises = [
            ex
            for ex in day.exercises
            if (ex.section or "") != "cardio" or id(ex) in keep
        ]
        cardios = []
        for ex in day.exercises:
            if (ex.section or "") != "cardio":
                continue
            if interval_cardio_wall_minutes(ex) is not None:
                cardios.append(ex)
            elif convert_continuous and parse_reps_minutes(ex.reps) is not None:
                cardios.append(ex)
    if not cardios:
        return
    per = budget / len(cardios)
    for ex in cardios:
        sets, reps, rest, notes = interval_cardio_prescription(
            per, experience_level=experience_level
        )
        ex.sets = sets
        ex.reps = reps
        ex.rest_seconds = rest
        if not (ex.notes_vi or "").strip() or "phút" in (ex.notes_vi or ""):
            ex.notes_vi = notes


def top_up_session_minutes(
    plan_days: list[PlanDayIn],
    *,
    session_minutes: int,
    meta_by_id: dict[int, dict[str, Any]] | dict[int, ShortlistItem],
    experience_level: int | None = None,
    home_session: bool = False,
) -> list[PlanDayIn]:
    """Light pass after volume trim: bump isolation sets/cardio only (no new exercises)."""
    target = max(30, int(session_minutes or 45))
    min_target = target * FILL_MIN_RATIO
    hard_cap = (
        l1_session_set_cap(target) if int(experience_level or 99) <= 1 else None
    )
    slim_meta = _slim_meta_by_id(meta_by_id)

    for day in plan_days:
        core_day = normalize_split_role(getattr(day, "split_role", None)) == "core"
        for _ in range(12):
            if estimate_day_minutes(day) >= min_target:
                break
            if core_day:
                if not _pick_core_fill_action(
                    day.exercises,
                    slim_meta,
                    target=target,
                ):
                    break
                continue
            gap = target - estimate_day_minutes(day)
            if not _pick_fill_action(
                day.exercises,
                slim_meta,
                gap,
                hard_set_cap=hard_cap,
                max_minutes=float(target),
            ):
                break
        if home_session and not core_day:
            absorb_home_cardio_surplus_into_main_sets(
                day,
                session_minutes=session_minutes,
                meta_by_id=slim_meta,
            )
            _rescale_interval_cardios_on_day(
                day,
                target,
                experience_level=experience_level,
                convert_continuous=True,
            )
        else:
            _rescale_interval_cardios_on_day(
                day, target, experience_level=experience_level
            )
        if estimate_day_minutes(day) > target:
            _trim_day_over_target(
                day,
                target,
                meta_by_id=slim_meta,
            )
        for i, ex in enumerate(day.exercises, start=1):
            ex.sort_order = i
    return plan_days

def refill_thin_days(
    plan_days: list[PlanDayIn],
    *,
    day_contexts: list[dict[str, Any]],
    session_minutes: int,
    location: str | None,
    experience_level: int,
    db: Session,
    goal: str | None,
    extra_goals: list[str] | None,
    cardio_on_lift_days: bool,
    liss_finisher: bool,
    meta_by_id: dict[int, dict[str, Any]],
    floor: int | None = None,
) -> bool:
    """If a day has fewer main lifts than the recipe floor, add isolation from that day's shortlist."""
    from app.services.workout_generation.assemble import _recipe_for_day

    changed = False
    for day, ctx in zip(plan_days, day_contexts):
        role = ctx.get("pick_role") or getattr(day, "split_role", None)
        day_floor = (
            int(floor)
            if floor is not None
            else main_lift_floor(session_minutes, location, role)
        )
        if main_exercise_count(day) >= day_floor:
            continue
        shortlists = ctx.get("shortlists") or {}
        if not shortlists:
            continue
        recipe = _recipe_for_day(
            location=location,
            session_minutes=session_minutes,
            split_role=ctx.get("pick_role") or getattr(day, "split_role", None),
            experience_level=experience_level,
            cardio_on_lift_days=cardio_on_lift_days,
            liss_finisher=liss_finisher,
        )
        slim: dict[int, ShortlistItem] = {}
        for items in shortlists.values():
            for item in items or []:
                slim[int(item.id)] = item
        used_ids = {int(ex.exercise_id) for ex in day.exercises}
        for _ in range(day_floor):
            if main_exercise_count(day) >= day_floor:
                break
            before = main_exercise_count(day)
            if not _add_exercises_from_blocks(
                day,
                recipe=recipe,
                shortlists=shortlists,
                meta_by_id=slim,
                used_ids=used_ids,
                db=db,
                experience_level=experience_level,
                goal=goal,
                extra_goals=extra_goals,
                session_minutes=session_minutes,
            ):
                break
            if main_exercise_count(day) == before:
                break
            changed = True
        for eid, item in slim.items():
            meta_by_id.setdefault(
                int(eid),
                {
                    "movement_role": item.movement_role,
                    "movement_pattern": item.movement_pattern,
                    "muscle_slug": item.muscle_slug,
                    "name_vi": item.name_vi,
                },
            )
    return changed
