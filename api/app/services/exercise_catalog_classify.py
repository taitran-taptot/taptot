"""Classify exercise venue, difficulty (1–4), and home-oriented movement roles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from app.services.exercise_movement_role import VALID_ROLES, infer_movement_role

VALID_VENUES = frozenset({"gym", "home", "both"})

DIFFICULTY_LABELS: dict[int, str] = {
    1: "Rất cơ bản",
    2: "Cơ bản",
    3: "Trung cấp",
    4: "Nâng cao",
}

# experience_level (UI/frame L1–L3) → allowed skill difficulties (max cap, easy always in for L2+)
DIFFICULTY_BANDS_BY_EXPERIENCE: dict[int, frozenset[int]] = {
    1: frozenset({1, 2}),
    2: frozenset({1, 2, 3}),
    3: frozenset({1, 2, 3, 4}),
}

# Preferred difficulty for scoring (still allow easier in-band)
TARGET_DIFFICULTY_BY_EXPERIENCE: dict[int, int] = {1: 2, 2: 2, 3: 3}

_GYM_EQ_KEYS: tuple[str, ...] = (
    "cable",
    "smith",
    "leg-press",
    "leg press",
    "hack",
    "machine",
    "may-",
    "máy",
    "barbell",
    "ta-don",
    "tạ đòn",
    "olympic",
    "rack",
    "squat-rack",
    "lat-pulldown",
    "pulldown",
    "pec-deck",
    "treadmill",
    "elliptical",
    "assault",
    "sled",
    "xe trượt",
    "xe truot",
)

_HOME_EQ_KEYS: tuple[str, ...] = (
    "bodyweight",
    "body-weight",
    "none",
    "no-equipment",
    "mat",
    "yoga",
    "tham",
    "không cần",
    "khong can",
)

_BOTH_EQ_KEYS: tuple[str, ...] = (
    "dumbbell",
    "ta-don-tay",
    "tạ đơn",
    "ta don",
    "kettlebell",
    "band",
    "resistance-band",
    "resistance-band-1",
    "resistance-band-2",
    "day-khang",
    "dây kháng",
    "pull-up-bar",
    "xà",
    "medicine-ball",
    "slam-ball",
    "ab-wheel",
)

_ADV_DIFF_KEYS: tuple[str, ...] = (
    "snatch",
    "clean and jerk",
    "muscle-up",
    "muscle up",
    "pistol",
    "handstand",
    "hspu",
    "planche",
    "front lever",
    "back lever",
    "dragon flag",
    "olympic",
)

_HARD_DIFF_KEYS: tuple[str, ...] = (
    "barbell",
    "tạ đòn",
    "pull-up",
    "pullup",
    "chin-up",
    "chinup",
    "deadlift",
    "romanian",
    "front squat",
    "back squat",
    "overhead press",
    "bench press",
    "turkish",
)

_EASY_DIFF_KEYS: tuple[str, ...] = (
    "knee",
    "gối",
    "assisted",
    "machine",
    "máy",
    "seated",
    "ngồi",
    "wall",
    "tường",
    "walk",
    "đi bộ",
    "march",
    "band pull-apart",
)

_CONDITIONING_KEYS: tuple[str, ...] = (
    "burpee",
    "jumping jack",
    "jumping-jack",
    "mountain climber",
    "high knee",
    "butt kick",
    "jump rope",
    "skipping",
    "battle rope",
    "hiit",
    "conditioning",
    "metcon",
    "shuttle",
    "bear crawl",
    "farmer carry",
    "sled",
    "thruster",
)


@dataclass(frozen=True)
class ClassifyResult:
    difficulty: int
    difficulty_label: str
    venue: str
    movement_role: str
    needs_review: bool
    reason: str = ""


def clamp_difficulty_1_4(value: Any) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = 2
    if n >= 5:
        return 4
    return max(1, min(4, n))


def difficulty_band_for_experience(experience_level: int) -> frozenset[int]:
    level = max(1, min(3, int(experience_level or 1)))
    return DIFFICULTY_BANDS_BY_EXPERIENCE[level]


def target_difficulty_for_experience(experience_level: int) -> int:
    level = max(1, min(3, int(experience_level or 1)))
    return TARGET_DIFFICULTY_BY_EXPERIENCE[level]


def _join_name(exercise: dict[str, Any]) -> str:
    return " ".join(
        str(exercise.get(k) or "") for k in ("name_vi", "name_en", "name", "slug")
    ).lower()


def _eq_blob(equipment: Iterable[dict[str, Any] | str] | None) -> str:
    if not equipment:
        return ""
    parts: list[str] = []
    for item in equipment:
        if isinstance(item, str):
            parts.append(item.lower())
            continue
        parts.append(str(item.get("slug") or "").lower())
        parts.append(str(item.get("name_vi") or "").lower())
        parts.append(str(item.get("name_en") or "").lower())
        parts.append(str(item.get("category") or "").lower())
    return " ".join(parts)


def infer_venue(
    exercise: dict[str, Any],
    equipment: Iterable[dict[str, Any] | str] | None = None,
) -> tuple[str, bool, str]:
    """Return (venue, needs_review, reason)."""
    name = _join_name(exercise)
    eq = _eq_blob(equipment)
    blob = f"{name} {eq}"

    has_eq_list = bool(equipment) and any(
        (isinstance(e, str) and e.strip())
        or (isinstance(e, dict) and (e.get("slug") or e.get("name_vi") or e.get("name_en")))
        for e in equipment  # type: ignore[union-attr]
    )

    gym_hit = any(k in blob for k in _GYM_EQ_KEYS)
    home_hit = any(k in blob for k in _HOME_EQ_KEYS) or (
        not has_eq_list
        and ("body" in blob or "trọng lượng cơ thể" in blob or "bodyweight" in blob)
    )
    both_hit = any(k in blob for k in _BOTH_EQ_KEYS)

    if "tại nhà" in name or "tai nha" in name or " home" in f" {name}":
        return "home", False, "name_home"
    if gym_hit and not both_hit and not home_hit:
        return "gym", False, "gym_equipment"
    if home_hit and not gym_hit:
        return "home", False, "home_or_bodyweight"
    if both_hit and not gym_hit:
        return "both", False, "portable_equipment"
    if gym_hit and both_hit:
        return "gym", False, "gym_plus_portable"
    if not has_eq_list:
        return "both", True, "no_equipment_link"
    return "both", True, "ambiguous_equipment"


def refine_difficulty(
    current: Any,
    exercise: dict[str, Any],
    equipment: Iterable[dict[str, Any] | str] | None = None,
) -> int:
    base = clamp_difficulty_1_4(current)
    name = _join_name(exercise)
    eq = _eq_blob(equipment)
    blob = f"{name} {eq}"

    if any(k in blob for k in _ADV_DIFF_KEYS):
        return 4
    if any(k in blob for k in _EASY_DIFF_KEYS) and base >= 3:
        return max(1, base - 1)
    if any(k in blob for k in _HARD_DIFF_KEYS):
        return max(base, 3)
    if any(k in blob for k in ("machine", "máy", "smith", "cable")) and base >= 3:
        return max(2, base - 1)
    return base


def is_conditioning_name(exercise: dict[str, Any]) -> bool:
    name = _join_name(exercise)
    return any(k in name for k in _CONDITIONING_KEYS)


def refine_movement_role(
    exercise: dict[str, Any],
    *,
    venue: str,
    current_role: str | None = None,
) -> str:
    role = (current_role or "").strip().lower()
    if role not in VALID_ROLES:
        role = infer_movement_role(exercise)

    if is_conditioning_name(exercise):
        return "conditioning"

    if venue == "home" and role in {"compound", "isolation"}:
        return "resistance"

    return role


def classify_exercise(
    exercise: dict[str, Any],
    equipment: Iterable[dict[str, Any] | str] | None = None,
) -> ClassifyResult:
    venue, needs_review, reason = infer_venue(exercise, equipment)
    difficulty = refine_difficulty(exercise.get("difficulty"), exercise, equipment)
    role = refine_movement_role(
        exercise,
        venue=venue,
        current_role=exercise.get("movement_role"),
    )
    if role not in VALID_ROLES:
        role = "isolation" if venue != "home" else "resistance"
        needs_review = True
        reason = f"{reason}|bad_role"

    return ClassifyResult(
        difficulty=difficulty,
        difficulty_label=DIFFICULTY_LABELS[difficulty],
        venue=venue,
        movement_role=role,
        needs_review=needs_review,
        reason=reason,
    )


def roles_for_block(
    block_role: str | None,
    *,
    location: str | None = None,
) -> frozenset[str] | None:
    """Expand session block movement_role for gym vs home shortlists."""
    role = (block_role or "").strip().lower()
    if not role:
        return None
    loc = (location or "gym").strip().lower()
    if loc == "home":
        if role in {"compound", "isolation", "resistance"}:
            return frozenset({"resistance", "compound", "isolation"})
        if role in {"cardio", "conditioning"}:
            return frozenset({"conditioning", "cardio"})
    if role == "resistance":
        return frozenset({"resistance", "compound", "isolation"})
    if role == "conditioning":
        return frozenset({"conditioning", "cardio"})
    return frozenset({role})


def venues_for_location(location: str | None, *, no_equipment: bool = False) -> frozenset[str]:
    loc = (location or "gym").strip().lower()
    if no_equipment or loc == "home":
        return frozenset({"home", "both"})
    if loc == "gym":
        return frozenset({"gym", "both"})
    return frozenset({"gym", "home", "both"})
