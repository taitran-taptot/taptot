"""Rule-based exercise picks within shortlists (no LLM)."""

from __future__ import annotations

import copy
from typing import Any

PICK_FAIL_VI = (
    "Hệ thống đang tắc nghẽn vì nhiều người đang tạo lịch cùng lúc. "
    "Vui lòng đợi khoảng 1 phút rồi thử lại."
)

_STRENGTH_KEYS = frozenset({"compound", "accessory", "resistance", "conditioning"})
_MOBILITY_KEYS = frozenset({"general_warmup", "dynamic_mobility", "cooldown"})
ISO_SWAP_KEYS = frozenset({"accessory", "resistance", "conditioning", "core", "cardio"})
SLOT_PICKS_KEY = "_slot_picks"
DOSE_PICKS_KEY = "_dose_by_exercise"


def _copy_picks(picks: dict[str, Any] | None) -> dict[str, Any]:
    return copy.deepcopy(picks or {})

class PickError(Exception):
    """Hard-fail when a required shortlist cannot fill the session."""

    def __init__(self, message: str = PICK_FAIL_VI) -> None:
        self.detail = message
        self.message = message
        super().__init__(message)

def _item_eid(item: object) -> int:
    return int(item["id"]) if isinstance(item, dict) else int(item.id)

def _item_muscle(item: object) -> str | None:
    if isinstance(item, dict):
        raw = item.get("muscle") or item.get("muscle_slug")
    else:
        raw = getattr(item, "muscle_slug", None) or getattr(item, "muscle", None)
    slug = str(raw or "").strip().lower()
    return slug or None

def _item_name(item: object) -> str | None:
    if isinstance(item, dict):
        raw = item.get("name_vi")
    else:
        raw = getattr(item, "name_vi", None)
    name = str(raw or "").strip()
    return name or None

def _item_name_en(item: object) -> str | None:
    if isinstance(item, dict):
        raw = item.get("name_en")
    else:
        raw = getattr(item, "name_en", None)
    name = str(raw or "").strip()
    return name or None

def _trained_slugs_from_picks(day_blocks: list[dict], picks: dict[str, list[int]]) -> frozenset[str]:
    by_id: dict[int, str] = {}
    for block in day_blocks:
        key = str(block.get("block_key") or "")
        if key in _MOBILITY_KEYS:
            continue
        for x in block.get("shortlist") or []:
            slug = _item_muscle(x)
            if slug:
                by_id[_item_eid(x)] = slug
    slugs: set[str] = set()
    for key, ids in picks.items():
        if str(key).startswith("_") or key in _MOBILITY_KEYS:
            continue
        for eid in ids or []:
            slug = by_id.get(int(eid))
            if slug:
                slugs.add(slug)
    return frozenset(slugs)

def deterministic_picks(
    day_blocks: list[dict],
    *,
    split_role: str | None = None,
    focus_slugs: frozenset[str] | None = None,
    used_ids: set[int] | None = None,
    avoid_compound_patterns: frozenset[str] | None = None,
    day_index: int = 0,
    avoid_ids: set[int] | frozenset[int] | None = None,
    avoid_stems: set[str] | frozenset[str] | None = None,
    prefer_knee: bool = False,
    session_minutes: int | None = None,
    experience_level: int = 2,
    focus_areas: list[str] | None = None,
) -> dict[str, list[int]]:
    """Slot-template / diversified deterministic picks, then day coverage repair.

    Used by challenge generation and unit tests.
    """
    from app.services.workout_generation.coverage import (
        diversified_pick,
        family_of,
        repair_day_coverage,
    )
    from app.services.workout_generation.muscle_quotas import repair_muscle_quotas
    from app.services.workout_generation.session_templates import (
        fill_strength_slots,
        slots_for_session,
        uses_session_templates,
    )
    from app.services.workout_generation.split_map import mobility_match_rank

    role = split_role
    blocks_by_key = {str(b.get("block_key")): b for b in day_blocks}

    def _item_eid(item: object) -> int:
        return int(item["id"]) if isinstance(item, dict) else int(item.id)

    def _pick_mobility(
        shortlist: list,
        n: int,
        used: set[int],
        *,
        cooldown: bool,
        trained_slugs: frozenset[str] | None = None,
    ) -> list[int]:
        ranked = sorted(
            shortlist,
            key=lambda x: (
                mobility_match_rank(
                    muscle_slug=_item_muscle(x),
                    name_vi=_item_name(x),
                    split_role=role,
                    cooldown=cooldown,
                    trained_slugs=trained_slugs,
                    gear_match=_cooldown_gear_match(x, shortlist) if cooldown else None,
                ),
                _item_eid(x),
            ),
        )
        ids: list[int] = []
        for x in ranked:
            eid = _item_eid(x)
            if eid in used:
                continue
            ids.append(eid)
            used.add(eid)
            if len(ids) >= n:
                break
        return ids

    primary_key = "resistance" if "resistance" in blocks_by_key else "compound"
    secondary_key = "conditioning" if "conditioning" in blocks_by_key else "accessory"
    primary_block = blocks_by_key.get(primary_key) or {}
    secondary_block = blocks_by_key.get(secondary_key) or {}
    location = "home" if primary_key == "resistance" else "gym"

    if uses_session_templates(role):
        primary_n = int(primary_block.get("count_max") or 0) if primary_block.get("pick") else 0
        secondary_n = int(secondary_block.get("count_max") or 0) if secondary_block.get("pick") else 0
        if location == "home":
            if primary_n <= 1:
                compound_n, accessory_n = primary_n, 0
            elif primary_n == 2:
                compound_n, accessory_n = 1, 1
            else:
                compound_n, accessory_n = 2, primary_n - 2
        else:
            compound_n = primary_n
            accessory_n = secondary_n if secondary_key == "accessory" else 0
        pool: list = []
        week_skip = set(used_ids or ())
        strength_keys = (primary_key, secondary_key) if location == "gym" else (primary_key,)
        for key in strength_keys:
            b = blocks_by_key.get(key) or {}
            if not b.get("pick"):
                continue
            for x in list(b.get("shortlist") or []):
                if _item_eid(x) in week_skip:
                    continue
                row = dict(x) if isinstance(x, dict) else {
                    "id": int(x.id),
                    "movement_pattern": getattr(x, "movement_pattern", None),
                    "movement_role": getattr(x, "movement_role", None),
                    "muscle": getattr(x, "muscle_slug", None) or getattr(x, "muscle", None),
                    "name_vi": getattr(x, "name_vi", ""),
                }
                row["_block"] = key
                pool.append(row)
        slots = slots_for_session(
            role,
            compound_n=compound_n,
            accessory_n=accessory_n,
            location=location,
            focus_slugs=focus_slugs,
            day_index=day_index,
            allow_bar_moves=location != "home",
            experience_level=experience_level,
            session_minutes=session_minutes,
            focus_areas=focus_areas,
        )
        filled = fill_strength_slots(
            role,
            slots,
            pool,
            used_ids=week_skip,
            avoid_compound_patterns=avoid_compound_patterns,
            focus_slugs=focus_slugs,
            avoid_ids=avoid_ids,
            avoid_stems=avoid_stems,
            prefer_knee=prefer_knee,
        )
        out: dict[str, Any] = {}
        for key, ids in filled.items():
            if str(key).startswith("_"):
                out[key] = ids
            else:
                out[key] = list(ids)
        if primary_key not in out:
            out[primary_key] = []
        if location == "gym" and secondary_key not in out:
            out[secondary_key] = []
        used = set(week_skip)
        for key, ids in out.items():
            if str(key).startswith("_"):
                continue
            used.update(ids)
        trained = _trained_slugs_from_picks(day_blocks, out)
        for block in day_blocks:
            if not block.get("pick"):
                continue
            key = str(block["block_key"])
            if key in out:
                continue
            n = int(block.get("count_max") or 0)
            shortlist = list(block.get("shortlist") or [])
            if n <= 0:
                out[key] = []
                continue
            if block.get("is_optional") and not shortlist:
                out[key] = []
                continue
            cooldown = key == "cooldown"
            warmup = key in {"general_warmup", "dynamic_mobility"}
            if warmup or cooldown:
                out[key] = _pick_mobility(
                    shortlist, n, used, cooldown=cooldown, trained_slugs=trained
                )
            else:
                ids = []
                for x in shortlist:
                    eid = _item_eid(x)
                    if eid in used:
                        continue
                    ids.append(eid)
                    used.add(eid)
                    if len(ids) >= n:
                        break
                out[key] = ids
        out = repair_muscle_quotas(
            day_blocks, out, split_role=role, focus_slugs=focus_slugs
        )
        out = repair_day_coverage(day_blocks, out, split_role=role)
        return fill_mobility_picks(day_blocks, out, split_role=role)

    out = {}
    used_ids = set(used_ids or ())
    covered: set[str] = set()
    for block in day_blocks:
        if not block.get("pick"):
            continue
        key = str(block["block_key"])
        n = int(block.get("count_max") or 0)
        shortlist = list(block.get("shortlist") or [])
        if n <= 0:
            out[key] = []
            continue
        if block.get("is_optional") and not shortlist:
            out[key] = []
            continue
        cooldown = key == "cooldown"
        warmup = key in {"general_warmup", "dynamic_mobility"}
        if warmup or cooldown:
            ids = _pick_mobility(shortlist, n, used_ids, cooldown=cooldown)
        elif key in {"compound", "accessory", "resistance", "conditioning"}:
            ids = diversified_pick(
                shortlist,
                count=n,
                split_role=role,
                used_ids=used_ids,
                block_key=key,
                already_covered=covered,
            )
        else:
            ids = []
            for x in shortlist:
                eid = _item_eid(x)
                if eid in used_ids:
                    continue
                ids.append(eid)
                if len(ids) >= n:
                    break
            if block.get("is_optional") and not ids:
                out[key] = []
                continue
        if block.get("is_optional") and not ids:
            out[key] = []
            continue
        out[key] = ids
        for eid in ids:
            used_ids.add(eid)
        if key not in {"compound", "accessory", "resistance", "conditioning"}:
            continue
        for x in shortlist:
            eid = _item_eid(x)
            if eid not in ids:
                continue
            pat = None
            if isinstance(x, dict):
                pat = x.get("movement_pattern")
            else:
                pat = getattr(x, "movement_pattern", None)
            fam = family_of(str(pat).lower() if pat else None)
            if fam:
                covered.add(fam)
    out = repair_day_coverage(day_blocks, out, split_role=role)
    return fill_mobility_picks(day_blocks, out, split_role=role)

def isolation_ids_from_picks(picks: dict[str, list[int]] | None) -> list[int]:
    """Isolation/accessory/cardio ids from a day's picks (compounds excluded)."""
    out: list[int] = []
    seen: set[int] = set()
    for key, ids in (picks or {}).items():
        if str(key).startswith("_"):
            continue
        if str(key) not in ISO_SWAP_KEYS:
            continue
        for raw in ids or []:
            try:
                eid = int(raw)
            except (TypeError, ValueError):
                continue
            if eid not in seen:
                seen.add(eid)
                out.append(eid)
    return out

def strength_ids_from_picks(picks: dict[str, list[int]] | None) -> list[int]:
    """Compound + isolation ids to avoid repeating across phases."""
    out: list[int] = []
    seen: set[int] = set()
    for key, ids in (picks or {}).items():
        if str(key).startswith("_"):
            continue
        if str(key) not in _STRENGTH_KEYS:
            continue
        for raw in ids or []:
            try:
                eid = int(raw)
            except (TypeError, ValueError):
                continue
            if eid not in seen:
                seen.add(eid)
                out.append(eid)
    return out

def stems_from_picks(
    picks: dict[str, list[int]] | None,
    day_blocks: list[dict] | None = None,
) -> list[str]:
    """Movement-family stems (step-up / lunge / push-up) for prior-phase avoid."""
    from app.services.workout_generation.weekly_volume import lift_stem

    names: dict[int, tuple[str | None, str | None]] = {}
    for block in day_blocks or []:
        for x in block.get("shortlist") or []:
            try:
                eid = _item_eid(x)
            except (TypeError, ValueError, KeyError, AttributeError):
                continue
            names[eid] = (_item_name(x), _item_name_en(x))
    out: list[str] = []
    seen: set[str] = set()
    for eid in strength_ids_from_picks(picks):
        nv, ne = names.get(eid, (None, None))
        stem = lift_stem(nv, ne)
        if stem and stem not in seen:
            seen.add(stem)
            out.append(stem)
    return out

def _avoid_id_set(avoid_ids: set[int] | frozenset[int] | list[int] | None) -> set[int]:
    out: set[int] = set()
    for raw in avoid_ids or ():
        try:
            out.add(int(raw))
        except (TypeError, ValueError):
            continue
    return out

def _avoid_stem_set(avoid_stems: set[str] | frozenset[str] | list[str] | None) -> set[str]:
    return {str(s).strip() for s in (avoid_stems or ()) if str(s).strip()}

def _item_stem(item: object) -> str | None:
    from app.services.workout_generation.weekly_volume import lift_stem

    return lift_stem(_item_name(item), _item_name_en(item))

def _item_is_avoided(
    item: object,
    avoid_ids: set[int],
    avoid_stems: set[str],
) -> bool:
    try:
        eid = _item_eid(item)
    except (TypeError, ValueError, KeyError, AttributeError):
        return False
    if eid in avoid_ids:
        return True
    stem = _item_stem(item)
    return bool(stem and stem in avoid_stems)

def _swap_avoided_picks(
    cleaned: list[int],
    shortlist: list,
    *,
    avoid_ids: set[int],
    avoid_stems: set[str],
    extra_used: set[int],
) -> list[int]:
    """Replace reused ids/stems when the shortlist still has a fresh option."""
    if not avoid_ids and not avoid_stems:
        return cleaned
    by_id = {}
    for x in shortlist:
        try:
            by_id[_item_eid(x)] = x
        except (TypeError, ValueError, KeyError, AttributeError):
            continue
    fresh = [
        _item_eid(x)
        for x in shortlist
        if not _item_is_avoided(x, avoid_ids, avoid_stems)
    ]
    taken = set(extra_used)
    out: list[int] = []
    for eid in cleaned:
        item = by_id.get(eid)
        if item is not None and _item_is_avoided(item, avoid_ids, avoid_stems):
            alt = next((f for f in fresh if f not in taken and f not in out), None)
            if alt is not None:
                out.append(alt)
                taken.add(alt)
                continue
        out.append(eid)
        taken.add(eid)
    return out

def _replace_same_day_duplicates(
    cleaned: list[int],
    shortlist: list,
    *,
    used: set[int],
    count_max: int,
) -> list[int]:
    """Swap ids already used in this session; reuse only when the shortlist is exhausted."""
    allowed = _shortlist_ids(shortlist)
    fresh = [
        eid
        for x in shortlist
        for eid in (_item_eid(x),)
        if eid in allowed and eid not in used
    ]
    out: list[int] = []
    taken = set(used)
    for eid in cleaned:
        if eid in taken:
            alt = next((f for f in fresh if f not in taken and f not in out), None)
            if alt is not None:
                out.append(alt)
                taken.add(alt)
                continue
        out.append(eid)
        taken.add(eid)
    while len(out) < count_max:
        alt = next((f for f in fresh if f not in out), None)
        if alt is None:
            break
        out.append(alt)
    return out[: max(count_max, 0)] if count_max else out

def _fold_slot_picks(
    prompt_slots: list[dict[str, Any]],
    slot_picks: dict[str, list[int]],
) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for spec in prompt_slots:
        block = str(spec.get("block_key") or "")
        key = str(spec.get("key") or "")
        ids = list(slot_picks.get(key) or [])
        if block:
            out.setdefault(block, []).extend(ids)
    out[SLOT_PICKS_KEY] = {k: list(v) for k, v in slot_picks.items()}
    return out

def _next_pool_id(
    pool: list,
    *,
    used: set[int],
    avoid_ids: set[int],
    avoid_stems: set[str],
    allow_avoided: bool,
) -> int | None:
    for x in pool:
        try:
            eid = _item_eid(x)
        except (TypeError, ValueError, KeyError, AttributeError):
            continue
        if eid in used:
            continue
        if not allow_avoided and _item_is_avoided(x, avoid_ids, avoid_stems):
            continue
        return eid
    return None

def _row_is_bodyweight(item: Any) -> bool:
    if not isinstance(item, dict):
        eq = getattr(item, "equipment_slugs", None)
        return not eq
    if item.get("bw"):
        return True
    if item.get("_gear"):
        return False
    eq = item.get("equipment_slugs")
    return eq is not None and not eq

def _prefer_gear_over_bodyweight(
    chosen: list[int],
    pool: list,
    *,
    used: set[int],
    avoid_ids: set[int],
    avoid_stems: set[str],
) -> list[int]:
    """If the slot still has a gear row, do not keep a bodyweight pick."""
    by_id: dict[int, Any] = {}
    gear_ids: list[int] = []
    saw_bw = False
    for raw in pool:
        try:
            eid = _item_eid(raw)
        except (TypeError, ValueError, KeyError, AttributeError):
            continue
        by_id[eid] = raw
        if _row_is_bodyweight(raw):
            saw_bw = True
            continue
        gear_ids.append(eid)
    if not saw_bw or not gear_ids:
        return chosen
    swapped: list[int] = []
    blocked = set(used)
    for eid in chosen:
        item = by_id.get(eid)
        if item is None or not _row_is_bodyweight(item):
            swapped.append(eid)
            blocked.add(eid)
            continue
        alt = next(
            (
                gid
                for gid in gear_ids
                if gid not in blocked
                and gid not in swapped
                and not _item_is_avoided(by_id[gid], avoid_ids, avoid_stems)
            ),
            None,
        )
        if alt is None:
            swapped.append(eid)
            blocked.add(eid)
            continue
        swapped.append(alt)
        blocked.add(alt)
    return swapped

def _cooldown_gear_match(item: object, pool: list) -> bool | None:
    """True when this cooldown row uses gear and the pool still has a bodyweight option."""
    saw_bw = False
    saw_gear = False
    for raw in pool:
        if _row_is_bodyweight(raw):
            saw_bw = True
        else:
            saw_gear = True
        if saw_bw and saw_gear:
            break
    if not (saw_bw and saw_gear):
        return None
    return not _row_is_bodyweight(item)

def _item_pattern(item: object) -> str | None:
    if isinstance(item, dict):
        raw = item.get("pattern") or item.get("movement_pattern")
    else:
        raw = getattr(item, "movement_pattern", None)
    pat = str(raw or "").strip().lower()
    return pat or None

def merge_week_b_isolation_picks(
    picks_a: dict[str, list[int]],
    llm_b_day: dict[str, Any] | None,
    day_blocks: list[dict],
    *,
    split_role: str | None = None,
    focus_slugs: frozenset[str] | None = None,
    avoid_ids: set[int] | frozenset[int] | list[int] | None = None,
    avoid_stems: set[str] | frozenset[str] | list[str] | None = None,
    slots: list[dict[str, Any]] | None = None,
) -> dict[str, list[int]]:
    """Keep week-A compounds/warmup; swap isolation from the remaining pool."""
    _ = llm_b_day
    if slots:
        return _merge_week_b_slots(
            picks_a,
            day_blocks,
            slots,
            split_role=split_role,
            avoid_ids=avoid_ids,
            avoid_stems=avoid_stems,
        )
    return _copy_picks(picks_a)

def _merge_week_b_slots(
    picks_a: dict[str, list[int]],
    day_blocks: list[dict],
    slots: list[dict[str, Any]],
    *,
    split_role: str | None,
    avoid_ids: set[int] | frozenset[int] | list[int] | None,
    avoid_stems: set[str] | frozenset[str] | list[str] | None,
) -> dict[str, list[int]]:
    from app.services.workout_generation.session_templates import slot_allows_week_b_swap

    raw_slots = (picks_a or {}).get(SLOT_PICKS_KEY) or {}
    a_slots = dict(raw_slots) if isinstance(raw_slots, dict) else {}
    if not a_slots:
        return _copy_picks(picks_a)
    b_raw: dict[str, list[int]] = {}
    avoid_eids = _avoid_id_set(avoid_ids)
    avoid_stem_keys = _avoid_stem_set(avoid_stems)
    used: set[int] = set()
    merged_slots: dict[str, list[int]] = {}
    for spec in slots:
        key = str(spec.get("key") or "")
        n = max(0, int(spec.get("pick") or 1))
        pool = list(spec.get("pool") or [])
        allowed = _shortlist_ids(pool)
        keep = [int(x) for x in (a_slots.get(key) or []) if int(x)]
        if not slot_allows_week_b_swap(spec):
            chosen = [eid for eid in keep if eid in allowed or not allowed][:n]
            merged_slots[key] = chosen
            used.update(chosen)
            continue
        b_ids = [
            eid
            for eid in (b_raw.get(key) or [])
            if eid in allowed and eid not in used and eid not in keep
        ]
        chosen: list[int] = []
        for eid in b_ids:
            if eid not in chosen:
                chosen.append(eid)
            if len(chosen) >= n:
                break
        if chosen:
            chosen = _swap_avoided_picks(
                chosen,
                pool,
                avoid_ids=avoid_eids,
                avoid_stems=avoid_stem_keys,
                extra_used=used | set(keep),
            )
        while len(chosen) < n:
            alt = _next_pool_id(
                pool,
                used=used | set(chosen) | set(keep),
                avoid_ids=avoid_eids,
                avoid_stems=avoid_stem_keys,
                allow_avoided=False,
            )
            if alt is None:
                break
            chosen.append(alt)
        # A small pool may not have enough replacements for every picked id.
        for eid in keep:
            if len(chosen) >= n:
                break
            if eid not in used and eid not in chosen:
                chosen.append(eid)
        while len(chosen) < n:
            alt = _next_pool_id(
                pool,
                used=used | set(chosen),
                avoid_ids=avoid_eids,
                avoid_stems=avoid_stem_keys,
                allow_avoided=True,
            )
            if alt is None:
                break
            chosen.append(alt)
        merged_slots[key] = chosen[:n]
        used.update(merged_slots[key])
    folded = _fold_slot_picks(slots, merged_slots)
    for key, ids in (picks_a or {}).items():
        if str(key).startswith("_"):
            continue
        a_ids = list(ids) if isinstance(ids, list) else []
        # Slot folding rebuilds blocks from prompt slots. Keep week-A ids when
        # a required block folded empty (home resistance compounds, gated pools).
        if not folded.get(key) and a_ids:
            folded[key] = a_ids
        else:
            folded.setdefault(key, a_ids)
    try:
        folded = fill_mobility_picks(day_blocks, folded, split_role=split_role)
    except PickError:
        return _copy_picks(picks_a)
    folded[DOSE_PICKS_KEY] = copy.deepcopy((picks_a or {}).get(DOSE_PICKS_KEY) or {})
    return folded

def clamp_pick_count(count_max: int, n_allowed: int) -> int:
    """Lower recipe count when the shortlist is smaller. Empty catalog is the caller's problem."""
    if count_max <= 0:
        return 0
    if n_allowed <= 0:
        return int(count_max)
    return min(int(count_max), int(n_allowed))

def _shortlist_ids(shortlist: list) -> set[int]:
    out: set[int] = set()
    for x in shortlist:
        try:
            if isinstance(x, dict):
                out.add(int(x["id"]))
            else:
                out.add(int(x.id))
        except (TypeError, ValueError, KeyError, AttributeError):
            continue
    return out

def fill_mobility_picks(
    day_blocks: list[dict],
    picks: dict[str, list[int]],
    *,
    split_role: str | None = None,
) -> dict[str, list[int]]:
    """Fill leftover warmup/cooldown slots. Never invents ids."""
    from app.services.workout_generation.split_map import mobility_match_rank

    out: dict[str, Any] = {}
    for k, v in picks.items():
        if k == SLOT_PICKS_KEY:
            out[k] = v
            continue
        out[k] = list(v)
    trained = _trained_slugs_from_picks(day_blocks, out)
    used: set[int] = set()
    for key, ids in out.items():
        if str(key).startswith("_"):
            continue
        used.update(ids or [])

    for block in day_blocks:
        if not block.get("pick"):
            continue
        key = str(block["block_key"])
        if key not in _MOBILITY_KEYS:
            continue
        shortlist = list(block.get("shortlist") or [])
        if key != "cooldown":
            from app.services.workout_generation.skill_gate import is_warmup_strength_leak

            shortlist = [x for x in shortlist if not is_warmup_strength_leak(x)]
        allowed = _shortlist_ids(shortlist)
        n = clamp_pick_count(int(block.get("count_max") or 0), len(allowed))
        if n <= 0:
            out[key] = []
            continue
        cur = [eid for eid in (out.get(key) or []) if eid in allowed]
        cooldown = key == "cooldown"

        def _rank(item: object) -> int:
            return mobility_match_rank(
                muscle_slug=_item_muscle(item),
                name_vi=_item_name(item),
                split_role=split_role,
                cooldown=cooldown,
                trained_slugs=trained,
                gear_match=_cooldown_gear_match(item, shortlist) if cooldown else None,
            )

        ranked = sorted(shortlist, key=lambda x: (_rank(x), _item_eid(x)))
        by_eid = {_item_eid(x): x for x in shortlist}
        for eid in list(cur):
            used.discard(eid)
        selected: list[int] = []
        for eid in cur:
            item = by_eid.get(eid)
            r = _rank(item) if item is not None else 99
            if item is not None and r <= 1:
                selected.append(eid)
                continue
            replacement = None
            for x in ranked:
                xid = _item_eid(x)
                if xid in used or xid in selected:
                    continue
                if _rank(x) < r:
                    replacement = xid
                    break
            if replacement is not None:
                selected.append(replacement)
            elif item is not None:
                selected.append(eid)
        cur = selected
        used.update(cur)
        for x in ranked:
            if len(cur) >= n:
                break
            eid = _item_eid(x)
            if eid in used or eid in cur:
                continue
            cur.append(eid)
            used.add(eid)
        out[key] = cur[:n]
        used.update(out[key])
    return out

def repair_strength_picks(
    day_blocks: list[dict],
    picks: dict[str, list[int]],
    *,
    split_role: str | None = None,
    focus_slugs: frozenset[str] | None = None,
) -> dict[str, list[int]]:
    """Swap compound/accessory ids inside shortlists to cover quota/pattern gaps."""
    from app.services.workout_generation.coverage import repair_day_coverage
    from app.services.workout_generation.muscle_quotas import repair_muscle_quotas

    out = repair_muscle_quotas(
        day_blocks, picks, split_role=split_role, focus_slugs=focus_slugs
    )
    return repair_day_coverage(day_blocks, out, split_role=split_role)

