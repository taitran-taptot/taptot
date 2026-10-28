"""Assemble PlanDayIn from frame days + picked exercise ids."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.plans import PlanDayIn, PlanExerciseIn, PlanSetPrescription
from app.services.exercise_prescription import get_prescription
from app.services.workout_generation.coach_notes import (
    COOLDOWN_NOTE_VI,
    PRIMER_NOTE_BW_VI,
    PRIMER_NOTE_LOADED_VI,
    PRIMER_TIMED_NOTE_VI,
    WARMUP_NOTE_VI,
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
    clamp_dose_to_bounds,
    default_reps_label,
    dose_bounds_for_item,
    half_working_reps_label,
    primer_reps_from_baseline,
    coerce_working_reps_label,
    snap_rep_to_five_band,
)
from app.services.workout_generation.effort_mode import exercise_effort_mode
from app.services.workout_generation.rule_picker import DOSE_PICKS_KEY, PICK_FAIL_VI
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

logger = logging.getLogger(__name__)

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
            if int(item.id) in used_ids:
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
    if row is None or int(row.id) in used_ids:
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


_BIKE_GEAR_KEYS = ("bike", "cycle", "cycling", "xe-dap", "xedap", "xe đạp", "xe dap")
_GENERAL_WARMUP_REPS = "20-30 giây"
_GENERAL_WARMUP_REST = 60
_PRIMER_REST = 90


def _item_name_blob(item: Any) -> str:
    if isinstance(item, dict):
        return f"{item.get('name_vi') or ''} {item.get('name_en') or ''}".lower()
    return f"{getattr(item, 'name_vi', '') or ''} {getattr(item, 'name_en', '') or ''}".lower()


def _general_warmup_kind(item: Any) -> str | None:
    blob = _item_name_blob(item)
    if "cycling warmup" in blob or "đạp xe khởi động" in blob or "dap xe khoi dong" in blob:
        return "cycle"
    if any(k in blob for k in ("jumping jack", "nhảy dang", "nhay dang", "nhảy jacks", "nhay jacks")):
        return "jack"
    return None


def _as_shortlist_item(item: Any, *, fallback_id: int | None = None) -> ShortlistItem | None:
    if isinstance(item, ShortlistItem):
        return item
    try:
        eid = int(item.get("id") if isinstance(item, dict) else getattr(item, "id", fallback_id))
    except (TypeError, ValueError):
        return None
    if isinstance(item, dict):
        name_vi = str(item.get("name_vi") or "")
        name_en = item.get("name_en")
        role = item.get("movement_role")
        pattern = item.get("movement_pattern")
        muscle = str(item.get("muscle_slug") or item.get("muscle") or "")
        difficulty = int(item.get("difficulty") or 1)
        eq = item.get("equipment_slugs") or ()
    else:
        name_vi = str(getattr(item, "name_vi", "") or "")
        name_en = getattr(item, "name_en", None)
        role = getattr(item, "movement_role", None)
        pattern = getattr(item, "movement_pattern", None)
        muscle = str(getattr(item, "muscle_slug", None) or getattr(item, "muscle", None) or "")
        difficulty = int(getattr(item, "difficulty", None) or 1)
        eq = getattr(item, "equipment_slugs", None) or ()
    return ShortlistItem(
        id=eid,
        name_vi=name_vi or "Khởi động",
        name_en=name_en,
        movement_role=role or "cardio",
        movement_pattern=pattern or "other",
        muscle_slug=muscle or "cardio",
        difficulty=difficulty,
        equipment_slugs=frozenset(str(s).strip().lower() for s in eq if str(s).strip()),
    )


def _prefers_cycling_warmup(equipment_slugs: list[str] | None) -> bool:
    blob = " ".join(str(s or "") for s in (equipment_slugs or [])).lower()
    return any(k in blob for k in _BIKE_GEAR_KEYS)


def _scan_general_warmup(items: list[Any]) -> tuple[ShortlistItem | None, ShortlistItem | None]:
    jack: ShortlistItem | None = None
    cycle: ShortlistItem | None = None
    for raw in items:
        kind = _general_warmup_kind(raw)
        if kind is None:
            continue
        item = _as_shortlist_item(raw)
        if item is None:
            continue
        if kind == "jack" and jack is None:
            jack = item
        elif kind == "cycle" and cycle is None:
            cycle = item
    return jack, cycle


def _lookup_general_warmup(
    *,
    meta_by_id: dict[int, Any] | None,
    shortlists: dict[str, list[ShortlistItem]] | None,
    equipment_slugs: list[str] | None,
    db: Session | None,
) -> ShortlistItem | None:
    scanned: list[Any] = []
    if meta_by_id:
        scanned.extend(meta_by_id.values())
    if shortlists:
        for rows in shortlists.values():
            scanned.extend(rows or [])
    jack, cycle = _scan_general_warmup(scanned)
    if db is not None and (jack is None or cycle is None):
        from sqlalchemy import or_

        from app.models.entities import Exercise, MuscleGroup

        rows = (
            db.query(Exercise, MuscleGroup)
            .join(MuscleGroup, MuscleGroup.id == Exercise.muscle_group_id)
            .filter(Exercise.is_active.is_(True))
            .filter(
                or_(
                    Exercise.name_en.ilike("%jumping jack%"),
                    Exercise.name_en.ilike("%cycling warmup%"),
                    Exercise.name_vi.ilike("%nhảy dang%"),
                    Exercise.name_vi.ilike("%đạp xe khởi động%"),
                )
            )
            .all()
        )
        db_items = [
            ShortlistItem(
                id=int(ex.id),
                name_vi=str(ex.name_vi or ""),
                name_en=ex.name_en,
                movement_role=ex.movement_role or "cardio",
                movement_pattern=ex.movement_pattern or "other",
                muscle_slug=str(mg.slug or "cardio"),
                difficulty=int(ex.difficulty or 1),
            )
            for ex, mg in rows
        ]
        db_jack, db_cycle = _scan_general_warmup(db_items)
        jack = jack or db_jack
        cycle = cycle or db_cycle
    if _prefers_cycling_warmup(equipment_slugs) and cycle is not None:
        return cycle
    return jack or cycle


def _cooldown_cap(session_minutes: int | None) -> int:
    try:
        minutes = int(session_minutes or 45)
    except (TypeError, ValueError):
        minutes = 45
    return 3 if minutes >= 60 else 2


_SPLIT_PRIMARY_REGIONS: dict[str, tuple[str, ...]] = {
    "pull": ("back",),
    "push": ("chest",),
    "legs": ("quads", "glutes", "hamstrings"),
    "lower": ("quads", "glutes", "hamstrings"),
    "upper": ("chest", "back"),
}


def _main_regions(day: PlanDayIn, meta_by_id: dict[int, Any]) -> list[str]:
    from app.services.workout_generation.split_map import normalize_split_role, region_for_muscle

    trained: list[str] = []
    for ex in day.exercises:
        if (ex.section or "main") != "main":
            continue
        meta = meta_by_id.get(int(ex.exercise_id))
        slug = ""
        if isinstance(meta, dict):
            slug = str(meta.get("muscle_slug") or meta.get("muscle") or "")
        elif meta is not None:
            slug = str(getattr(meta, "muscle_slug", None) or getattr(meta, "muscle", None) or "")
        region = region_for_muscle(slug)
        if region and region not in trained:
            trained.append(region)
    role = normalize_split_role(getattr(day, "split_role", None))
    ordered: list[str] = []
    for region in list(_SPLIT_PRIMARY_REGIONS.get(role, ())) + trained:
        if region not in ordered:
            ordered.append(region)
    return ordered


def _cooldown_candidates(
    shortlists: dict[str, list[ShortlistItem]] | None,
    meta_by_id: dict[int, Any],
) -> list[ShortlistItem]:
    from app.services.workout_generation.split_map import is_stretch_item

    found: list[ShortlistItem] = []
    seen: set[int] = set()
    pools: list[Any] = []
    if shortlists:
        pools.extend(shortlists.get("cooldown") or [])
        for key, rows in shortlists.items():
            if key == "cooldown":
                continue
            pools.extend(rows or [])
    pools.extend(meta_by_id.values())
    for raw in pools:
        item = _as_shortlist_item(raw)
        if item is None or int(item.id) in seen:
            continue
        if not is_stretch_item(item):
            continue
        seen.add(int(item.id))
        found.append(item)
    return found


def _canonical_stretch_rank(item: ShortlistItem, region: str) -> int:
    from app.services.workout_generation.split_map import CANONICAL_STRETCH_NAMES

    blob = f"{item.name_vi or ''} {item.name_en or ''}".lower()
    for index, needle in enumerate(CANONICAL_STRETCH_NAMES.get(region, ())):
        if needle in blob:
            return index
    return len(CANONICAL_STRETCH_NAMES.get(region, ()))


def _pick_cooldown_stretches(
    candidates: list[ShortlistItem],
    regions: list[str],
    *,
    cap: int,
    user_gear: set[str],
) -> list[ShortlistItem]:
    from app.services.workout_generation.home_gear_priority import TIER_GEAR, gear_tier
    from app.services.workout_generation.split_map import stretch_matches_region

    def _geared(item: ShortlistItem) -> bool:
        return gear_tier(item.equipment_slugs, user_gear) == TIER_GEAR

    picked: list[ShortlistItem] = []
    used: set[int] = set()
    for region in regions:
        if len(picked) >= cap:
            break
        matches = [c for c in candidates if int(c.id) not in used and stretch_matches_region(c, region)]
        if not matches:
            continue
        geared = [c for c in matches if _geared(c)]
        pool = geared or matches
        pool.sort(key=lambda c: (0 if _geared(c) else 1, _canonical_stretch_rank(c, region), int(c.id)))
        choice = pool[0]
        picked.append(choice)
        used.add(int(choice.id))
    return picked


def _lookup_canonical_stretches(
    db: Session | None,
    regions: list[str],
    *,
    already: set[int],
) -> list[ShortlistItem]:
    """Catalog bodyweight stretches for a region when the gear pool has none."""
    if db is None or not regions:
        return []
    from sqlalchemy import or_

    from app.models.entities import Exercise, MuscleGroup
    from app.services.workout_generation.split_map import CANONICAL_STRETCH_NAMES, stretch_matches_region

    needles: list[str] = []
    for region in regions:
        for needle in CANONICAL_STRETCH_NAMES.get(region, ()):
            if needle.isascii() and needle not in needles:
                needles.append(needle)
    if not needles:
        return []
    rows = (
        db.query(Exercise, MuscleGroup)
        .join(MuscleGroup, MuscleGroup.id == Exercise.muscle_group_id)
        .filter(Exercise.is_active.is_(True))
        .filter(
            or_(
                *[
                    clause
                    for needle in needles
                    for clause in (
                        Exercise.name_en.ilike(f"%{needle}%"),
                        Exercise.name_vi.ilike(f"%{needle}%"),
                    )
                ]
            )
        )
        .all()
    )
    found: list[ShortlistItem] = []
    for ex, mg in rows:
        if int(ex.id) in already:
            continue
        item = ShortlistItem(
            id=int(ex.id),
            name_vi=str(ex.name_vi or ""),
            name_en=ex.name_en,
            movement_role=ex.movement_role or "mobility",
            movement_pattern=ex.movement_pattern or "other",
            muscle_slug=str(mg.slug or "stretch"),
            difficulty=int(ex.difficulty or 1),
        )
        if any(stretch_matches_region(item, region) for region in regions):
            found.append(item)
            already.add(int(item.id))
    return found


def ensure_cooldown_stretches(
    day: PlanDayIn,
    *,
    shortlists: dict[str, list[ShortlistItem]] | None,
    used_ids: set[int],
    meta_by_id: dict[int, ShortlistItem],
    session_minutes: int | None = None,
    equipment_slugs: list[str] | None = None,
    db: Session | None = None,
) -> None:
    """Replace cooldown with stretches for the muscles just trained.

    Prefer a stretch that uses the user's gear. Bodyweight stretches fill a
    region only when that region has no geared stretch.
    """
    from app.services.workout_generation.home_gear_priority import user_gear_set

    from app.services.workout_generation.split_map import stretch_matches_region

    regions = _main_regions(day, meta_by_id)
    candidates = _cooldown_candidates(shortlists, meta_by_id)
    missing = [
        region
        for region in regions
        if not any(stretch_matches_region(item, region) for item in candidates)
    ]
    candidates.extend(
        _lookup_canonical_stretches(db, missing, already={int(item.id) for item in candidates})
    )
    cap = _cooldown_cap(session_minutes)
    picks = _pick_cooldown_stretches(
        candidates,
        regions,
        cap=cap,
        user_gear=user_gear_set(equipment_slugs) if equipment_slugs else set(),
    )
    if not picks and any((ex.section or "").strip().lower() == "cooldown" for ex in day.exercises):
        return
    old_ids = {
        int(ex.exercise_id)
        for ex in day.exercises
        if (ex.section or "").strip().lower() == "cooldown"
    }
    kept = [ex for ex in day.exercises if (ex.section or "").strip().lower() != "cooldown"]
    still_used = {int(ex.exercise_id) for ex in kept}
    for eid in old_ids:
        if eid not in still_used:
            used_ids.discard(eid)
    for item in picks:
        kept.append(
            PlanExerciseIn(
                exercise_id=int(item.id),
                sets=2,
                reps="30 giây",
                rest_seconds=20,
                section="cooldown",
                notes_vi=COOLDOWN_NOTE_VI,
                sort_order=len(kept) + 1,
            )
        )
        used_ids.add(int(item.id))
        meta_by_id[int(item.id)] = item
    day.exercises = kept


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
        existing.sets = 1
        existing.reps = reps
        existing.notes_vi = hold_note_vi(reps)
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
        sets=1,
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


def _is_abs_main_ex(ex: PlanExerciseIn, meta: Any | None) -> bool:
    if str(ex.section or "main") not in {"main", "exercises"}:
        return False
    if meta is not None and _is_any_front_plank(meta):
        return True
    blob = ""
    slug = ""
    if isinstance(meta, dict):
        blob = f"{meta.get('name_en') or ''} {meta.get('name_vi') or ''}".lower()
        slug = str(meta.get("muscle_slug") or "")
    elif meta is not None:
        blob = f"{getattr(meta, 'name_en', '') or ''} {getattr(meta, 'name_vi', '') or ''}".lower()
        slug = str(getattr(meta, "muscle_slug", "") or "")
    if "plank" in blob:
        return True
    if any(
        token in blob
        for token in (
            "dead bug",
            "v-up",
            "russian twist",
            "side plank",
            "situp",
            "sit-up",
            "crunch",
            "gập bụng",
            "gap bung",
            "xoay người",
            "xoay nguoi",
        )
    ):
        return True
    return slug in {"core", "co-bung", "abs", "waist", "bung"}


def ensure_leading_plank(
    day: PlanDayIn,
    *,
    meta_by_id: dict[int, Any] | None = None,
    fitness_baseline: dict[str, Any] | None = None,
    shortlists: dict[str, list[ShortlistItem]] | None = None,
    used_ids: set[int] | None = None,
    db: Session | None = None,
) -> PlanDayIn:
    """One front-elbow plank as the first abs main, 1 set at 80% of the plank test."""
    reps = plank_finisher_reps(fitness_baseline)
    kept: list[PlanExerciseIn] = []
    plank: PlanExerciseIn | None = None
    for ex in day.exercises:
        meta = (meta_by_id or {}).get(int(ex.exercise_id)) if getattr(ex, "exercise_id", None) else None
        is_main = (ex.section or "main") in {"main", "exercises"}
        is_fp = bool(meta and is_main and _is_any_front_plank(meta))
        if not is_fp:
            kept.append(ex)
            continue
        if plank is not None:
            continue
        ex.sets = 1
        ex.reps = reps
        if int(getattr(ex, "rest_seconds", 0) or 0) < REST_ISOLATION_FLOOR_SEC:
            ex.rest_seconds = REST_ISOLATION_FLOOR_SEC
        ex.notes_vi = hold_note_vi(reps)
        plank = ex
        kept.append(ex)
    day.exercises = kept

    def _abs_indexes() -> list[int]:
        out: list[int] = []
        for i, ex in enumerate(day.exercises):
            meta = (meta_by_id or {}).get(int(ex.exercise_id)) if getattr(ex, "exercise_id", None) else None
            if _is_abs_main_ex(ex, meta):
                out.append(i)
        return out

    abs_idxs = _abs_indexes()
    if plank is None and abs_idxs:
        taken = set(used_ids or ())
        pick = _lookup_elbow_plank(shortlists=shortlists, used_ids=taken, db=db)
        if pick is not None:
            insert_at = abs_idxs[0]
            plank = PlanExerciseIn(
                exercise_id=int(pick.id),
                sets=1,
                reps=reps,
                rest_seconds=REST_ISOLATION_FLOOR_SEC,
                section="main",
                notes_vi=hold_note_vi(reps),
                sort_order=insert_at + 1,
            )
            day.exercises = [*day.exercises[:insert_at], plank, *day.exercises[insert_at:]]
            if used_ids is not None:
                used_ids.add(int(pick.id))
            if meta_by_id is not None:
                meta_by_id[int(pick.id)] = pick
            abs_idxs = _abs_indexes()
    if plank is None:
        return day
    pidx = next(
        (
            i
            for i, ex in enumerate(day.exercises)
            if ex is plank
            or (
                int(getattr(ex, "exercise_id", 0) or 0) == int(plank.exercise_id)
                and str(ex.section or "main") in {"main", "exercises"}
            )
        ),
        None,
    )
    abs_idxs = _abs_indexes()
    if pidx is None or not abs_idxs or pidx == abs_idxs[0]:
        return day
    item = day.exercises.pop(pidx)
    dest = abs_idxs[0]
    if pidx < dest:
        dest -= 1
    day.exercises.insert(dest, item)
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
    equipment_slugs: list[str] | None = None,
    shortlists: dict[str, list[ShortlistItem]] | None = None,
    db: Session | None = None,
) -> PlanDayIn:
    """Warmup is Jumping Jack or Cycling Warmup, then 2 half-rep sets of the first main."""
    del session_minutes
    mains = [ex for ex in day.exercises if (ex.section or "main") == "main"]
    rest = [ex for ex in day.exercises if (ex.section or "") not in {"warmup"}]
    if not mains:
        return day
    first = mains[0]
    timed = _is_timed_prescription(first.reps)
    meta = meta_by_id.get(int(first.exercise_id)) if meta_by_id else None
    loaded = looks_loaded(meta, no_equipment=no_equipment)
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
    primer = PlanExerciseIn(
        exercise_id=int(first.exercise_id),
        sets=2,
        reps=primer_reps,
        rest_seconds=_PRIMER_REST,
        section="warmup",
        notes_vi=(
            PRIMER_TIMED_NOTE_VI
            if timed or _is_timed_prescription(primer_reps)
            else (PRIMER_NOTE_LOADED_VI if loaded else PRIMER_NOTE_BW_VI)
        ),
        sort_order=0,
    )
    general = _lookup_general_warmup(
        meta_by_id=meta_by_id,
        shortlists=shortlists,
        equipment_slugs=equipment_slugs,
        db=db,
    )
    new_wu: list[PlanExerciseIn] = []
    if general is not None and int(general.id) != int(first.exercise_id):
        new_wu.append(
            PlanExerciseIn(
                exercise_id=int(general.id),
                sets=2,
                reps=_GENERAL_WARMUP_REPS,
                rest_seconds=_GENERAL_WARMUP_REST,
                section="warmup",
                notes_vi=WARMUP_NOTE_VI,
                sort_order=0,
            )
        )
        if meta_by_id is not None and int(general.id) not in meta_by_id:
            meta_by_id[int(general.id)] = general
    new_wu.append(primer)
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
    strict_picks: bool = False,
    precomputed_shortlists: dict[str, list[ShortlistItem]] | None = None,
    pushups_max: int | None = None,
    fitness_baseline: dict[str, Any] | None = None,
    challenge_session: bool = False,
    focus_areas: list[str] | None = None,
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
        server_filled_block = block.block_key in {
            "general_warmup",
            "dynamic_mobility",
            "cooldown",
        }
        chosen = repair_block_picks(
            block=block,
            picked_ids=raw,
            shortlist=shortlists.get(block.block_key, []),
            used_ids=used,
            # Mobility is selected deterministically by the server. A tiny
            # shortlist may need to reuse a warm-up item for cooldown, so it
            # must not hard-fail merely because the pick omitted that block.
            fill_missing=(not strict_picks or server_filled_block),
            user_gear=user_gear if strength_block else None,
        )
        if not chosen and not block.is_optional and _target_count(block) > 0:
            shortlist = shortlists.get(block.block_key, [])
            if strict_picks and not shortlist:
                logger.warning(
                    "Strict assembly missing required block: role=%s block=%s "
                    "picked=%s shortlist_size=%s",
                    role,
                    block.block_key,
                    raw,
                    0,
                )
                raise BadRequestError(
                    PICK_FAIL_VI
                )
            chosen = repair_block_picks(
                block=block,
                picked_ids=[],
                shortlist=shortlist,
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
                if (challenge_session or not home_session)
                else None
            )
            apply_proposed_dose = (not timed) or bool(
                challenge_session and proposal and effort_mode == "hold"
            )
            if apply_proposed_dose:
                bounds = dose_bounds_for_item(
                    meta or {
                        "movement_role": move_role,
                    },
                    experience_level=experience_level,
                    fitness_baseline=fitness_baseline,
                    plan_section=block.plan_section,
                    no_equipment=no_equipment,
                    home_session=home_session,
                    challenge=challenge_session,
                )
                default_reps = (
                    default_reps_label(bounds)
                    if home_session and str(bounds.get("work_mode")) == "reps"
                    else str(reps)
                )
                from app.services.workout_generation.dose_bounds import is_hard_bw_skill_item

                sets, reps = clamp_dose_to_bounds(
                    proposal,
                    bounds,
                    default_sets=int(sets),
                    default_reps=default_reps,
                    prefer_proposal_reps=bool(
                        challenge_session
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
                            challenge_session
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
            if challenge_session and proposal and proposal.get("rest_seconds") is not None:
                rest_seconds = clamp_challenge_rest_seconds(
                    proposal.get("rest_seconds"),
                    rest_seconds,
                    movement_role=move_role,
                )
            from app.services.schedule_spec_master import snap_session_minutes

            if (
                snap_session_minutes(int(session_minutes or 45)) <= 45
                and (block.plan_section or "") == "main"
            ):
                role_l = str(move_role or "").strip().lower()
                if role_l in {"compound", "resistance"}:
                    rest_seconds = 120
                elif role_l == "isolation":
                    rest_seconds = 90

            set_rx = None
            if challenge_session and proposal:
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
        equipment_slugs=list(equipment_slugs or []),
        shortlists=shortlists,
        db=db,
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
        equipment_slugs=list(equipment_slugs or []),
        shortlists=shortlists,
        db=db,
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
    if not home_session:
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
        session_minutes=session_minutes,
        equipment_slugs=list(equipment_slugs or []),
        db=db,
    )
    day.exercises = reorder_main_section_exercises(
        role,
        day.exercises,
        meta_by_id,
        focus_slugs=focus_slugs,
    )
    from app.services.workout_generation.kit_schedule import apply_kit_mains

    apply_kit_mains(
        day,
        db,
        equipment_slugs=list(equipment_slugs or []),
        fitness_baseline=fitness_baseline,
        experience_level=experience_level,
        session_minutes=session_minutes,
        meta_by_id=meta_by_id,
        home_session=home_session,
        challenge_session=challenge_session,
        focus_keys=focus_areas,
    )
    ensure_leading_plank(
        day,
        meta_by_id=meta_by_id,
        fitness_baseline=fitness_baseline,
        shortlists=shortlists,
        used_ids=used,
        db=db,
    )
    inject_main_primer_warmup(
        day,
        meta_by_id=meta_by_id,
        no_equipment=no_equipment,
        fitness_baseline=fitness_baseline,
        home_session=home_session,
        experience_level=experience_level,
        session_minutes=session_minutes,
        equipment_slugs=list(equipment_slugs or []),
        shortlists=shortlists,
        db=db,
    )
    attach_band_set_prescriptions(
        day, meta_by_id=meta_by_id, fitness_baseline=fitness_baseline
    )
    attach_db_set_prescriptions(
        day, meta_by_id=meta_by_id, fitness_baseline=fitness_baseline
    )
    ensure_cooldown_stretches(
        day,
        shortlists=shortlists,
        used_ids=used,
        meta_by_id=meta_by_id,
        session_minutes=session_minutes,
        equipment_slugs=list(equipment_slugs or []),
        db=db,
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
    focus_areas: list[str] | None = None,
) -> list[dict]:
    """Recipe blocks + slot pools for the rule picker.

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
    from app.services.workout_generation.rule_picker import clamp_pick_count
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
            location=loc,
            focus_slugs=focus_slugs,
            day_index=int(getattr(frame_day, "day_index", 0) or 0),
            allow_bar_moves="pull-up-bar" in {
                str(s).strip().lower() for s in (equipment_slugs or [])
            },
            experience_level=experience_level,
            no_equipment=no_equipment,
            session_minutes=session_minutes,
            focus_areas=focus_areas,
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
