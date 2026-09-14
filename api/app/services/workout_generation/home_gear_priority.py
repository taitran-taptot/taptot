"""Home with equipment: gear-first pools, bodyweight only when gear would repeat.

Tier 0 = uses the user's selected gear, tier 1 = bodyweight (no linked equipment),
tier 2 = other gear (already filtered upstream; kept for safety).

Two deterministic stages:

1. ``tier_slot_pool`` — before the OpenAI pick, each slot pool keeps only gear rows when
   there are at least ``need`` of them; otherwise bodyweight rows top up the difference.
2. ``enforce_home_gear_variety`` — after assembly, an exercise repeated more than
   ``MAX_SAME_EXERCISE_PER_WEEK`` (or a lift stem more than ``MAX_SAME_STEM_PER_WEEK``)
   is swapped for an unused gear row first, a bodyweight row only when no gear is left.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Iterable

from app.services.workout_generation.shortlist import (
    expand_equipment_aliases,
    is_unassisted_bar_skill,
)
from app.services.workout_generation.split_map import is_denied_for_split

HOME_GEAR_MIN_POOL = 3
MAX_SAME_EXERCISE_PER_WEEK = 2
MAX_SAME_STEM_PER_WEEK = 3
TIER_GEAR = 0
TIER_BODYWEIGHT = 1
TIER_OTHER = 2

_STRENGTH_ROLES = frozenset({"compound", "isolation", "resistance"})
_NON_STRENGTH_ROLES = frozenset({"cardio", "conditioning", "mobility", "warmup", "cooldown"})


def home_gear_active(
    location: str | None,
    *,
    no_equipment: bool,
    equipment_slugs: Iterable[str] | None,
) -> bool:
    """True only for home + at least one selected implement."""
    loc = (location or "").strip().lower()
    if loc != "home" or no_equipment:
        return False
    return any(str(s or "").strip() for s in (equipment_slugs or ()))


def user_gear_set(equipment_slugs: Iterable[str] | None) -> set[str]:
    return expand_equipment_aliases(equipment_slugs)


def _slugs_of(obj: Any) -> set[str]:
    if isinstance(obj, dict):
        raw = obj.get("equipment_slugs") or obj.get("eq") or ()
    else:
        raw = getattr(obj, "equipment_slugs", None) or ()
    if isinstance(raw, str):
        raw = (raw,)
    return {str(s or "").strip().lower() for s in raw if str(s or "").strip()}


def gear_tier(equipment_slugs: Iterable[str] | None, user_expanded: set[str]) -> int:
    linked = {str(s or "").strip().lower() for s in (equipment_slugs or ()) if str(s or "").strip()}
    if not linked:
        return TIER_BODYWEIGHT
    if expand_equipment_aliases(linked) & user_expanded:
        return TIER_GEAR
    return TIER_OTHER


def item_tier(obj: Any, user_expanded: set[str]) -> int:
    return gear_tier(_slugs_of(obj), user_expanded)


def min_gear_pool(role_count: int, variants: int = 1) -> int:
    """Distinct gear options a slot needs so the week (and challenge phases) can vary.

    role_count: sessions in the week sharing this split role (FB×3 → 3, PPL → 1).
    variants: 1 normal plan; 3 for the 100-day challenge (three phases, each avoiding
    the previous picks).
    """
    rc = max(1, int(role_count or 1))
    v = max(1, int(variants or 1))
    return max(HOME_GEAR_MIN_POOL, rc * v + 1)


def tier_slot_pool(
    pool: list[dict[str, Any]],
    *,
    user_expanded: set[str],
    need: int,
    bw_key: Callable[[dict[str, Any]], Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Gear rows first; bodyweight rows only top up to ``need``.

    Returns (rows, meta) with meta = {gear_n, bw_n, bw_kept, need}. Rows keep their
    incoming relative order; ``bw_key`` (lower is better) reorders the bodyweight
    candidates before the cut. Tier-0 rows get an internal ``_gear`` flag so the
    deterministic slot filler can prefer them.
    """
    gear: list[dict[str, Any]] = []
    bw: list[dict[str, Any]] = []
    for row in pool or []:
        tier = item_tier(row, user_expanded)
        if tier == TIER_GEAR:
            r = dict(row)
            r["_gear"] = 1
            gear.append(r)
        elif tier == TIER_BODYWEIGHT:
            bw.append(dict(row))
    need_n = max(1, int(need or 1))
    if bw_key is not None and bw:
        bw = sorted(enumerate(bw), key=lambda p: (bw_key(p[1]), p[0]))
        bw = [r for _, r in bw]
    if len(gear) >= need_n:
        kept_bw: list[dict[str, Any]] = []
    else:
        kept_bw = bw[: need_n - len(gear)]
    meta = {
        "gear_n": len(gear),
        "bw_n": len(bw),
        "bw_kept": len(kept_bw),
        "need": need_n,
    }
    return gear + kept_bw, meta


def sort_gear_first(items: list[Any], user_expanded: set[str]) -> list[Any]:
    """Stable: gear rows before bodyweight, otherwise keep the incoming order."""
    return sorted(items, key=lambda it: item_tier(it, user_expanded))


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
        "movement_pattern": getattr(raw, "movement_pattern", None),
        "muscle_slug": getattr(raw, "muscle_slug", None) or getattr(raw, "muscle", None),
        "equipment_slugs": getattr(raw, "equipment_slugs", None),
    }


def _row(raw: Any) -> dict[str, Any] | None:
    if isinstance(raw, dict):
        try:
            eid = int(raw.get("id") or raw.get("exercise_id"))
        except (TypeError, ValueError):
            return None
        d = dict(raw)
        d["id"] = eid
        return d
    try:
        eid = int(getattr(raw, "id", None) or getattr(raw, "exercise_id"))
    except (TypeError, ValueError, AttributeError):
        return None
    return {
        "id": eid,
        "name_vi": getattr(raw, "name_vi", "") or "",
        "name_en": getattr(raw, "name_en", None),
        "movement_role": getattr(raw, "movement_role", None),
        "movement_pattern": getattr(raw, "movement_pattern", None),
        "muscle_slug": getattr(raw, "muscle_slug", None) or getattr(raw, "muscle", None),
        "equipment_slugs": sorted(getattr(raw, "equipment_slugs", None) or ()),
    }


def _pattern(d: dict[str, Any]) -> str:
    return str(d.get("movement_pattern") or d.get("pattern") or "").strip().lower()


def _muscle(d: dict[str, Any]) -> str:
    return str(d.get("muscle_slug") or d.get("muscle") or "").strip().lower()


def _role(d: dict[str, Any]) -> str:
    return str(d.get("movement_role") or "").strip().lower()


def _is_strength_main(ex: Any, meta: dict[str, Any]) -> bool:
    if str(getattr(ex, "section", None) or "main") != "main":
        return False
    role = _role(meta)
    if role in _NON_STRENGTH_ROLES:
        return False
    return role in _STRENGTH_ROLES or not role


def _stem(meta: dict[str, Any]) -> str | None:
    from app.services.workout_generation.weekly_volume import lift_stem

    return lift_stem(str(meta.get("name_vi") or ""), str(meta.get("name_en") or "") or None)


def gear_share(
    plan_days: list[Any],
    *,
    meta_by_id: dict[int, Any],
    user_expanded: set[str],
) -> float | None:
    """Share of main strength exercises that use the selected gear (None if unknown)."""
    gear = 0
    bw = 0
    for day in plan_days:
        for ex in getattr(day, "exercises", None) or []:
            meta = _meta(meta_by_id, int(ex.exercise_id))
            if not meta or not _is_strength_main(ex, meta):
                continue
            if "equipment_slugs" not in meta:
                continue
            tier = gear_tier(meta.get("equipment_slugs"), user_expanded)
            if tier == TIER_GEAR:
                gear += 1
            elif tier == TIER_BODYWEIGHT:
                bw += 1
    total = gear + bw
    if not total:
        return None
    return round(gear / total, 3)


def enforce_home_gear_variety(
    plan_days: list[Any],
    *,
    pools_by_day: dict[int, list[Any]],
    meta_by_id: dict[int, Any],
    user_slugs: Iterable[str] | None,
    experience_level: int = 2,
    location: str | None = "home",
    no_equipment: bool = False,
    max_same_exercise: int = MAX_SAME_EXERCISE_PER_WEEK,
    max_same_stem: int = MAX_SAME_STEM_PER_WEEK,
) -> dict[str, Any]:
    """Cap week-level repeats on main strength lifts; swap gear first, bodyweight last.

    Mutates ``plan_days`` / ``meta_by_id`` in place. Returns an insight dict:
    {replaced: [...], unchanged_no_alternative: [...], gear_share: float|None}.
    """
    insight: dict[str, Any] = {
        "replaced": [],
        "unchanged_no_alternative": [],
        "gear_share": None,
    }
    if not home_gear_active(location, no_equipment=no_equipment, equipment_slugs=user_slugs):
        return insight
    user = user_gear_set(user_slugs)

    used_ids: set[int] = set()
    id_count: Counter[int] = Counter()
    stem_count: Counter[str] = Counter()
    for day in plan_days:
        for ex in getattr(day, "exercises", None) or []:
            eid = int(ex.exercise_id)
            used_ids.add(eid)
            meta = _meta(meta_by_id, eid)
            if not _is_strength_main(ex, meta):
                continue
            id_count[eid] += 1
            stem = _stem(meta)
            if stem:
                stem_count[stem] += 1

    seen_ids: Counter[int] = Counter()
    seen_stems: Counter[str] = Counter()
    level = int(experience_level or 2)

    for day in plan_days:
        day_number = int(getattr(day, "day_number", 0) or 0)
        pool_rows = [
            r
            for r in (
                _row(x) for x in (pools_by_day.get(day_number) or pools_by_day.get(day_number - 1) or [])
            )
            if r is not None
        ]
        day_ids = {int(ex.exercise_id) for ex in getattr(day, "exercises", None) or []}
        for ex in getattr(day, "exercises", None) or []:
            eid = int(ex.exercise_id)
            meta = _meta(meta_by_id, eid)
            if not _is_strength_main(ex, meta):
                continue
            stem = _stem(meta)
            over_id = seen_ids[eid] >= max(1, int(max_same_exercise))
            over_stem = bool(stem) and seen_stems[stem] >= max(1, int(max_same_stem))
            if not over_id and not over_stem:
                seen_ids[eid] += 1
                if stem:
                    seen_stems[stem] += 1
                continue
            reason = "repeat_id" if over_id else "repeat_stem"
            cand = _pick_replacement(
                pool_rows,
                meta=meta,
                split_role=getattr(day, "split_role", None),
                used_ids=used_ids | day_ids,
                stem_count=seen_stems,
                max_same_stem=max_same_stem,
                user_expanded=user,
                level=level,
            )
            if cand is None:
                insight["unchanged_no_alternative"].append(
                    {"day_number": day_number, "exercise_id": eid, "reason": reason}
                )
                seen_ids[eid] += 1
                if stem:
                    seen_stems[stem] += 1
                continue
            new_id = int(cand["id"])
            ex.exercise_id = new_id
            used_ids.add(new_id)
            day_ids.add(new_id)
            m = meta_by_id.setdefault(new_id, {})
            if isinstance(m, dict):
                for k in ("name_vi", "name_en", "movement_role", "movement_pattern", "muscle_slug"):
                    if cand.get(k) is not None:
                        m.setdefault(k, cand.get(k))
                m.setdefault("equipment_slugs", sorted(_slugs_of(cand)))
            tier = item_tier(cand, user)
            seen_ids[new_id] += 1
            new_stem = _stem(cand)
            if new_stem:
                seen_stems[new_stem] += 1
            insight["replaced"].append(
                {
                    "day_number": day_number,
                    "from": eid,
                    "to": new_id,
                    "reason": reason,
                    "bw": tier == TIER_BODYWEIGHT,
                }
            )

    insight["gear_share"] = gear_share(plan_days, meta_by_id=meta_by_id, user_expanded=user)
    return insight


def _pick_replacement(
    pool_rows: list[dict[str, Any]],
    *,
    meta: dict[str, Any],
    split_role: str | None,
    used_ids: set[int],
    stem_count: Counter,
    max_same_stem: int,
    user_expanded: set[str],
    level: int,
) -> dict[str, Any] | None:
    want_pattern = _pattern(meta)
    want_muscle = _muscle(meta)
    # (tier, strict muscle) passes: gear first, bodyweight only when no gear is left.
    passes = (
        (TIER_GEAR, True),
        (TIER_GEAR, False),
        (TIER_BODYWEIGHT, True),
        (TIER_BODYWEIGHT, False),
    )
    for tier, strict_muscle in passes:
        for row in pool_rows:
            eid = int(row["id"])
            if eid in used_ids:
                continue
            if item_tier(row, user_expanded) != tier:
                continue
            role = _role(row)
            if role and role not in _STRENGTH_ROLES:
                continue
            if want_pattern and _pattern(row) != want_pattern:
                continue
            if strict_muscle and want_muscle and _muscle(row) != want_muscle:
                continue
            if is_denied_for_split(split_role, pattern=_pattern(row), muscle_slug=_muscle(row)):
                continue
            if level <= 1 and is_unassisted_bar_skill(
                str(row.get("name_vi") or "") or None, str(row.get("name_en") or "") or None
            ):
                continue
            stem = _stem(row)
            if stem and stem_count[stem] >= max(1, int(max_same_stem)):
                continue
            return row
    return None
