"""Deterministic Pull-day menu for home bar / rings from pullups_max."""

from __future__ import annotations

from typing import Any, Callable

from app.schemas.plans import PlanExerciseIn
from app.services.workout_generation.shortlist import expand_equipment_aliases
from app.services.workout_generation.skill_gate import (
    REQUIRE_PULLUP_MIN,
    is_strict_pullup_item,
    pullups_max_unspecified,
)
from app.services.workout_generation.split_map import (
    is_denied_for_split,
    normalize_split_role,
)
from app.services.workout_generation.weekly_volume import fold_lift_name

BACKPACK_ROW_MIN_PULLUPS = 3
RING_COMBO_MIN = 10
RING_LEGS_SQUAT_MIN = 30
RING_LEGS_EXPERIENCE_MIN = 2
_LEG_SPLITS = frozenset({"legs", "lower", "fb", "fb_a", "fb_b"})
_PUSH_SPLITS = frozenset({"push", "upper", "fb", "fb_b"})
_BAR_RINGS = frozenset({"pull-up-bar", "gymnastic-rings"})
_PULL_SPLITS = frozenset({"pull"})
_PULL_FAMILY_SPLITS = frozenset({"pull", "upper", "fb", "fb_a", "fb_b"})
_FILL_SPLITS = frozenset({"push", "legs", "lower", "pull"})

_BACKPACK_NEEDLES = (
    "backpack row",
    "cheo ba lo",
    "chèo ba lô",
    "balo",
    "ba lo",
    "ba lô",
)
_RING_ROW_NEEDLES = (
    "ring row",
    "cheo vong",
    "chèo vòng",
    "keo ngang",
    "kéo ngang",
)
_REAR_DELT_NEEDLES = (
    "rear delt",
    "rear-delt",
    "vai sau",
    "delt fly",
)
_FACE_PULL_NEEDLES = ("face pull", "face-pull", "keo mat", "kéo mặt")
_CHIN_NEEDLES = ("chin-up", "chinup", "chin up", "xa up", "xà úp")
_RING_PU_NEEDLES = (
    "ring pull-up",
    "ring pullup",
    "ring pull up",
    "hit xa vong",
    "hít xà vòng",
)
_HANGING_CORE_NEEDLES = (
    "toes-to-bar",
    "toes to bar",
    "hanging knee",
    "hanging leg",
    "treo goi",
    "treo gối",
    "treo chan",
    "treo chân",
    "nang goi treo",
    "nâng gối treo",
)
_TRICEPS_LEAK = (
    "triceps extension",
    "duoi tay sau",
    "duỗi tay sau",
    "tay sau",
)
_CHEST_LEAK = (
    "chest fly",
    "chest press",
    "ring fly",
    "ring push",
    "push-up",
    "pushup",
    "push up",
    "chong day",
    "chống đẩy",
    "dip",
)
_FRONT_DELT_LEAK = (
    "front raise",
    "front delt",
    "vai truoc",
    "vai trước",
    "anterior delt",
)
_CORE_LEAK = ("plank", "crunch", "sit-up", "situp", "hollow", "dead bug")


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def pullups_max_of(fitness_baseline: dict[str, Any] | None) -> int | None:
    return _as_int((fitness_baseline or {}).get("pullups_max"))


def load_bar_rings_menu_catalog(db: Any) -> list[dict[str, Any]]:
    """Pull-up family at difficulty 2–3 — L1 SQL bands omit these from shortlists."""
    from app.models.entities import Exercise, MuscleGroup

    rows = (
        db.query(Exercise, MuscleGroup)
        .join(MuscleGroup, MuscleGroup.id == Exercise.muscle_group_id)
        .filter(
            Exercise.is_active.is_(True),
            Exercise.owner_user_id.is_(None),
            Exercise.difficulty.in_((1, 2, 3)),
        )
        .all()
    )
    out: list[dict[str, Any]] = []
    for ex, mg in rows:
        meta = {
            "id": int(ex.id),
            "name_vi": ex.name_vi,
            "name_en": getattr(ex, "name_en", None),
            "movement_role": ex.movement_role,
            "movement_pattern": ex.movement_pattern,
            "muscle_slug": mg.slug,
        }
        if (
            is_strict_pullup_item(meta)
            or is_ring_row_item(meta)
            or is_ring_rear_delt_item(meta)
            or is_ring_face_pull_item(meta)
            or is_hanging_core_item(meta)
            or is_ring_hamstring_curl_item(meta)
            or is_bulgarian_ring_squat_item(meta)
            or is_ring_dip_item(meta)
        ):
            out.append(meta)
    return out


def bar_rings_menu_active(
    equipment_slugs: Any = None,
    *,
    location: str | None = None,
    no_equipment: bool = False,
) -> bool:
    if no_equipment:
        return False
    if str(location or "").strip().lower() != "home":
        return False
    user = expand_equipment_aliases(equipment_slugs)
    return bool(user & _BAR_RINGS)


def _as_meta_dict(meta: Any) -> dict[str, Any]:
    if meta is None:
        return {}
    if isinstance(meta, dict):
        return dict(meta)
    return {
        "id": getattr(meta, "id", None),
        "name_vi": getattr(meta, "name_vi", None),
        "name_en": getattr(meta, "name_en", None),
        "movement_role": getattr(meta, "movement_role", None),
        "movement_pattern": getattr(meta, "movement_pattern", None),
        "muscle_slug": getattr(meta, "muscle_slug", None),
        "difficulty": getattr(meta, "difficulty", None),
        "equipment_slugs": getattr(meta, "equipment_slugs", None),
    }


def _merge_meta_entry(meta_by_id: dict[int, Any], eid: int, meta: Any) -> None:
    cur = meta_by_id.get(eid)
    if not isinstance(cur, dict):
        cur = _as_meta_dict(cur)
    extra = _as_meta_dict(meta)
    cur.update({k: v for k, v in extra.items() if v not in (None, "")})
    meta_by_id[eid] = cur


def _blob(meta: dict[str, Any] | None) -> str:
    meta = _as_meta_dict(meta)
    return fold_lift_name(f"{meta.get('name_vi') or ''} {meta.get('name_en') or ''}")


def is_backpack_row_name(name_vi: str | None = None, name_en: str | None = None) -> bool:
    blob = fold_lift_name(f"{name_vi or ''} {name_en or ''}")
    if not blob:
        return False
    if "good morning" in blob or "cui nguoi om" in blob:
        return False
    return any(k in blob for k in _BACKPACK_NEEDLES)


def deny_backpack_row(
    fitness_baseline: dict[str, Any] | None,
    *,
    day_has_strict_pullup: bool = False,
) -> bool:
    n = pullups_max_of(fitness_baseline)
    if day_has_strict_pullup:
        return True
    return n is not None and n >= BACKPACK_ROW_MIN_PULLUPS


def is_ring_row_item(meta: dict[str, Any] | None) -> bool:
    blob = _blob(meta)
    if any(k in blob for k in _FACE_PULL_NEEDLES):
        return False
    if is_strict_pullup_item(meta or {}):
        return False
    return any(k in blob for k in _RING_ROW_NEEDLES)


def is_ring_rear_delt_item(meta: dict[str, Any] | None) -> bool:
    blob = _blob(meta)
    return any(k in blob for k in _REAR_DELT_NEEDLES) and (
        "ring" in blob or "vong" in blob or "vòng" in blob
    )


def is_ring_face_pull_item(meta: dict[str, Any] | None) -> bool:
    blob = _blob(meta)
    if not any(k in blob for k in _FACE_PULL_NEEDLES):
        return False
    return "ring" in blob or "vong" in blob or "vòng" in blob or "treo" in blob


def is_chin_up_item(meta: dict[str, Any] | None) -> bool:
    if not is_strict_pullup_item(meta or {}):
        return False
    blob = _blob(meta)
    return any(k in blob for k in _CHIN_NEEDLES)


def is_ring_pullup_item(meta: dict[str, Any] | None) -> bool:
    if not is_strict_pullup_item(meta or {}):
        return False
    blob = _blob(meta)
    return any(k in blob for k in _RING_PU_NEEDLES) or "vong" in blob or "vòng" in blob


def is_bar_pullup_item(meta: dict[str, Any] | None) -> bool:
    if not is_strict_pullup_item(meta or {}):
        return False
    if is_chin_up_item(meta) or is_ring_pullup_item(meta):
        return False
    return True


def is_ring_hamstring_curl_item(meta: dict[str, Any] | None) -> bool:
    blob = _blob(meta)
    return "hamstring curl" in blob and ("ring" in blob or "vong" in blob or "vòng" in blob)


def is_assisted_ring_dip_item(meta: dict[str, Any] | None) -> bool:
    blob = _blob(meta)
    return "assisted ring dip" in blob or "dip vong co tro" in blob or "dip vòng có trợ" in blob


def is_ring_dip_item(meta: dict[str, Any] | None) -> bool:
    blob = _blob(meta)
    if is_assisted_ring_dip_item(meta):
        return False
    return "ring dip" in blob or "dip vong" in blob or "dip vòng" in blob


def is_bulgarian_ring_squat_item(meta: dict[str, Any] | None) -> bool:
    blob = _blob(meta)
    bulgarian = "bulgarian" in blob or "bulgaria" in blob
    ring = "ring" in blob or "vong" in blob or "vòng" in blob
    return bulgarian and ring


def squats_max_of(fitness_baseline: dict[str, Any] | None) -> int | None:
    return _as_int((fitness_baseline or {}).get("squats_max"))


def must_include_ring_legs(
    fitness_baseline: dict[str, Any] | None,
    equipment_slugs: Any = None,
    *,
    experience_level: int | None = None,
    location: str | None = "home",
    no_equipment: bool = False,
) -> bool:
    if not bar_rings_menu_active(
        equipment_slugs, location=location, no_equipment=no_equipment
    ):
        return False
    if int(experience_level or 1) < RING_LEGS_EXPERIENCE_MIN:
        return False
    n = squats_max_of(fitness_baseline)
    return n is not None and n > RING_LEGS_SQUAT_MIN


def is_hanging_core_item(meta: dict[str, Any] | None) -> bool:
    blob = _blob(meta)
    return any(k in blob for k in _HANGING_CORE_NEEDLES)


def is_pull_leak_item(meta: dict[str, Any] | None) -> bool:
    """Chest / front-delt / triceps / non-hanging core on a Pull day."""
    meta = meta or {}
    if is_hanging_core_item(meta):
        return False
    if is_denied_for_split(
        "pull",
        pattern=str(meta.get("movement_pattern") or ""),
        muscle_slug=str(meta.get("muscle_slug") or ""),
    ):
        return True
    blob = _blob(meta)
    if any(k in blob for k in _TRICEPS_LEAK + _CHEST_LEAK + _FRONT_DELT_LEAK):
        return True
    pattern = str(meta.get("movement_pattern") or "").strip().lower()
    if pattern == "core" and not is_hanging_core_item(meta):
        return True
    if any(k in blob for k in _CORE_LEAK):
        return True
    return False


Matcher = Callable[[dict[str, Any] | None], bool]


_REGRESSION_NEEDLES = (
    "chin-over-bar",
    "hold negative",
    "giu cam",
    "giữ cằm",
    "dead hang",
    "treo nguoi",
    "treo người",
)


def is_pull_regression_item(meta: dict[str, Any] | None) -> bool:
    blob = _blob(meta)
    return any(k in blob for k in _REGRESSION_NEEDLES)


def required_pull_matchers(
    pullups_max: int | None, *, unspecified: bool = False
) -> list[Matcher]:
    if unspecified:
        return [is_bar_pullup_item, is_chin_up_item]
    n = pullups_max if pullups_max is not None else 0
    if n < REQUIRE_PULLUP_MIN:
        return [is_ring_row_item, is_ring_rear_delt_item, is_ring_face_pull_item]
    if n < RING_COMBO_MIN:
        return [is_bar_pullup_item, is_chin_up_item]
    return [
        is_bar_pullup_item,
        is_chin_up_item,
        is_ring_pullup_item,
        is_ring_row_item,
        is_ring_rear_delt_item,
        is_ring_face_pull_item,
    ]


def _candidate_meta(raw: Any) -> tuple[int, dict[str, Any]] | None:
    if isinstance(raw, dict):
        try:
            eid = int(raw.get("id") or raw.get("exercise_id"))
        except (TypeError, ValueError):
            return None
        meta = {
            "name_vi": raw.get("name_vi"),
            "name_en": raw.get("name_en"),
            "movement_role": raw.get("movement_role"),
            "movement_pattern": raw.get("movement_pattern") or raw.get("pattern"),
            "muscle_slug": raw.get("muscle_slug") or raw.get("muscle"),
        }
        return eid, meta
    try:
        eid = int(getattr(raw, "id", None) or getattr(raw, "exercise_id"))
    except (TypeError, ValueError, AttributeError):
        return None
    meta = {
        "name_vi": getattr(raw, "name_vi", None),
        "name_en": getattr(raw, "name_en", None),
        "movement_role": getattr(raw, "movement_role", None),
        "movement_pattern": getattr(raw, "movement_pattern", None),
        "muscle_slug": getattr(raw, "muscle_slug", None),
    }
    return eid, meta


def _is_main(ex: Any) -> bool:
    return (getattr(ex, "section", "main") or "main") == "main"


def _copy_ex(template: Any, eid: int) -> PlanExerciseIn:
    if isinstance(template, PlanExerciseIn):
        return template.model_copy(update={"exercise_id": eid, "section": "main"})
    return PlanExerciseIn(
        exercise_id=eid,
        section="main",
        sets=int(getattr(template, "sets", None) or 3),
        reps=getattr(template, "reps", None) or "8",
        rest_seconds=int(getattr(template, "rest_seconds", None) or 90),
    )


def _find_in_pool(
    pool: list[tuple[int, dict[str, Any]]],
    match: Matcher,
    used: set[int],
) -> tuple[int, dict[str, Any]] | None:
    for eid, meta in pool:
        if eid in used:
            continue
        if match(meta):
            return eid, meta
    return None


def _fill_matchers() -> list[Matcher]:
    return [is_hanging_core_item, lambda m: str((m or {}).get("movement_pattern") or "") == "core"]


def dedupe_session_exercises(exercises: list[Any]) -> list[Any]:
    seen: set[int] = set()
    out: list[Any] = []
    for ex in exercises:
        try:
            eid = int(ex.exercise_id)
        except (TypeError, ValueError, AttributeError):
            out.append(ex)
            continue
        if not _is_main(ex):
            out.append(ex)
            continue
        if eid in seen:
            continue
        seen.add(eid)
        out.append(ex)
    return out


def repair_plan_day_pull_menu(
    day: Any,
    *,
    candidates: list[Any],
    meta_by_id: dict[int, dict[str, Any]],
    fitness_baseline: dict[str, Any] | None,
    equipment_slugs: Any = None,
    location: str | None = "home",
    no_equipment: bool = False,
) -> bool:
    """Strip leaks / backpack / dups and inject the pullups_max menu on bar+rings home."""
    if not bar_rings_menu_active(
        equipment_slugs, location=location, no_equipment=no_equipment
    ):
        return False

    key = normalize_split_role(getattr(day, "split_role", None))
    exercises = list(getattr(day, "exercises", None) or [])
    if not exercises:
        return False

    pu = pullups_max_of(fitness_baseline)
    unspecified = pullups_max_unspecified(fitness_baseline)
    pool = [p for raw in candidates if (p := _candidate_meta(raw)) is not None]
    for eid, meta in list(meta_by_id.items()):
        try:
            eid_i = int(eid)
        except (TypeError, ValueError):
            continue
        if any(p[0] == eid_i for p in pool):
            continue
        pool.append((eid_i, _as_meta_dict(meta)))
    for eid, meta in pool:
        _merge_meta_entry(meta_by_id, eid, meta)

    changed = False
    has_strict = any(
        is_strict_pullup_item(meta_by_id.get(int(ex.exercise_id)) or {})
        for ex in exercises
        if _is_main(ex)
    )
    drop_backpack = deny_backpack_row(
        fitness_baseline, day_has_strict_pullup=has_strict
    )

    kept: list[Any] = []
    for ex in exercises:
        meta = meta_by_id.get(int(ex.exercise_id)) or {}
        if not _is_main(ex):
            kept.append(ex)
            continue
        if drop_backpack and is_backpack_row_name(meta.get("name_vi"), meta.get("name_en")):
            changed = True
            continue
        if key in _PULL_SPLITS and is_pull_leak_item(meta):
            changed = True
            continue
        if (
            key in _PULL_SPLITS
            and not unspecified
            and pu is not None
            and pu < REQUIRE_PULLUP_MIN
        ):
            if is_strict_pullup_item(meta):
                changed = True
                continue
        kept.append(ex)

    before_n = sum(1 for ex in exercises if _is_main(ex))
    kept = dedupe_session_exercises(kept)
    if len(kept) != len(exercises):
        changed = True

    used = {int(ex.exercise_id) for ex in kept}
    template = next((ex for ex in kept if _is_main(ex)), exercises[0])

    def _inject(match: Matcher, *, replace_regression: bool = False) -> bool:
        nonlocal changed
        hit = _find_in_pool(pool, match, used)
        if hit is None:
            return False
        eid, meta = hit
        used.add(eid)
        _merge_meta_entry(meta_by_id, eid, meta)
        if replace_regression:
            for i, ex in enumerate(kept):
                if not _is_main(ex):
                    continue
                old = meta_by_id.get(int(ex.exercise_id)) or {}
                if is_pull_regression_item(old):
                    kept[i] = _copy_ex(ex, eid)
                    changed = True
                    return True
        kept.append(_copy_ex(template, eid))
        changed = True
        return True

    if key in _PULL_FAMILY_SPLITS:
        present = [
            meta_by_id.get(int(ex.exercise_id)) or {} for ex in kept if _is_main(ex)
        ]
        for match in required_pull_matchers(pu, unspecified=unspecified):
            if any(match(m) for m in present):
                continue
            if _inject(match, replace_regression=True):
                present = [
                    meta_by_id.get(int(ex.exercise_id)) or {}
                    for ex in kept
                    if _is_main(ex)
                ]

        need_strict = unspecified or (pu is not None and pu >= REQUIRE_PULLUP_MIN)
        if need_strict and not any(is_strict_pullup_item(m) for m in present):
            _inject(is_ring_pullup_item, replace_regression=True) or _inject(
                is_strict_pullup_item, replace_regression=True
            )

    main_n = sum(1 for ex in kept if _is_main(ex))
    target = before_n
    if key in _FILL_SPLITS:
        target = max(target, 4 if key == "pull" else 3)
    if key in _FILL_SPLITS and main_n < target:
        for match in _fill_matchers():
            while main_n < target and _inject(match):
                main_n += 1
            if main_n >= target:
                break

    day.exercises = kept
    return changed


def repair_plan_day_legs_menu(
    day: Any,
    *,
    candidates: list[Any],
    meta_by_id: dict[int, dict[str, Any]],
    fitness_baseline: dict[str, Any] | None,
    equipment_slugs: Any = None,
    location: str | None = "home",
    no_equipment: bool = False,
    experience_level: int | None = None,
) -> bool:
    """Inject Ring Hamstring Curl + Bulgarian Ring Squat when squat test is strong."""
    if not must_include_ring_legs(
        fitness_baseline,
        equipment_slugs,
        experience_level=experience_level,
        location=location,
        no_equipment=no_equipment,
    ):
        return False
    key = normalize_split_role(getattr(day, "split_role", None))
    if key not in _LEG_SPLITS:
        return False
    exercises = list(getattr(day, "exercises", None) or [])
    if not exercises:
        return False

    pool = [p for raw in candidates if (p := _candidate_meta(raw)) is not None]
    for eid, meta in list(meta_by_id.items()):
        try:
            eid_i = int(eid)
        except (TypeError, ValueError):
            continue
        if any(p[0] == eid_i for p in pool):
            continue
        pool.append((eid_i, _as_meta_dict(meta)))
    for eid, meta in pool:
        _merge_meta_entry(meta_by_id, eid, meta)

    kept = dedupe_session_exercises(list(exercises))
    used = {int(ex.exercise_id) for ex in kept}
    template = next((ex for ex in kept if _is_main(ex)), exercises[0])
    changed = len(kept) != len(exercises)
    present = [meta_by_id.get(int(ex.exercise_id)) or {} for ex in kept if _is_main(ex)]

    def _inject(match: Matcher) -> bool:
        nonlocal changed
        hit = _find_in_pool(pool, match, used)
        if hit is None:
            return False
        eid, meta = hit
        used.add(eid)
        _merge_meta_entry(meta_by_id, eid, meta)
        kept.append(_copy_ex(template, eid))
        changed = True
        return True

    for match in (is_bulgarian_ring_squat_item, is_ring_hamstring_curl_item):
        if any(match(m) for m in present):
            continue
        if _inject(match):
            present.append(meta_by_id.get(int(kept[-1].exercise_id)) or {})

    day.exercises = kept
    return changed


def repair_plan_day_ring_dip(
    day: Any,
    *,
    candidates: list[Any],
    meta_by_id: dict[int, dict[str, Any]],
    equipment_slugs: Any = None,
    location: str | None = "home",
    no_equipment: bool = False,
) -> bool:
    """Replace Assisted Ring Dip with Ring Dip on Push/Upper/FB when rings are selected."""
    if not bar_rings_menu_active(
        equipment_slugs, location=location, no_equipment=no_equipment
    ):
        return False
    if "gymnastic-rings" not in expand_equipment_aliases(equipment_slugs):
        return False
    key = normalize_split_role(getattr(day, "split_role", None))
    if key not in _PUSH_SPLITS:
        return False
    exercises = list(getattr(day, "exercises", None) or [])
    if not exercises:
        return False

    pool = [p for raw in candidates if (p := _candidate_meta(raw)) is not None]
    for eid, meta in list(meta_by_id.items()):
        try:
            eid_i = int(eid)
        except (TypeError, ValueError):
            continue
        if any(p[0] == eid_i for p in pool):
            continue
        pool.append((eid_i, _as_meta_dict(meta)))
    for eid, meta in pool:
        _merge_meta_entry(meta_by_id, eid, meta)

    kept: list[Any] = []
    changed = False
    for ex in exercises:
        meta = meta_by_id.get(int(ex.exercise_id)) or {}
        if _is_main(ex) and is_assisted_ring_dip_item(meta):
            changed = True
            continue
        kept.append(ex)
    kept = dedupe_session_exercises(kept)
    used = {int(ex.exercise_id) for ex in kept}
    template = next((ex for ex in kept if _is_main(ex)), exercises[0])
    present = [meta_by_id.get(int(ex.exercise_id)) or {} for ex in kept if _is_main(ex)]
    if not any(is_ring_dip_item(m) for m in present):
        hit = _find_in_pool(pool, is_ring_dip_item, used)
        if hit is not None:
            eid, meta = hit
            meta_by_id.setdefault(eid, {}).update(
                {k: v for k, v in meta.items() if v not in (None, "")}
            )
            kept.append(_copy_ex(template, eid))
            changed = True
    day.exercises = kept
    return changed
