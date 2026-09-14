"""Muscle-group quotas for PPL + Upper/Lower deterministic picks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.services.workout_generation.coverage import family_of
from app.services.workout_generation.split_map import (
    is_denied_for_split,
    muscle_hints_for_split,
    normalize_split_role,
    patterns_for_split,
)

Matcher = Callable[[dict[str, Any]], bool]

# Canonical EN slugs preferred; keep VI / legacy aliases for DBs not yet remapped.
CHEST_SLUGS = frozenset(
    {"chest", "co-nguc", "chest-upper", "chest-mid", "chest-lower"}
)
BACK_SLUGS = frozenset(
    {"back", "co-lung", "back-lats", "back-middle", "back-lower"}
)
SHOULDER_SLUGS = frozenset(
    {
        "shoulders",
        "shoulders-deltoids",
        "co-vai",
        "shoulders-front",
        "shoulders-lateral",
        "shoulders-rear",
        "shoulders-traps",
    }
)
# Push-day shoulder work: OHP / lateral / front — not rear-delt pulls (those are Pull).
PUSH_SHOULDER_SLUGS = frozenset(
    {
        "shoulders",
        "shoulders-deltoids",
        "co-vai",
        "shoulders-front",
        "shoulders-lateral",
    }
)
REAR_DELT_SLUGS = frozenset({"shoulders-rear"})
BICEPS_SLUGS = frozenset({"biceps", "co-tay-truoc"})
TRICEPS_SLUGS = frozenset({"triceps", "co-tay-sau"})
QUAD_SLUGS = frozenset({"quads", "co-dui-truoc", "upper-legs"})
HINGE_MUSCLE_SLUGS = frozenset({"hamstrings", "glutes", "co-dui-sau", "co-mong"})
HAMSTRING_SLUGS = frozenset({"hamstrings", "co-dui-sau"})
CALF_SLUGS = frozenset({"calves", "co-bap-chan", "lower-legs"})
CORE_SLUGS = frozenset(
    {"core", "co-bung", "waist", "abs", "core-upper", "core-lower", "core-obliques"}
)
GLUTE_SLUGS = frozenset({"glutes", "co-mong"})
PULL_PATTERNS = frozenset({"h_pull", "v_pull"})
PUSH_PATTERNS = frozenset({"h_push", "v_push"})

MUSCLE_QUOTA_ROLES = frozenset({"push", "pull", "legs", "lower", "upper"})

# Compound pattern slots filled first so a 2-lift Push day is chest + OHP, not 2× bench.
COMPOUND_PATTERN_SLOTS: dict[str, tuple[str, ...]] = {
    "push": ("h_push", "v_push"),
    "pull": ("v_pull", "h_pull"),
    "legs": ("squat", "hinge"),
    "lower": ("squat", "hinge"),
    "upper": ("h_push", "h_pull"),
}

# Within compounds: heavy / primary pattern first.
_COMPOUND_PATTERN_RANK: dict[str, dict[str, int]] = {
    "push": {"h_push": 0, "v_push": 1},
    "pull": {"v_pull": 0, "h_pull": 1},
    "legs": {"squat": 0, "hinge": 1},
    "lower": {"squat": 0, "hinge": 1},
    "upper": {"h_push": 0, "h_pull": 1, "v_push": 2, "v_pull": 3},
    "fb": {"squat": 0, "h_push": 1, "hinge": 2, "h_pull": 3, "v_push": 4, "v_pull": 5, "core": 6},
    "fb_a": {"squat": 0, "h_push": 1, "hinge": 2, "h_pull": 3},
    "fb_b": {"squat": 0, "v_push": 1, "hinge": 2, "v_pull": 3},
}


@dataclass(frozen=True)
class QuotaBucket:
    key: str
    min_n: int
    max_n: int
    match: Matcher


def _as_dict(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return item
    return {
        "id": int(item.id),
        "movement_pattern": getattr(item, "movement_pattern", None),
        "movement_role": getattr(item, "movement_role", None),
        "muscle": getattr(item, "muscle_slug", None) or getattr(item, "muscle", None),
        "name_vi": getattr(item, "name_vi", ""),
        "name_en": getattr(item, "name_en", ""),
    }


def _muscle(d: dict[str, Any]) -> str:
    return str(d.get("muscle") or d.get("muscle_slug") or "").strip().lower()


def _pattern(d: dict[str, Any]) -> str:
    return str(d.get("movement_pattern") or "").strip().lower()


def _role(d: dict[str, Any]) -> str:
    return str(d.get("movement_role") or "").strip().lower()


def _eid(d: dict[str, Any]) -> int:
    return int(d["id"])


def _slug_in(d: dict[str, Any], slugs: frozenset[str]) -> bool:
    return _muscle(d) in slugs


def _match_back(d: dict[str, Any]) -> bool:
    return _slug_in(d, BACK_SLUGS)


def _match_rear_delt(d: dict[str, Any]) -> bool:
    """Rear-delt / face-pull isolations belong on Pull, not Push.

    Catalog rows may use pattern ``other`` (e.g. ring face-pull) while still
    targeting shoulders-rear — treat those as rear delt too.
    """
    if not _slug_in(d, REAR_DELT_SLUGS | frozenset({"shoulders", "shoulders-deltoids", "co-vai"})):
        return False
    if _role(d) != "isolation":
        return False
    if _slug_in(d, REAR_DELT_SLUGS):
        return True
    if _pattern(d) in PULL_PATTERNS:
        return True
    blob = " ".join(
        str(d.get(k) or "") for k in ("name_vi", "name_en", "name")
    ).lower()
    return any(
        k in blob
        for k in (
            "face pull",
            "face-pull",
            "rear delt",
            "rear-delt",
            "bay vai sau",
            "vai sau",
            "pull-apart",
            "pull apart",
        )
    )


def _match_biceps(d: dict[str, Any]) -> bool:
    return _slug_in(d, BICEPS_SLUGS)


def _match_chest(d: dict[str, Any]) -> bool:
    return _slug_in(d, CHEST_SLUGS)


def _match_push_shoulder(d: dict[str, Any]) -> bool:
    """OHP, lateral/front raise, upright row — not rear-delt pulls (those are Pull)."""
    if not _slug_in(d, PUSH_SHOULDER_SLUGS):
        return False
    if _match_rear_delt(d):
        return False
    if _pattern(d) in PULL_PATTERNS:
        return False
    return True


def _match_triceps(d: dict[str, Any]) -> bool:
    return _slug_in(d, TRICEPS_SLUGS)


def _match_squat_quad(d: dict[str, Any]) -> bool:
    return family_of(_pattern(d)) == "squat" or _slug_in(d, QUAD_SLUGS)


def _match_hinge_post(d: dict[str, Any]) -> bool:
    return family_of(_pattern(d)) == "hinge" or _slug_in(d, HAMSTRING_SLUGS)


def _match_calves(d: dict[str, Any]) -> bool:
    return _slug_in(d, CALF_SLUGS)


def _is_calf_exercise(d: dict[str, Any]) -> bool:
    if _match_calves(d):
        return True
    blob = " ".join(
        str(d.get(k) or "") for k in ("name_vi", "name_en", "name")
    ).lower()
    return (
        "calf" in blob
        or "bắp chân" in blob
        or "bap chan" in blob
        or "nhón" in blob
        or "nhon bap" in blob
    )


def _match_h_push(d: dict[str, Any]) -> bool:
    # Triceps isolations are often tagged h_push; they belong in the triceps bucket.
    return _pattern(d) == "h_push" and not _match_triceps(d)


def _match_h_pull(d: dict[str, Any]) -> bool:
    return _pattern(d) == "h_pull" and not _match_rear_delt(d)


def _match_v_pull(d: dict[str, Any]) -> bool:
    return _pattern(d) == "v_pull"


MUSCLE_QUOTAS: dict[str, tuple[QuotaBucket, ...]] = {
    "pull": (
        QuotaBucket("back", 2, 4, _match_back),
        QuotaBucket("rear_delt", 0, 1, _match_rear_delt),
        QuotaBucket("biceps", 1, 2, _match_biceps),
    ),
    "push": (
        QuotaBucket("chest", 1, 4, _match_chest),
        QuotaBucket("shoulders", 1, 2, _match_push_shoulder),
        QuotaBucket("triceps", 1, 2, _match_triceps),
    ),
    "legs": (
        QuotaBucket("squat_quad", 1, 3, _match_squat_quad),
        QuotaBucket("hinge_post", 1, 3, _match_hinge_post),
        QuotaBucket("calves", 0, 2, _match_calves),
    ),
    "lower": (
        QuotaBucket("squat_quad", 1, 3, _match_squat_quad),
        QuotaBucket("hinge_post", 1, 3, _match_hinge_post),
        QuotaBucket("calves", 0, 2, _match_calves),
    ),
    "upper": (
        QuotaBucket("h_push", 1, 2, _match_h_push),
        QuotaBucket("h_pull", 1, 2, _match_h_pull),
        QuotaBucket("v_push", 0, 1, _match_push_shoulder),
        QuotaBucket("v_pull", 0, 1, _match_v_pull),
        QuotaBucket("biceps", 0, 2, _match_biceps),
        QuotaBucket("triceps", 0, 1, _match_triceps),
    ),
}


def uses_muscle_quotas(split_role: str | None) -> bool:
    return normalize_split_role(split_role) in MUSCLE_QUOTA_ROLES


def keep_outside_preferred_pattern(
    split_role: str | None,
    *,
    muscle_slug: str | None,
    pattern: str | None,
) -> bool:
    """Isolation pattern=other (fly/raise/curl) still belongs on the matching split day."""
    if is_denied_for_split(split_role, pattern=pattern, muscle_slug=muscle_slug):
        return False
    key = normalize_split_role(split_role)
    slug = str(muscle_slug or "").strip().lower()
    pat = str(pattern or "").strip().lower()
    if key == "pull" and slug in BICEPS_SLUGS:
        return True
    if key == "upper" and slug in BICEPS_SLUGS | TRICEPS_SLUGS:
        return True
    if key in {"legs", "lower"} and slug in CALF_SLUGS | HAMSTRING_SLUGS:
        return True
    if pat == "other" and slug in muscle_hints_for_split(key):
        return True
    return False


def quotas_for_split(
    split_role: str | None,
    *,
    focus_slugs: frozenset[str] | None = None,
    lift_slots: int | None = None,
) -> tuple[QuotaBucket, ...]:
    key = normalize_split_role(split_role)
    buckets = MUSCLE_QUOTAS.get(key, ())
    if not buckets:
        return buckets
    bumped: list[QuotaBucket] = []
    slots = int(lift_slots) if lift_slots is not None else 0
    for b in buckets:
        min_n = b.min_n
        max_n = b.max_n
        if focus_slugs and _bucket_is_focus(b, focus_slugs):
            min_n = min(max_n, min_n + 1)
        # 4+ lift Push: 2 chest. 5+ lifts: 2-2-1 or 2-1-2, never 1 chest + 3 triceps.
        if key == "push":
            if b.key == "chest" and slots >= 4:
                min_n = min(max_n, max(min_n, 2))
            if b.key == "shoulders" and slots >= 5:
                min_n = min(max_n, max(min_n, 2))
        bumped.append(QuotaBucket(b.key, min_n, max_n, b.match))
    return tuple(bumped)


def _bucket_is_focus(bucket: QuotaBucket, focus_slugs: frozenset[str]) -> bool:
    key_slugs = {
        "chest": CHEST_SLUGS,
        "back": BACK_SLUGS,
        "biceps": BICEPS_SLUGS,
        "triceps": TRICEPS_SLUGS,
        "shoulders": SHOULDER_SLUGS,
        "rear_delt": SHOULDER_SLUGS,
        "calves": CALF_SLUGS,
        "squat_quad": QUAD_SLUGS,
        "hinge_post": HINGE_MUSCLE_SLUGS | GLUTE_SLUGS,
        "h_push": CHEST_SLUGS,
        "h_pull": BACK_SLUGS,
        "v_push": SHOULDER_SLUGS,
        "v_pull": BACK_SLUGS,
        "push_side": CHEST_SLUGS | SHOULDER_SLUGS | TRICEPS_SLUGS,
        "pull_side": BACK_SLUGS | BICEPS_SLUGS | SHOULDER_SLUGS,
        "core": CORE_SLUGS,
    }.get(bucket.key)
    if not key_slugs:
        return False
    return bool(key_slugs & focus_slugs)


def _normalize_pool(pool: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for raw in pool:
        d = _as_dict(raw)
        eid = _eid(d)
        if eid in seen:
            continue
        seen.add(eid)
        out.append(d)
    return out


def allocate_muscle_quotas(
    split_role: str | None,
    pool: list[Any],
    *,
    compound_n: int,
    accessory_n: int,
    focus_slugs: frozenset[str] | None = None,
    avoid_compound_patterns: frozenset[str] | None = None,
) -> tuple[list[int], list[int]]:
    """
    Allocate exercise ids by muscle-bucket mins/maxes, then split into
    compound vs accessory blocks.
    """
    slots = max(0, int(compound_n)) + max(0, int(accessory_n))
    if slots <= 0:
        return [], []

    buckets = quotas_for_split(
        split_role, focus_slugs=focus_slugs, lift_slots=slots
    )
    items = _normalize_pool(pool)
    preferred = patterns_for_split(split_role)

    # Prefer staying inside preferred patterns when possible
    preferred_items = [
        d
        for d in items
        if _pattern(d) in preferred and not is_denied_for_split(
            split_role, pattern=_pattern(d), muscle_slug=_muscle(d)
        )
    ]
    allowed_items = [
        d
        for d in items
        if not is_denied_for_split(split_role, pattern=_pattern(d), muscle_slug=_muscle(d))
    ]

    def _pick_order(d: dict[str, Any]) -> tuple:
        return (0 if _role(d) == "compound" else 1,) + quota_sort_key(
            split_role, d, focus_slugs=focus_slugs
        )

    preferred_items = sorted(preferred_items, key=_pick_order)
    allowed_items = sorted(allowed_items, key=_pick_order)
    work_pool = preferred_items if preferred_items else allowed_items

    picked: list[dict[str, Any]] = []
    picked_ids: set[int] = set()
    counts: dict[str, int] = {b.key: 0 for b in buckets}
    pattern_n: dict[str, int] = {}
    sig_n: dict[tuple[str, str, str], int] = {}
    v_push_compounds = 0
    avoid_pats = frozenset(
        str(p).strip().lower() for p in (avoid_compound_patterns or ()) if str(p).strip()
    )

    def _allowed(d: dict[str, Any]) -> bool:
        if is_denied_for_split(split_role, pattern=_pattern(d), muscle_slug=_muscle(d)):
            return False
        pat = _pattern(d) or "other"
        muscle = _muscle(d)
        role = _role(d)
        if role == "compound" and pat in avoid_pats:
            return False
        if role == "compound" and sum(1 for x in picked if _role(x) == "compound") >= max(0, int(compound_n)):
            return False
        if pat == "v_push" and role == "compound" and v_push_compounds >= 1:
            return False
        if role != "compound":
            cap = 1 if muscle in SHOULDER_SLUGS else 2
        else:
            cap = 1 if pat == "v_push" else 2
        if sig_n.get((pat, muscle, role), 0) >= cap:
            return False
        return True

    def _commit(d: dict[str, Any], bucket: QuotaBucket | None) -> None:
        eid = _eid(d)
        picked.append(d)
        picked_ids.add(eid)
        pat = _pattern(d) or "other"
        muscle = _muscle(d)
        role = _role(d)
        pattern_n[pat] = pattern_n.get(pat, 0) + 1
        sig = (pat, muscle, role)
        sig_n[sig] = sig_n.get(sig, 0) + 1
        if pat == "v_push" and role == "compound":
            nonlocal v_push_compounds
            v_push_compounds += 1
        if bucket:
            counts[bucket.key] = counts.get(bucket.key, 0) + 1

    def first_bucket(d: dict[str, Any]) -> QuotaBucket | None:
        for b in buckets:
            if b.match(d):
                return b
        return None

    # Slot compounds by pattern (Push: h_push then v_push) before filling muscle mins.
    split_key = normalize_split_role(split_role)
    for pat in COMPOUND_PATTERN_SLOTS.get(split_key, ()):
        if len(picked) >= max(0, int(compound_n)):
            break
        for source in (work_pool, allowed_items):
            hit = next(
                (
                    d
                    for d in source
                    if _eid(d) not in picked_ids
                    and _role(d) == "compound"
                    and _pattern(d) == pat
                    and _allowed(d)
                ),
                None,
            )
            if hit:
                _commit(hit, first_bucket(hit))
                break

    def take_matching(bucket: QuotaBucket, *, respect_max: bool = True) -> bool:
        if len(picked) >= slots:
            return False
        if respect_max and counts.get(bucket.key, 0) >= bucket.max_n:
            return False
        for pool in (work_pool, allowed_items):
            for d in pool:
                eid = _eid(d)
                if eid in picked_ids:
                    continue
                if not bucket.match(d):
                    continue
                if not _allowed(d):
                    continue
                _commit(d, bucket)
                return True
        return False

    # Phase 1: fill mins in bucket priority order
    for bucket in buckets:
        target = min(bucket.min_n, max(0, slots - len(picked)))
        # Leave room only implicitly by stopping at slots
        while counts.get(bucket.key, 0) < target and len(picked) < slots:
            if not take_matching(bucket):
                break

    # Phase 2: fill toward max
    progressed = True
    while progressed and len(picked) < slots:
        progressed = False
        for bucket in buckets:
            if len(picked) >= slots:
                break
            if counts.get(bucket.key, 0) >= bucket.max_n:
                continue
            if take_matching(bucket):
                progressed = True

    def try_take(d: dict[str, Any]) -> bool:
        eid = _eid(d)
        if eid in picked_ids or len(picked) >= slots:
            return False
        if not _allowed(d):
            return False
        b = first_bucket(d)
        if b and counts.get(b.key, 0) >= b.max_n:
            return False
        _commit(d, b)
        return True

    # Phase 3: leftover slots still respect bucket max_n (no 4× triceps).
    for source in (work_pool, allowed_items):
        for d in source:
            if len(picked) >= slots:
                break
            try_take(d)

    return _split_into_blocks(
        picked,
        compound_n=compound_n,
        accessory_n=accessory_n,
        split_role=split_role,
        focus_slugs=focus_slugs,
    )


def quota_sort_key(
    split_role: str | None,
    item: Any,
    *,
    focus_slugs: frozenset[str] | None = None,
) -> tuple[int, int, int, int]:
    """Compounds first (heavy pattern), then isolation large → small."""
    d = _as_dict(item)
    key = normalize_split_role(split_role)
    role_rank = 0 if _role(d) == "compound" else 1
    pat = _pattern(d)
    pat_rank = _COMPOUND_PATTERN_RANK.get(key, {}).get(pat, 8) if role_rank == 0 else 0
    buckets = quotas_for_split(split_role, focus_slugs=focus_slugs)
    rank = len(buckets)
    for i, bucket in enumerate(buckets):
        if bucket.match(d):
            rank = i
            break
    else:
        muscle = _muscle(d)
        if muscle:
            for i, bucket in enumerate(buckets):
                if _bucket_is_focus(bucket, frozenset({muscle})):
                    rank = i
                    break
    try:
        eid = _eid(d)
    except (KeyError, TypeError, ValueError):
        eid = 0
    return (role_rank, pat_rank, rank, eid)


def sort_items_by_quota(
    split_role: str | None,
    items: list[Any],
    *,
    focus_slugs: frozenset[str] | None = None,
) -> list[Any]:
    return sorted(
        items,
        key=lambda x: quota_sort_key(split_role, x, focus_slugs=focus_slugs),
    )


def _contiguous_index_runs(idxs: list[int]) -> list[list[int]]:
    if not idxs:
        return []
    runs: list[list[int]] = [[idxs[0]]]
    for i in idxs[1:]:
        if i == runs[-1][-1] + 1:
            runs[-1].append(i)
        else:
            runs.append([i])
    return runs


def _interleave_push_pull(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    push = [d for d in items if family_of(_pattern(d)) == "push"]
    pull = [d for d in items if family_of(_pattern(d)) == "pull"]
    rest = [d for d in items if d not in push and d not in pull]
    out: list[dict[str, Any]] = []
    i = j = 0
    while i < len(push) or j < len(pull):
        if i < len(push):
            out.append(push[i])
            i += 1
        if j < len(pull):
            out.append(pull[j])
            j += 1
    return out + rest


def _push_group_rank(d: dict[str, Any]) -> int:
    """Push day order: chest, then shoulders, then triceps."""
    if _match_triceps(d):
        return 2
    if _match_push_shoulder(d):
        return 1
    if _match_chest(d):
        return 0
    return 3


def reorder_main_section_exercises(
    split_role: str | None,
    exercises: list[Any],
    meta_by_id: dict[int, Any],
    *,
    focus_slugs: frozenset[str] | None = None,
) -> list[Any]:
    """Keep warmup/cardio/cooldown; compact every main into one block before cardio."""
    if len(exercises) < 2:
        return exercises
    mains = [
        ex
        for ex in exercises
        if str(getattr(ex, "section", "") or "") == "main"
    ]
    others = [
        ex
        for ex in exercises
        if str(getattr(ex, "section", "") or "") != "main"
    ]
    if not mains:
        return list(exercises)

    def as_dict(ex: Any) -> dict[str, Any]:
        eid = int(getattr(ex, "exercise_id"))
        raw = meta_by_id.get(eid)
        if raw is None:
            return {"id": eid, "movement_role": "", "movement_pattern": "", "muscle": ""}
        d = _as_dict(raw)
        d["id"] = eid
        return d

    def item_key(ex: Any) -> tuple[int, int, int, int]:
        return quota_sort_key(split_role, as_dict(ex), focus_slugs=focus_slugs)

    key = normalize_split_role(split_role)
    if key == "push":
        def push_key(ex: Any) -> tuple[int, int, int]:
            d = as_dict(ex)
            role_rank = 0 if _role(d) == "compound" else 1
            try:
                eid = int(getattr(ex, "exercise_id"))
            except (TypeError, ValueError):
                eid = 0
            return (_push_group_rank(d), role_rank, eid)

        sorted_mains = sorted(mains, key=push_key)
    else:
        compounds = [ex for ex in mains if _role(as_dict(ex)) == "compound"]
        isolations = [ex for ex in mains if _role(as_dict(ex)) != "compound"]
        if key == "upper" and len(compounds) >= 2:
            compounds_sorted = _interleave_push_pull([as_dict(ex) for ex in compounds])
            id_order = [_eid(d) for d in compounds_sorted]
            by_id = {int(getattr(ex, "exercise_id")): ex for ex in compounds}
            compounds = [by_id[i] for i in id_order if i in by_id]
        else:
            compounds = sorted(compounds, key=item_key)
        isolations = sorted(isolations, key=item_key)
        sorted_mains = compounds + isolations
        if key in {"legs", "lower"}:
            calves = [ex for ex in sorted_mains if _is_calf_exercise(as_dict(ex))]
            rest = [ex for ex in sorted_mains if not _is_calf_exercise(as_dict(ex))]
            sorted_mains = rest + calves

    insert_at = 0
    for i, ex in enumerate(others):
        sec = str(getattr(ex, "section", "") or "")
        if sec == "warmup":
            insert_at = i + 1
        elif sec in {"cardio", "cooldown"}:
            break
    return others[:insert_at] + sorted_mains + others[insert_at:]


def _anchor_upper_compounds(
    picked: list[dict[str, Any]],
    compounds: list[dict[str, Any]],
    compound_n: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Fill Upper compound slots with 1 h_push + 1 pull before extra presses."""
    chosen: list[dict[str, Any]] = []
    seen: set[int] = set()

    def add(d: dict[str, Any] | None) -> None:
        if not d or len(chosen) >= compound_n:
            return
        eid = _eid(d)
        if eid in seen:
            return
        chosen.append(d)
        seen.add(eid)

    add(next((d for d in compounds if _pattern(d) == "h_push"), None))
    add(next((d for d in compounds if _pattern(d) == "h_pull"), None))
    add(next((d for d in picked if _pattern(d) == "h_pull"), None))
    add(next((d for d in compounds if _pattern(d) == "v_pull"), None))
    add(next((d for d in picked if _pattern(d) == "v_pull"), None))
    add(next((d for d in compounds if _pattern(d) == "v_push"), None))
    for d in compounds:
        add(d)
    leftover = [d for d in compounds if _eid(d) not in seen]
    return chosen, leftover


def _anchor_compound_slots(
    split_role: str | None,
    compounds: list[dict[str, Any]],
    compound_n: int,
    picked: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    key = normalize_split_role(split_role)
    if key == "upper" and compound_n >= 2:
        return _anchor_upper_compounds(picked, compounds, compound_n)
    slots = COMPOUND_PATTERN_SLOTS.get(key, ())
    chosen: list[dict[str, Any]] = []
    seen: set[int] = set()

    def add(d: dict[str, Any] | None) -> None:
        if not d or len(chosen) >= compound_n:
            return
        eid = _eid(d)
        if eid in seen:
            return
        chosen.append(d)
        seen.add(eid)

    for pat in slots:
        add(next((d for d in compounds if _pattern(d) == pat), None))
    for d in compounds:
        add(d)
    leftover = [d for d in compounds if _eid(d) not in seen]
    return chosen, leftover


def _split_into_blocks(
    picked: list[dict[str, Any]],
    *,
    compound_n: int,
    accessory_n: int,
    split_role: str | None = None,
    focus_slugs: frozenset[str] | None = None,
) -> tuple[list[int], list[int]]:
    compound_n = max(0, int(compound_n))
    accessory_n = max(0, int(accessory_n))
    compounds = sort_items_by_quota(
        split_role,
        [d for d in picked if _role(d) == "compound"],
        focus_slugs=focus_slugs,
    )
    isolations = sort_items_by_quota(
        split_role,
        [d for d in picked if _role(d) != "compound"],
        focus_slugs=focus_slugs,
    )

    compound_ids: list[int] = []
    leftover_compounds: list[dict[str, Any]] = []
    if compound_n >= 1 and compounds:
        anchored, leftover_compounds = _anchor_compound_slots(
            split_role, compounds, compound_n, picked
        )
        compound_ids = [_eid(d) for d in anchored]
    else:
        leftover_compounds = list(compounds)

    # Isolation first in accessory — do not dump leftover compounds ahead of flies.
    remaining = sort_items_by_quota(
        split_role, isolations, focus_slugs=focus_slugs
    ) + sort_items_by_quota(
        split_role, leftover_compounds, focus_slugs=focus_slugs
    )
    accessory_ids: list[int] = []
    used = set(compound_ids)
    for d in remaining:
        eid = _eid(d)
        if eid in used:
            continue
        if len(compound_ids) < compound_n:
            compound_ids.append(eid)
            used.add(eid)
        elif len(accessory_ids) < accessory_n:
            accessory_ids.append(eid)
            used.add(eid)

    leftover = [d for d in picked if _eid(d) not in used]
    for d in leftover:
        eid = _eid(d)
        if len(compound_ids) < compound_n:
            compound_ids.append(eid)
        elif len(accessory_ids) < accessory_n:
            accessory_ids.append(eid)

    return compound_ids[:compound_n], accessory_ids[:accessory_n]


def _bucket_counts(
    buckets: tuple[QuotaBucket, ...],
    picked_metas: list[dict[str, Any]],
) -> dict[str, int]:
    """Count each item into first matching bucket only (priority order)."""
    counts = {b.key: 0 for b in buckets}
    for d in picked_metas:
        for b in buckets:
            if b.match(d):
                counts[b.key] += 1
                break
    return counts


def quota_would_exceed_max(
    split_role: str | None,
    picked: list[Any],
    candidate: Any,
    *,
    focus_slugs: frozenset[str] | None = None,
) -> bool:
    """True if adding candidate would put its quota bucket over max_n."""
    if not uses_muscle_quotas(split_role):
        return False
    items = [_as_dict(x) for x in picked]
    cand = _as_dict(candidate)
    buckets = quotas_for_split(
        split_role, focus_slugs=focus_slugs, lift_slots=len(items) + 1
    )
    if not buckets:
        return False
    counts = _bucket_counts(buckets, items)
    for b in buckets:
        if b.match(cand):
            return counts.get(b.key, 0) >= b.max_n
    return False


def repair_muscle_quotas(
    day_blocks: list[dict[str, Any]],
    picks_by_block: dict[str, list[int]],
    *,
    split_role: str | None,
    focus_slugs: frozenset[str] | None = None,
) -> dict[str, list[int]]:
    """Swap accessories to satisfy unpaid bucket mins when candidates remain."""
    if not uses_muscle_quotas(split_role):
        return picks_by_block

    _REPAIR_KEYS = frozenset({"compound", "accessory", "resistance"})
    picks = {k: list(v) for k, v in picks_by_block.items()}
    lift_n = sum(len(picks.get(k) or []) for k in _REPAIR_KEYS)
    buckets = quotas_for_split(
        split_role, focus_slugs=focus_slugs, lift_slots=lift_n
    )
    if not buckets:
        return picks_by_block
    id_to_meta: dict[int, dict[str, Any]] = {}
    for block in day_blocks:
        if str(block.get("block_key")) not in _REPAIR_KEYS:
            continue
        for raw in block.get("shortlist") or []:
            d = _as_dict(raw)
            id_to_meta[_eid(d)] = d

    def picked_metas() -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for ids in picks.values():
            for eid in ids:
                if eid in id_to_meta:
                    out.append(id_to_meta[eid])
        return out

    def candidates(bucket: QuotaBucket, block_key: str | None = None) -> list[int]:
        used = {eid for ids in picks.values() for eid in ids}
        found: list[int] = []
        for block in day_blocks:
            key = str(block.get("block_key"))
            if key not in _REPAIR_KEYS:
                continue
            if block_key and key != block_key:
                continue
            for raw in block.get("shortlist") or []:
                d = _as_dict(raw)
                eid = _eid(d)
                if eid in used:
                    continue
                if bucket.match(d):
                    found.append(eid)
        found.sort(
            key=lambda eid: (
                0 if _role(id_to_meta.get(eid) or {}) == "isolation" else 1,
                eid,
            )
        )
        return found

    counts = _bucket_counts(buckets, picked_metas())
    if normalize_split_role(split_role) == "upper" and counts.get("v_pull", 0) >= 1:
        # Upper B uses pulldown; one compound pull covers the row min on 2-lift days.
        counts["h_pull"] = max(int(counts.get("h_pull") or 0), 1)
    key_order = {"accessory": 0, "resistance": 1, "compound": 2}

    def _swap_priority(bucket: QuotaBucket, meta: dict[str, Any]) -> int:
        """Lower = more willing to swap out. Paying the unpaid bucket is forbidden."""
        if bucket.match(meta):
            return 10_000
        role = _role(meta)
        fam = family_of(_pattern(meta))
        if bucket.key == "biceps":
            if _match_rear_delt(meta):
                return 0
            if role == "isolation" and not _match_back(meta):
                return 1
            if _match_back(meta) and role != "compound":
                return 4
            if _match_back(meta) and role == "compound":
                return 80
            return 3
        if bucket.key == "squat_quad":
            if fam == "hinge" and role == "isolation":
                return 0
            if fam == "hinge":
                return 2
            return 5
        if bucket.key == "h_push":
            if fam == "pull" and role == "isolation":
                return 0
            if _match_triceps(meta):
                return 0
            if fam == "pull":
                return 1
            return 5
        if bucket.key == "chest":
            if _match_triceps(meta):
                return 0
            if _match_push_shoulder(meta) and role == "isolation":
                return 4
            return 2
        if bucket.key == "shoulders":
            if _match_triceps(meta):
                return 0
            if _match_chest(meta) and role == "isolation":
                return 4
            return 2
        if role == "isolation":
            return 2
        if role == "compound":
            return 20
        return 10

    for bucket in buckets:
        while counts.get(bucket.key, 0) < bucket.min_n:
            best = None
            best_cand = None
            for key in ("accessory", "resistance", "compound"):
                ids = picks.get(key) or []
                cands = candidates(bucket, key)
                if not ids or not cands:
                    continue
                for i in range(len(ids) - 1, -1, -1):
                    meta = id_to_meta.get(ids[i])
                    if not meta:
                        continue
                    pri = _swap_priority(bucket, meta)
                    if pri >= 10_000:
                        continue
                    row = (pri, key_order[key], -i, key, i)
                    if best is None or row < best:
                        best = row
                        best_cand = cands[0]
            if best is None or best_cand is None:
                appended = False
                for key in ("accessory", "resistance"):
                    blk = next(
                        (b for b in day_blocks if str(b.get("block_key")) == key),
                        {},
                    )
                    max_n = int(blk.get("count_max") or 0)
                    cur = picks.get(key) or []
                    extra = candidates(bucket, key)
                    if max_n and len(cur) < max_n and extra:
                        picks.setdefault(key, []).append(extra[0])
                        counts = _bucket_counts(buckets, picked_metas())
                        appended = True
                        break
                if appended:
                    continue
                break
            _, _, _, swap_key, swap_idx = best
            picks[swap_key][swap_idx] = best_cand
            counts = _bucket_counts(buckets, picked_metas())

    # Trim buckets over max (e.g. 3× triceps on Push) by swapping into under-min / under-max.
    while True:
        over = next((b for b in buckets if counts.get(b.key, 0) > b.max_n), None)
        if over is None:
            break
        target = next((b for b in buckets if counts.get(b.key, 0) < b.min_n), None)
        if target is None:
            target = next(
                (
                    b
                    for b in buckets
                    if b.key != over.key and counts.get(b.key, 0) < b.max_n
                ),
                None,
            )
        if target is None:
            break
        cands = [
            eid
            for eid in candidates(target)
            if not over.match(id_to_meta.get(eid) or {})
        ]
        if not cands:
            break
        best = None
        for key in ("accessory", "resistance"):
            ids = picks.get(key) or []
            for i in range(len(ids) - 1, -1, -1):
                meta = id_to_meta.get(ids[i])
                if not meta or not over.match(meta):
                    continue
                pri = 0 if _role(meta) == "isolation" else 8
                row = (pri, key_order[key], -i, key, i)
                if best is None or row < best:
                    best = row
        if best is None:
            break
        _, _, _, swap_key, swap_idx = best
        picks[swap_key][swap_idx] = cands[0]
        counts = _bucket_counts(buckets, picked_metas())

    return picks
