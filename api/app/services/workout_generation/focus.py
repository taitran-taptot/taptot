"""Map UI focus_areas → muscle slugs."""

from __future__ import annotations

from app.services.workout_generation.muscle_quotas import (
    BACK_SLUGS,
    BICEPS_SLUGS,
    CALF_SLUGS,
    CHEST_SLUGS,
    CORE_SLUGS,
    GLUTE_SLUGS,
    HINGE_MUSCLE_SLUGS,
    QUAD_SLUGS,
    SHOULDER_SLUGS,
    TRICEPS_SLUGS,
)

FOCUS_TO_SLUGS: dict[str, frozenset[str]] = {
    "eo": CORE_SLUGS,
    "bung": CORE_SLUGS,
    "nguc": CHEST_SLUGS,
    "vai": SHOULDER_SLUGS,
    "vai_thon": SHOULDER_SLUGS,
    "mong": GLUTE_SLUGS,
    "tay": BICEPS_SLUGS | TRICEPS_SLUGS,
    "tay_to": BICEPS_SLUGS | TRICEPS_SLUGS,
    "lung": BACK_SLUGS,
    "mo_lung": BACK_SLUGS,
    "chan": QUAD_SLUGS | HINGE_MUSCLE_SLUGS | CALF_SLUGS | GLUTE_SLUGS,
}

FOCUS_LABEL_VI: dict[str, str] = {
    "eo": "giảm mỡ bụng",
    "bung": "6 múi",
    "nguc": "ngực săn",
    "vai": "vai rộng",
    "vai_thon": "vai thon gọn",
    "mong": "mông đầy đặn",
    "tay": "tay thon gọn",
    "tay_to": "tay to",
    "lung": "lưng rộng",
    "mo_lung": "giảm mỡ lưng",
    "chan": "chân",
}

FOCUS_SHORTLIST_BONUS = 20


def focus_muscle_slugs(focus_areas: list[str] | None) -> frozenset[str]:
    slugs: set[str] = set()
    for raw in focus_areas or []:
        key = str(raw).strip().lower()
        slugs |= FOCUS_TO_SLUGS.get(key, frozenset())
    return frozenset(slugs)


def focus_labels_vi(focus_areas: list[str] | None) -> list[str]:
    out: list[str] = []
    for raw in focus_areas or []:
        key = str(raw).strip().lower()
        label = FOCUS_LABEL_VI.get(key)
        if label and label not in out:
            out.append(label)
    return out


def is_focus_muscle(muscle_slug: str | None, focus_slugs: frozenset[str]) -> bool:
    if not focus_slugs:
        return False
    return str(muscle_slug or "").strip().lower() in focus_slugs
