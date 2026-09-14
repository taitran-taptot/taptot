"""Validate / repair OpenAI block picks against shortlists and counts."""

from __future__ import annotations

from app.services.session_blocks import BlockSpec
from app.services.workout_generation.shortlist import ShortlistItem


def repair_block_picks(
    *,
    block: BlockSpec,
    picked_ids: list[int],
    shortlist: list[ShortlistItem],
    used_ids: set[int],
    fill_missing: bool = True,
    user_gear: set[str] | None = None,
) -> list[int]:
    """Return exercise ids in [count_min, count_max], subset of shortlist, preferring unused.

    When fill_missing is False (OpenAI path), only keep valid ids and trim — never
    invent replacements from the shortlist. ``user_gear`` (home + equipment) makes the
    fill prefer rows that use the selected gear before bodyweight rows.
    """
    if block.count_max <= 0:
        return []

    if user_gear:
        from app.services.workout_generation.home_gear_priority import sort_gear_first

        shortlist = sort_gear_first(list(shortlist), user_gear)
    allowed = {item.id: item for item in shortlist}
    cleaned: list[int] = []
    for eid in picked_ids:
        if eid in allowed and eid not in cleaned:
            cleaned.append(eid)

    target = block.count_max
    if block.is_optional and not cleaned and not shortlist:
        return []
    if block.is_optional and block.count_min == 0 and not cleaned:
        if not fill_missing:
            return []
        if shortlist:
            target = max(block.count_min, min(block.count_max, 1))
        else:
            return []

    cleaned = cleaned[: block.count_max]

    if not fill_missing:
        if not cleaned and block.is_optional:
            return []
        return cleaned[: block.count_max]

    # Fill from shortlist preferring unused
    pool = [i.id for i in shortlist if i.id not in cleaned]
    unused_first = [i for i in pool if i not in used_ids] + [i for i in pool if i in used_ids]
    for eid in unused_first:
        if len(cleaned) >= target:
            break
        cleaned.append(eid)

    # Trim to count_max
    cleaned = cleaned[: block.count_max]

    # Optional core/cardio may stay empty if still nothing
    if not cleaned and block.is_optional:
        return []

    # Enforce count_min when required
    if len(cleaned) < block.count_min and not block.is_optional:
        for eid in unused_first:
            if eid not in cleaned:
                cleaned.append(eid)
            if len(cleaned) >= block.count_min:
                break

    return cleaned[: block.count_max]
