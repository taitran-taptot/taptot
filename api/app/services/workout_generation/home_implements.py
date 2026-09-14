"""Home-with-equipment implement coverage: mix dumbbells, bands, bars — not DB-only."""

from __future__ import annotations

from typing import Any, Iterable

from app.schemas.plans import PlanDayIn
from app.services.workout_generation.split_map import (
    is_denied_for_split,
    normalize_split_role,
)

STRENGTH_IMPLEMENTS = frozenset(
    {
        "dumbbell",
        "resistance-band-1",
        "resistance-band-2",
        "pull-up-bar",
        "parallel-bars",
        "gymnastic-rings",
    }
)
CONDITIONING_IMPLEMENTS = frozenset({"jump-rope"})
_JUMP_ROPE_NEEDLES = (
    "jump rope",
    "jump-rope",
    "jumprope",
    "nhảy dây",
    "nhay day",
    "dây nhảy",
    "day nhay",
    "skipping rope",
)
_BAND_FAMILY = frozenset({"resistance-band", "resistance-band-1", "resistance-band-2"})
_BAND1_NEEDLES = (
    "loop",
    "mini",
    "lateral",
    "monster walk",
    "clamshell",
    "đá mông",
    "da mong",
    "kickback",
    "glute bridge",
    "cầu mông",
    "squat",
    "rdl",
    "romanian",
    "deadlift dây",
)
_BAND2_NEEDLES = (
    "tube",
    "handle",
    "row",
    "chèo",
    "cheo",
    "pulldown",
    "kéo xô",
    "keo xo",
    "chest press",
    "đẩy ngực",
    "face pull",
    "overhead press",
    "đẩy vai",
    "front raise",
    "nâng tay trước",
    "nang tay truoc",
)
_PROTECTED_ROLES = frozenset({"compound", "primary", "main"})


def _blob(name_vi: str | None, name_en: str | None) -> str:
    return f"{name_vi or ''} {name_en or ''}".strip().lower()


def classify_home_implement(
    *,
    name_vi: str | None = None,
    name_en: str | None = None,
    equipment_slugs: Iterable[str] | None = None,
) -> str | None:
    """Map an exercise to a public home implement (band-1 vs band-2 from name)."""
    linked = {str(s or "").strip().lower() for s in (equipment_slugs or ()) if str(s or "").strip()}
    blob = _blob(name_vi, name_en)
    if "jump-rope" in linked or any(k in blob for k in _JUMP_ROPE_NEEDLES):
        return "jump-rope"
    # Rings before bare pull-up name match — "Hít xà vòng treo" is rings, not bar.
    if (
        "gymnastic-rings" in linked
        or any(
            k in blob
            for k in (
                "gymnastic ring",
                "gymnastic rings",
                "ring dip",
                "ring row",
                "ring push",
                "ring pull",
                "ring chin",
                "ring face",
                "face pull",
                "rear delt",
                "ring hold",
                "ring fly",
                "vòng treo",
                "vong treo",
            )
        )
        or "rings" in blob
    ):
        return "gymnastic-rings"
    if "pull-up-bar" in linked or any(
        k in blob for k in ("hít xà", "hit xa", "pull-up", "pullup", "chin-up")
    ):
        return "pull-up-bar"
    if "parallel-bars" in linked or any(k in blob for k in ("xà kép", "xa kep", "dip")):
        return "parallel-bars"
    if "dumbbell" in linked or "tạ đơn" in blob or "ta don" in blob or "dumbbell" in blob:
        return "dumbbell"
    is_band = bool(linked & _BAND_FAMILY) or "band" in blob or "dây" in blob
    if not is_band:
        return None
    # Arm curls are pull work — do not count as band-2 back coverage.
    if any(
        k in blob
        for k in ("cuốn tay", "cuon tay", "bicep", "band curl", "hammer curl")
    ) and not any(k in blob for k in ("đùi", "dui", "leg curl", "hamstring")):
        return None
    if any(k in blob for k in _BAND1_NEEDLES):
        return "resistance-band-1"
    if any(k in blob for k in _BAND2_NEEDLES):
        return "resistance-band-2"
    if "resistance-band-1" in linked and "resistance-band-2" not in linked:
        return "resistance-band-1"
    if "resistance-band-2" in linked and "resistance-band-1" not in linked:
        return "resistance-band-2"
    return "resistance-band-2"


def _meta(meta_by_id: dict[int, Any], eid: int) -> dict[str, Any]:
    raw = meta_by_id.get(int(eid))
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    return {
        "name_vi": getattr(raw, "name_vi", "") or "",
        "name_en": getattr(raw, "name_en", None),
        "movement_role": getattr(raw, "movement_role", None),
        "muscle_slug": getattr(raw, "muscle_slug", None) or getattr(raw, "muscle", None),
        "equipment_slugs": getattr(raw, "equipment_slugs", None),
    }


def _item_implement(meta: dict[str, Any]) -> str | None:
    slugs = meta.get("equipment_slugs") or meta.get("equipment") or ()
    if isinstance(slugs, str):
        slugs = (slugs,)
    return classify_home_implement(
        name_vi=str(meta.get("name_vi") or "") or None,
        name_en=str(meta.get("name_en") or "") or None,
        equipment_slugs=slugs,
    )


def _is_protected_main(meta: dict[str, Any], *, index_among_mains: int) -> bool:
    if index_among_mains == 0:
        return True
    pattern = str(meta.get("movement_pattern") or meta.get("pattern") or "").strip().lower()
    if pattern in {"h_push", "squat", "hinge", "v_push"}:
        return True
    role = str(meta.get("movement_role") or "").strip().lower()
    return role in _PROTECTED_ROLES


def _preferred_implement_for_day(split_role: str | None, wanted: set[str]) -> str | None:
    key = normalize_split_role(split_role)
    if key in {"pull", "upper"} and "gymnastic-rings" in wanted:
        return "gymnastic-rings"
    if key in {"pull", "upper"} and "resistance-band-2" in wanted:
        return "resistance-band-2"
    if key in {"legs", "lower"} and "resistance-band-1" in wanted:
        return "resistance-band-1"
    return None


def _pool_items(pool: Iterable[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in pool or ():
        if isinstance(raw, dict):
            try:
                eid = int(raw.get("id") or raw.get("exercise_id"))
            except (TypeError, ValueError):
                continue
            row = dict(raw)
            row["id"] = eid
            out.append(row)
            continue
        try:
            eid = int(getattr(raw, "id", None) or getattr(raw, "exercise_id"))
        except (TypeError, ValueError, AttributeError):
            continue
        out.append(
            {
                "id": eid,
                "name_vi": getattr(raw, "name_vi", "") or "",
                "name_en": getattr(raw, "name_en", None),
                "movement_role": getattr(raw, "movement_role", None),
                "movement_pattern": getattr(raw, "movement_pattern", None),
                "muscle_slug": getattr(raw, "muscle_slug", None)
                or getattr(raw, "muscle", None),
                "equipment_slugs": getattr(raw, "equipment_slugs", None),
            }
        )
    return out


def _swap_iso_for_implement(
    day: PlanDayIn,
    *,
    want: str,
    pool: list[dict[str, Any]],
    meta_by_id: dict[int, Any],
    used_ids: set[int],
    experience_level: int = 2,
) -> bool:
    from app.services.workout_generation.shortlist import is_unassisted_bar_skill

    cand = None
    for row in pool:
        eid = int(row["id"])
        if eid in used_ids:
            continue
        impl = _item_implement(row) or _item_implement(meta_by_id.get(eid) or row)
        if impl != want:
            continue
        if int(experience_level or 2) <= 1 and is_unassisted_bar_skill(
            str(row.get("name_vi") or "") or None,
            str(row.get("name_en") or "") or None,
        ):
            continue
        muscle = str(
            row.get("muscle_slug") or row.get("muscle") or ""
        ).strip().lower()
        if not muscle:
            muscle = str(
                (_meta(meta_by_id, eid) or {}).get("muscle_slug")
                or (_meta(meta_by_id, eid) or {}).get("muscle")
                or ""
            ).strip().lower()
        pattern = str(
            row.get("movement_pattern") or row.get("pattern") or ""
        ).strip().lower()
        if is_denied_for_split(day.split_role, pattern=pattern, muscle_slug=muscle):
            continue
        cand = row
        break
    if cand is None:
        return False
    mains = [i for i, ex in enumerate(day.exercises) if (ex.section or "main") == "main"]
    if len(mains) < 2:
        return False
    main_n = 0
    swap_i: int | None = None
    for i, ex in enumerate(day.exercises):
        if (ex.section or "main") != "main":
            continue
        meta = _meta(meta_by_id, int(ex.exercise_id))
        if not _is_protected_main(meta, index_among_mains=main_n):
            swap_i = i
        main_n += 1
    if swap_i is None:
        return False
    new_id = int(cand["id"])
    day.exercises[swap_i].exercise_id = new_id
    if new_id not in meta_by_id:
        meta_by_id[new_id] = cand
    return True


def _is_cardio_ex(ex: Any, meta_by_id: dict[int, Any]) -> bool:
    if (getattr(ex, "section", None) or "") == "cardio":
        return True
    role = str(
        (_meta(meta_by_id, int(ex.exercise_id)).get("movement_role") or "")
    ).strip().lower()
    return role in {"cardio", "conditioning"}


def _swap_conditioning_for_implement(
    day: PlanDayIn,
    *,
    want: str,
    pool: list[dict[str, Any]],
    meta_by_id: dict[int, Any],
    used_ids: set[int],
) -> bool:
    cand = None
    for row in pool:
        eid = int(row["id"])
        if eid in used_ids:
            continue
        impl = _item_implement(row) or _item_implement(meta_by_id.get(eid) or row)
        if impl != want:
            continue
        cand = row
        break
    if cand is None:
        return False
    swap_i: int | None = None
    for i, ex in enumerate(day.exercises):
        if _is_cardio_ex(ex, meta_by_id):
            swap_i = i
            break
    if swap_i is None:
        return False
    new_id = int(cand["id"])
    day.exercises[swap_i].exercise_id = new_id
    if new_id not in meta_by_id:
        meta_by_id[new_id] = cand
    return True


def apply_home_implement_coverage(
    plan_days: list[PlanDayIn],
    *,
    user_slugs: Iterable[str] | None,
    meta_by_id: dict[int, Any],
    pools_by_day: dict[int, list[Any]] | None = None,
    location: str | None = None,
    no_equipment: bool = False,
    experience_level: int = 2,
) -> list[PlanDayIn]:
    """Swap isolations/conditioning so selected home implements appear."""
    loc = (location or "").strip().lower()
    if loc != "home" or no_equipment:
        return plan_days
    raw = {str(s).strip().lower() for s in (user_slugs or ()) if str(s).strip()}
    if "resistance-band" in raw:
        raw.update({"resistance-band-1", "resistance-band-2"})
    wanted = {s for s in raw if s in STRENGTH_IMPLEMENTS}
    wanted_cond = {s for s in raw if s in CONDITIONING_IMPLEMENTS}
    if not wanted and not wanted_cond:
        return plan_days
    pools = pools_by_day or {}
    used_ids: set[int] = set()
    seen_impl: set[str] = set()

    for day in plan_days:
        for ex in day.exercises:
            used_ids.add(int(ex.exercise_id))
            impl = _item_implement(_meta(meta_by_id, int(ex.exercise_id)))
            if impl:
                seen_impl.add(impl)

    for day in plan_days:
        prefer = _preferred_implement_for_day(day.split_role, wanted)
        if not prefer:
            continue
        day_impls = {
            _item_implement(_meta(meta_by_id, int(ex.exercise_id)))
            for ex in day.exercises
            if (ex.section or "main") == "main"
        }
        if prefer in day_impls:
            continue
        key = int(getattr(day, "day_number", 0) or 0)
        pool = _pool_items(pools.get(key) or pools.get(key - 1) or [])
        if _swap_iso_for_implement(
            day,
            want=prefer,
            pool=pool,
            meta_by_id=meta_by_id,
            used_ids=used_ids,
            experience_level=experience_level,
        ):
            seen_impl.add(prefer)
            used_ids = {int(ex.exercise_id) for d in plan_days for ex in d.exercises}

    missing = [s for s in wanted if s not in seen_impl]
    for impl in missing:
        for day in plan_days:
            key = int(getattr(day, "day_number", 0) or 0)
            pool = _pool_items(pools.get(key) or pools.get(key - 1) or [])
            if _swap_iso_for_implement(
                day,
                want=impl,
                pool=pool,
                meta_by_id=meta_by_id,
                used_ids=used_ids,
                experience_level=experience_level,
            ):
                seen_impl.add(impl)
                used_ids = {int(ex.exercise_id) for d in plan_days for ex in d.exercises}
                break

    missing_cond = [s for s in wanted_cond if s not in seen_impl]
    for impl in missing_cond:
        for day in plan_days:
            key = int(getattr(day, "day_number", 0) or 0)
            pool = _pool_items(pools.get(key) or pools.get(key - 1) or [])
            if _swap_conditioning_for_implement(
                day,
                want=impl,
                pool=pool,
                meta_by_id=meta_by_id,
                used_ids=used_ids,
            ):
                seen_impl.add(impl)
                used_ids = {int(ex.exercise_id) for d in plan_days for ex in d.exercises}
                break
    return plan_days
