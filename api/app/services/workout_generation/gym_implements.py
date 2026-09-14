"""Gym loaded implements vs calisthenics / bodyweight.

Used when location=gym and the user did not pick equipment: prefer barbell,
Smith, dumbbell, cable and machines over pike push-ups and other BW work.
"""

from __future__ import annotations

from collections.abc import Iterable

# Explicit catalog slugs (plus token match below for machines).
GYM_LOAD_SLUGS = frozenset(
    {
        "barbell",
        "smith-machine",
        "dumbbell",
        "kettlebell",
        "ez-bar",
        "ez-curl-bar",
        "trap-bar",
        "hex-bar",
        "functional-trainer",
        "cable",
        "lat-pulldown",
        "seated-row",
        "chest-press-machine",
        "shoulder-press-machine",
        "pec-deck",
        "pec-deck-butterfly",
        "leg-press",
        "hack-squat",
        "preacher-curl-bench",
        "t-bar-row",
        "landmine",
        "lying-leg-curl",
        "seated-leg-curl",
        "standing-calf-raise",
        "seated-calf-raise",
        "glute-kickback",
        "back-extension",
        "roman-chair",
        "hip-abductor",
        "hip-adductor",
        "may-leg-extension",
        "may-hip-thrust",
        "may-glute-drive",
    }
)

# Substrings on equipment.slug that count as loaded gym work.
_GYM_LOAD_TOKENS: tuple[str, ...] = (
    "smith",
    "barbell",
    "dumbbell",
    "kettlebell",
    "cable",
    "pulldown",
    "functional-trainer",
    "ez-bar",
    "trap-bar",
    "hex-bar",
    "landmine",
    "pec-deck",
    "leg-press",
    "hack-squat",
    "preacher",
    "chest-press",
    "shoulder-press",
    "seated-row",
    "t-bar",
    "tbar",
    "-machine",
    "machine-",
    "leg-curl",
    "leg-extension",
    "calf-raise",
    "glute-kickback",
    "back-extension",
    "roman-chair",
    "hip-abduct",
    "hip-adduct",
)

# Dip bars / rings / mats are gym-adjacent but not "standard loaded upper day".
_CALISTHENICS_SLUGS = frozenset(
    {
        "parallel-bars",
        "gymnastic-rings",
        "yoga-mat-exercise-mat",
        "yoga-mat",
        "pull-up-bar",
        "plyometric-box",
        "resistance-band",
        "resistance-band-1",
        "resistance-band-2",
        "jump-rope",
    }
)


def _norm(slug: str | None) -> str:
    return str(slug or "").strip().lower()


def is_gym_load_slug(slug: str | None) -> bool:
    s = _norm(slug)
    if not s or s in _CALISTHENICS_SLUGS:
        return False
    if s in GYM_LOAD_SLUGS:
        return True
    return any(tok in s for tok in _GYM_LOAD_TOKENS)


def has_gym_load(slugs: Iterable[str] | None) -> bool:
    return any(is_gym_load_slug(s) for s in (slugs or ()))
