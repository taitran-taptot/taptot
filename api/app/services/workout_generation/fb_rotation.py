"""Full Body A/B session variants so 3 FB days are not identical copies."""

from __future__ import annotations

from app.services.workout_generation.split_map import normalize_split_role

FB_A = "fb_a"
FB_B = "fb_b"
FB_ROLES = frozenset({"fb", FB_A, FB_B})


def is_full_body_role(split_role: str | None) -> bool:
    return normalize_split_role(split_role) in FB_ROLES


def fb_variant_for_offset(fb_offset: int) -> str:
    """Even slots → A, odd → B. Three-day week becomes A / B / A."""
    return FB_A if int(fb_offset) % 2 == 0 else FB_B


def effective_pick_role(split_role: str | None, *, fb_offset: int | None = None) -> str:
    key = normalize_split_role(split_role)
    if key in FB_ROLES and fb_offset is not None:
        return fb_variant_for_offset(fb_offset)
    return key


def fb_session_title(variant: str, *, day_number: int) -> str:
    letter = "A" if variant == FB_A else "B"
    return f"Buổi {day_number}: Full Body {letter}"
