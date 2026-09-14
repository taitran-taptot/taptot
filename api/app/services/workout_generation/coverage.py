"""Pattern-family coverage for deterministic workout picks."""

from __future__ import annotations

from typing import Any

from app.services.workout_generation.split_map import normalize_split_role, patterns_for_split

# Movement-pattern → family
_PATTERN_FAMILY: dict[str, str] = {
    "h_push": "push",
    "v_push": "push",
    "h_pull": "pull",
    "v_pull": "pull",
    "squat": "squat",
    "hinge": "hinge",
    "core": "core",
}

# Required families per split (coverage), in pick priority order.
_REQUIRED_FAMILIES: dict[str, tuple[str, ...]] = {
    "push": ("push",),
    "pull": ("pull",),
    "legs": ("squat", "hinge"),
    "lower": ("squat", "hinge"),
    "upper": ("push", "pull"),
    "fb": ("push", "pull", "squat", "hinge"),
    "fb_a": ("push", "pull", "squat", "hinge"),
    "fb_b": ("push", "pull", "squat", "hinge"),
}

# Pattern-level coverage: h_push ≠ v_push. Optional patterns omitted if shortlist lacks them.
_REQUIRED_PATTERNS: dict[str, tuple[str, ...]] = {
    "push": ("h_push",),
    "pull": ("h_pull", "v_pull"),
    "legs": ("squat", "hinge"),
    "lower": ("squat", "hinge"),
    "upper": ("h_push", "h_pull"),
    "fb": ("h_push", "h_pull", "squat", "hinge"),
    "fb_a": ("h_push", "h_pull", "squat", "hinge"),
    "fb_b": ("v_push", "v_pull", "squat", "hinge"),
}

_STRENGTH_BLOCKS = frozenset({"compound", "accessory", "resistance", "conditioning"})
_FB_KEYS = frozenset({"fb", "fb_a", "fb_b"})
_TRICEPS_SLUGS = frozenset({"triceps", "co-tay-sau"})
_PRESS_PATTERNS = frozenset({"h_push", "v_push"})


def _family_fill_order(split_role: str | None) -> tuple[str, ...]:
    """Interleave lower/upper on Full Body so 2 compounds are not both press/row."""
    key = normalize_split_role(split_role)
    if key in _FB_KEYS:
        return ("squat", "push", "hinge", "pull")
    return required_families(split_role)


def _pattern_pref_for_family(split_role: str | None, fam: str) -> tuple[str, ...]:
    key = normalize_split_role(split_role)
    if fam == "push":
        return ("v_push", "h_push") if key == "fb_b" else ("h_push", "v_push")
    if fam == "pull":
        return ("v_pull", "h_pull") if key == "fb_b" else ("h_pull", "v_pull")
    if fam == "squat":
        return ("squat",)
    if fam == "hinge":
        return ("hinge",)
    if fam == "core":
        return ("core",)
    return ()


def family_of(pattern: str | None) -> str | None:
    if not pattern:
        return None
    return _PATTERN_FAMILY.get(str(pattern).strip().lower())


def _is_main_section(ex: Any) -> bool:
    return (getattr(ex, "section", "main") or "main") == "main"


def day_covered_families(day: Any, meta_by_id: dict[int, dict[str, Any]]) -> set[str]:
    """Movement families present in a day's main exercises."""
    return families_from_exercises(getattr(day, "exercises", None) or [], meta_by_id)


def families_from_exercises(
    exercises: list[Any],
    meta_by_id: dict[int, dict[str, Any]],
) -> set[str]:
    out: set[str] = set()
    for ex in exercises:
        if not _is_main_section(ex):
            continue
        try:
            eid = int(ex.exercise_id)
        except (TypeError, ValueError, AttributeError):
            continue
        meta = meta_by_id.get(eid) or {}
        fam = family_of(meta.get("movement_pattern"))
        if fam:
            out.add(fam)
    return out


def _meta_muscle(meta: dict[str, Any] | None) -> str:
    raw = meta or {}
    return str(raw.get("muscle_slug") or raw.get("muscle") or "").strip().lower()


def is_real_press(meta: dict[str, Any] | None) -> bool:
    """Horizontal/vertical press that is not a triceps isolation/pushdown."""
    raw = meta or {}
    pat = str(raw.get("movement_pattern") or "").strip().lower()
    if pat not in _PRESS_PATTERNS:
        return False
    return _meta_muscle(raw) not in _TRICEPS_SLUGS


def coverage_ok(plan_days: list[Any], meta_by_id: dict[int, dict[str, Any]]) -> bool:
    """True if every day covers required families plus upper press / legs squat pattern."""
    for day in plan_days:
        role = getattr(day, "split_role", None)
        req = required_families(role)
        if not req:
            continue
        covered = day_covered_families(day, meta_by_id)
        n_strength = 0
        has_press = False
        has_squat = False
        for ex in getattr(day, "exercises", None) or []:
            if not _is_main_section(ex):
                continue
            try:
                eid = int(ex.exercise_id)
            except (TypeError, ValueError, AttributeError):
                continue
            meta = meta_by_id.get(eid) or {}
            if family_of(meta.get("movement_pattern")):
                n_strength += 1
            if is_real_press(meta):
                has_press = True
            if str(meta.get("movement_pattern") or "").strip().lower() == "squat":
                has_squat = True
        if n_strength <= 0:
            return False
        need = min(len(req), n_strength)
        hit = sum(1 for fam in req if fam in covered)
        if hit < need:
            return False
        key = normalize_split_role(role)
        if n_strength >= 2:
            if key == "upper" and not has_press:
                return False
            if key in {"legs", "lower"} and not has_squat:
                return False
    return True


def repair_plan_day_upper_pull(
    day: Any,
    *,
    candidates: list[Any],
    meta_by_id: dict[int, dict[str, Any]],
) -> bool:
    """Replace one redundant Upper accessory when the final day has no back pull.

    This is a post-processing guard: it never adds an exercise or changes sets.
    Pick-level coverage can be lost later when weekly dose/refill rewrites a day.
    """
    if normalize_split_role(getattr(day, "split_role", None)) != "upper":
        return False

    exercises = list(getattr(day, "exercises", None) or [])
    main_indices = [
        i for i, ex in enumerate(exercises) if _is_main_section(ex)
    ]
    if any(
        family_of(
            (meta_by_id.get(int(exercises[i].exercise_id)) or {}).get(
                "movement_pattern"
            )
        )
        == "pull"
        for i in main_indices
    ):
        return False

    used = {int(ex.exercise_id) for ex in exercises}

    def candidate_meta(raw: Any) -> tuple[int, dict[str, Any]] | None:
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
        else:
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
        if eid in used or family_of(meta.get("movement_pattern")) != "pull":
            return None
        return eid, meta

    pull_candidates = [
        parsed
        for raw in candidates
        if (parsed := candidate_meta(raw)) is not None
    ]
    if not pull_candidates:
        return False

    # Preserve the only real press; replace core/arm isolation before chest work.
    press_count = sum(
        1
        for i in main_indices
        if is_real_press(meta_by_id.get(int(exercises[i].exercise_id)))
    )

    def replace_priority(index: int) -> tuple[int, int]:
        meta = meta_by_id.get(int(exercises[index].exercise_id)) or {}
        role = str(meta.get("movement_role") or "").strip().lower()
        pattern = str(meta.get("movement_pattern") or "").strip().lower()
        muscle = _meta_muscle(meta)
        sole_press = is_real_press(meta) and press_count <= 1
        if sole_press:
            return (99, index)
        if pattern == "core" or muscle.startswith("core"):
            return (0, -index)
        if role == "isolation" and muscle in {"biceps", "triceps", "co-tay-truoc", "co-tay-sau"}:
            return (1, -index)
        if role == "isolation":
            return (2, -index)
        return (3, -index)

    replace_i = min(main_indices, key=replace_priority, default=None)
    if replace_i is None or replace_priority(replace_i)[0] >= 99:
        return False

    old_meta = meta_by_id.get(int(exercises[replace_i].exercise_id)) or {}
    old_role = str(old_meta.get("movement_role") or "").strip().lower()
    pull_candidates.sort(
        key=lambda pair: (
            str(pair[1].get("movement_role") or "").strip().lower() != old_role,
            pair[0],
        )
    )
    new_id, new_meta = pull_candidates[0]
    exercises[replace_i].exercise_id = new_id
    meta_by_id.setdefault(new_id, {}).update(
        {k: v for k, v in new_meta.items() if v not in (None, "")}
    )
    day.exercises = exercises
    return True


def required_families(split_role: str | None) -> tuple[str, ...]:
    key = normalize_split_role(split_role)
    if key in {"conditioning", "mobility", "recovery", "core"}:
        return ()
    return _REQUIRED_FAMILIES.get(key, ())


def required_patterns(split_role: str | None) -> tuple[str, ...]:
    key = normalize_split_role(split_role)
    if key in {"conditioning", "mobility", "recovery", "core"}:
        return ()
    return _REQUIRED_PATTERNS.get(key, ())


def _item_pattern(item: dict[str, Any] | Any) -> str | None:
    if isinstance(item, dict):
        p = item.get("movement_pattern")
    else:
        p = getattr(item, "movement_pattern", None)
    return str(p).strip().lower() if p else None


def _item_id(item: dict[str, Any] | Any) -> int:
    if isinstance(item, dict):
        return int(item["id"])
    return int(item.id)


def diversified_pick(
    shortlist: list[Any],
    *,
    count: int,
    split_role: str | None,
    used_ids: set[int] | None = None,
    block_key: str | None = None,
    already_covered: set[str] | None = None,
) -> list[int]:
    """
    Pick up to `count` ids from shortlist with pattern-family quota.
    Prefer covering required families still missing (`already_covered`).
    """
    if count <= 0 or not shortlist:
        return []

    used_ids = used_ids or set()
    preferred = patterns_for_split(split_role)
    req = list(required_families(split_role))
    req_pats = list(required_patterns(split_role))
    strength = (block_key or "compound") in _STRENGTH_BLOCKS

    items = [i for i in shortlist if _item_id(i) not in used_ids]
    if not items:
        items = list(shortlist)

    by_family: dict[str, list[Any]] = {}
    preferred_pool: list[Any] = []
    other_pool: list[Any] = []
    for it in items:
        pat = _item_pattern(it)
        fam = family_of(pat)
        if fam:
            by_family.setdefault(fam, []).append(it)
        if pat and pat in preferred:
            preferred_pool.append(it)
        else:
            other_pool.append(it)

    picked: list[int] = []
    picked_set: set[int] = set()
    covered: set[str] = set(already_covered or ())
    covered_pats: set[str] = set()

    def take_from(pool: list[Any], fam: str | None = None, pat: str | None = None) -> bool:
        for it in pool:
            eid = _item_id(it)
            if eid in picked_set or eid in used_ids:
                continue
            item_pat = _item_pattern(it)
            if fam is not None and family_of(item_pat) != fam:
                continue
            if pat is not None and item_pat != pat:
                continue
            picked.append(eid)
            picked_set.add(eid)
            f = family_of(item_pat)
            if f:
                covered.add(f)
            if item_pat:
                covered_pats.add(item_pat)
            return True
        return False

    fill_order = list(_family_fill_order(split_role)) or list(req)
    if strength and (fill_order or req_pats or req):
        made_progress = True
        while len(picked) < count and made_progress:
            made_progress = False
            for fam in fill_order:
                if len(picked) >= count:
                    break
                if fam in covered:
                    continue
                for pat in _pattern_pref_for_family(split_role, fam):
                    matched = [i for i in items if _item_pattern(i) == pat]
                    if take_from(matched, pat=pat):
                        made_progress = True
                        break
                if fam not in covered and by_family.get(fam):
                    if take_from(by_family[fam], fam):
                        made_progress = True
            if made_progress:
                continue
            for pat in req_pats:
                if len(picked) >= count:
                    break
                if pat in covered_pats:
                    continue
                if family_of(pat) in covered:
                    continue
                matched = [i for i in items if _item_pattern(i) == pat]
                if take_from(matched, pat=pat):
                    made_progress = True
            if made_progress:
                continue
            for fam in req:
                if len(picked) >= count:
                    break
                if fam in covered:
                    continue
                if not by_family.get(fam):
                    continue
                if take_from(by_family[fam], fam):
                    made_progress = True

        preferred_ordered = sorted(preferred)
        idx = 0
        guard = 0
        while len(picked) < count and preferred_pool and guard < count * 8:
            guard += 1
            if not preferred_ordered:
                break
            want = preferred_ordered[idx % len(preferred_ordered)]
            idx += 1
            matched = [i for i in preferred_pool if _item_pattern(i) == want]
            if not take_from(matched):
                if not take_from(preferred_pool):
                    break
    else:
        for it in items:
            if len(picked) >= count:
                break
            eid = _item_id(it)
            if eid not in picked_set and eid not in used_ids:
                picked.append(eid)
                picked_set.add(eid)

    for pool in (preferred_pool, other_pool, items):
        for it in pool:
            if len(picked) >= count:
                break
            eid = _item_id(it)
            if eid not in picked_set and eid not in used_ids:
                picked.append(eid)
                picked_set.add(eid)

    return picked[:count]


def day_available_families(day_blocks: list[dict[str, Any]]) -> set[str]:
    """Families present anywhere in day's strength shortlists."""
    out: set[str] = set()
    for block in day_blocks:
        if str(block.get("block_key")) not in _STRENGTH_BLOCKS:
            continue
        for raw in block.get("shortlist") or []:
            if isinstance(raw, dict):
                fam = family_of(_item_pattern(raw))
                if fam:
                    out.add(fam)
    return out


def effective_required_families(
    split_role: str | None,
    day_blocks: list[dict[str, Any]],
) -> tuple[str, ...]:
    """Required families narrowed to those available in shortlists."""
    avail = day_available_families(day_blocks)
    return tuple(f for f in required_families(split_role) if f in avail)


def day_available_patterns(day_blocks: list[dict[str, Any]]) -> set[str]:
    out: set[str] = set()
    for block in day_blocks:
        if str(block.get("block_key")) not in _STRENGTH_BLOCKS:
            continue
        for raw in block.get("shortlist") or []:
            if isinstance(raw, dict):
                pat = _item_pattern(raw)
                if pat:
                    out.add(pat)
    return out


def effective_required_patterns(
    split_role: str | None,
    day_blocks: list[dict[str, Any]],
) -> tuple[str, ...]:
    avail = day_available_patterns(day_blocks)
    return tuple(p for p in required_patterns(split_role) if p in avail)


def repair_day_coverage(
    day_blocks: list[dict[str, Any]],
    picks_by_block: dict[str, list[int]],
    *,
    split_role: str | None,
) -> dict[str, list[int]]:
    """
    If required families missing and accessory shortlist has candidates,
    replace a redundant accessory with a missing-family pick.
    """
    req = effective_required_families(split_role, day_blocks)
    if not req:
        return picks_by_block

    picks = {k: list(v) for k, v in picks_by_block.items()}
    blocks_by_key = {str(b.get("block_key")): b for b in day_blocks}

    id_to_meta: dict[int, dict[str, Any]] = {}
    for block in day_blocks:
        for raw in block.get("shortlist") or []:
            if isinstance(raw, dict):
                id_to_meta[int(raw["id"])] = raw

    def family_counts_all() -> dict[str, int]:
        out: dict[str, int] = {}
        for ids in picks.values():
            for eid in ids:
                f = family_of(_item_pattern(id_to_meta.get(int(eid), {}))) or "_"
                out[f] = out.get(f, 0) + 1
        return out

    def can_drop(fam_to_drop: str | None) -> bool:
        if not fam_to_drop or fam_to_drop == "_":
            return True
        if fam_to_drop not in req:
            return True
        return family_counts_all().get(fam_to_drop, 0) > 1

    def covered() -> set[str]:
        out: set[str] = set()
        for ids in picks.values():
            for eid in ids:
                fam = family_of(_item_pattern(id_to_meta.get(int(eid), {})))
                if fam:
                    out.add(fam)
        return out

    def candidates_in(fam: str, key: str) -> list[int]:
        used = {eid for ids in picks.values() for eid in ids}
        found: list[int] = []
        block = blocks_by_key.get(key) or {}
        for raw in block.get("shortlist") or []:
            if not isinstance(raw, dict):
                continue
            eid = int(raw["id"])
            if eid in used:
                continue
            if family_of(_item_pattern(raw)) == fam:
                found.append(eid)
        return found

    cov = covered()
    for fam in req:
        if fam in cov:
            continue
        swap_key = None
        swap_idx = None
        cands: list[int] = []
        for key in ("accessory", "resistance", "compound"):
            ids = picks.get(key) or []
            if not ids:
                continue
            block_cands = candidates_in(fam, key)
            if not block_cands:
                continue
            for i, eid in enumerate(reversed(ids)):
                f = family_of(_item_pattern(id_to_meta.get(int(eid), {})))
                if f == fam:
                    continue
                if can_drop(f):
                    swap_key = key
                    swap_idx = len(ids) - 1 - i
                    cands = block_cands
                    break
            if swap_key is not None:
                break
            if key in {"accessory", "resistance"} and ids and block_cands:
                last_f = family_of(_item_pattern(id_to_meta.get(int(ids[-1]), {})))
                if can_drop(last_f):
                    swap_key = key
                    swap_idx = len(ids) - 1
                    cands = block_cands
                    break

        if swap_key is None or swap_idx is None or not cands:
            acc_key = "resistance" if "resistance" in blocks_by_key else "accessory"
            acc = blocks_by_key.get(acc_key) or {}
            max_n = int(acc.get("count_max") or 0)
            cur = picks.get(acc_key) or []
            extra = candidates_in(fam, acc_key)
            if max_n and len(cur) < max_n and extra:
                picks.setdefault(acc_key, []).append(extra[0])
                cov = covered()
            continue

        picks[swap_key][swap_idx] = cands[0]
        cov = covered()

    req_pats = effective_required_patterns(split_role, day_blocks)

    def covered_pats() -> set[str]:
        out: set[str] = set()
        for ids in picks.values():
            for eid in ids:
                pat = _item_pattern(id_to_meta.get(int(eid), {}))
                if pat:
                    out.add(pat)
        return out

    def candidates_for_pat(pat: str, key: str) -> list[int]:
        used = {eid for ids in picks.values() for eid in ids}
        found: list[int] = []
        block = blocks_by_key.get(key) or {}
        for raw in block.get("shortlist") or []:
            if not isinstance(raw, dict):
                continue
            eid = int(raw["id"])
            if eid in used:
                continue
            if _item_pattern(raw) != pat:
                continue
            if pat in _PRESS_PATTERNS and not is_real_press(raw):
                continue
            found.append(eid)
        return found

    cov_p = covered_pats()
    for pat in req_pats:
        if pat in cov_p:
            continue
        swap_key = None
        swap_idx = None
        cands: list[int] = []
        for key in ("accessory", "resistance", "compound", "conditioning"):
            ids = picks.get(key) or []
            if not ids:
                continue
            block_cands = candidates_for_pat(pat, key)
            if not block_cands:
                continue
            for i, eid in enumerate(reversed(ids)):
                p = _item_pattern(id_to_meta.get(int(eid), {}))
                if p == pat:
                    continue
                if can_drop(family_of(p)):
                    swap_key = key
                    swap_idx = len(ids) - 1 - i
                    cands = block_cands
                    break
            if swap_key is not None:
                break
            if key in {"accessory", "resistance"} and ids:
                last_pat = _item_pattern(id_to_meta.get(int(ids[-1]), {}))
                if last_pat != pat and can_drop(family_of(last_pat)):
                    swap_key = key
                    swap_idx = len(ids) - 1
                    cands = block_cands
                    break
        if swap_key is None or swap_idx is None or not cands:
            continue
        picks[swap_key][swap_idx] = cands[0]
        cov_p = covered_pats()

    role_key = normalize_split_role(split_role)

    def _ids_in_block(key: str, pred) -> list[int]:
        used = {eid for ids in picks.values() for eid in ids}
        found: list[int] = []
        for raw in (blocks_by_key.get(key) or {}).get("shortlist") or []:
            if not isinstance(raw, dict):
                continue
            eid = int(raw["id"])
            if eid in used:
                continue
            if pred(raw):
                found.append(eid)
        return found

    def _force_swap(keep_pred, need_pred) -> None:
        """Swap within one block so assemble does not drop cross-block ids."""
        for key in ("accessory", "resistance", "compound"):
            cands = _ids_in_block(key, need_pred)
            if not cands:
                continue
            ids = picks.get(key) or []
            best_i = None
            best_pri = 99
            for i in range(len(ids) - 1, -1, -1):
                meta = id_to_meta.get(int(ids[i]), {})
                if keep_pred(meta):
                    continue
                fam = family_of(_item_pattern(meta))
                if not can_drop(fam):
                    continue
                pri = 0 if str(meta.get("movement_role") or "") == "isolation" else 1
                if pri < best_pri:
                    best_pri = pri
                    best_i = i
            if best_i is not None:
                picks[key][best_i] = cands[0]
                return
        acc_key = "resistance" if "resistance" in blocks_by_key else "accessory"
        acc = blocks_by_key.get(acc_key) or {}
        max_n = int(acc.get("count_max") or 0)
        cur = picks.get(acc_key) or []
        extra = _ids_in_block(acc_key, need_pred)
        if max_n and len(cur) < max_n and extra:
            picks.setdefault(acc_key, []).append(extra[0])

    if role_key == "upper":
        already = any(
            is_real_press(id_to_meta.get(int(eid), {}))
            for ids in picks.values()
            for eid in ids
        )
        if not already:
            _force_swap(is_real_press, is_real_press)
    if role_key in {"legs", "lower"}:
        already = any(
            _item_pattern(id_to_meta.get(int(eid), {})) == "squat"
            for ids in picks.values()
            for eid in ids
        )
        if not already:
            _force_swap(
                lambda m: _item_pattern(m) == "squat",
                lambda m: _item_pattern(m) == "squat",
            )

    return picks
