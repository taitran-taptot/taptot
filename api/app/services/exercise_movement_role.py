"""Classify exercises as compound / isolation / mobility / cardio."""

from __future__ import annotations

from typing import Any

VALID_ROLES = frozenset(
    {"compound", "isolation", "mobility", "cardio", "resistance", "conditioning"}
)

# True multi-joint lifts — checked before isolation / generic tokens.
_TRUE_COMPOUND_PHRASES: tuple[str, ...] = (
    "deadlift",
    "romanian",
    "rdl",
    "hip thrust",
    "leg press",
    "hack squat",
    "split squat",
    "bulgarian",
    "goblet squat",
    "front squat",
    "back squat",
    "overhead press",
    "shoulder press",
    "military press",
    "bench press",
    "chest press",
    "incline press",
    "decline press",
    "floor press",
    "lat pulldown",
    "pulldown",
    "pull-up",
    "pullup",
    "pull up",
    "chin-up",
    "chinup",
    "chin up",
    "seated row",
    "cable row",
    "barbell row",
    "dumbbell row",
    "bent over row",
    "t-bar row",
    "push-up",
    "pushup",
    "push up",
    "burpee",
    "clean and jerk",
    "power clean",
    "hang clean",
    "snatch",
    "thruster",
    "kettlebell swing",
    "turkish get",
    "farmer",
    "sled",
    "chống đẩy",
    "chong day",
    "ngồi xổm",
    "ngoi xom",
    "kéo xô",
    "keo xo",
    "kéo tạ chết",
    "keo ta chet",
    "chèo",
    "cheo",
    "đẩy ngực",
    "day nguc",
    "hít đất",
    "hit dat",
    "hít xà",
    "hit xa",
    "động tác toàn thân",
)

_COMPOUND_KEYS: tuple[str, ...] = _TRUE_COMPOUND_PHRASES + (
    "lunge",
    "squat",
    "row",
    "press",
    "dip",
)

_ISOLATION_KEYS: tuple[str, ...] = (
    "face pull",
    "lateral raise",
    "front raise",
    "rear delt",
    "pec deck",
    "cable fly",
    "chest fly",
    "leg extension",
    "leg curl",
    "hamstring curl",
    "calf raise",
    "wrist curl",
    "concentration curl",
    "hammer curl",
    "bicep curl",
    "biceps curl",
    "tricep extension",
    "triceps extension",
    "skull crusher",
    "kickback",
    "pushdown",
    "shrug",
    "crunch",
    "sit-up",
    "situp",
    "plank",
    "pallof",
    "ab wheel",
    "leg raise",
    "hip abduction",
    "hip adduction",
    "glute kickback",
    "ép ngực",
    "ep nguc",
    "ép vai",
    "ep vai",
    "flye",
    "fly",
    "curl",
    "raise",
    "extension",
    "cuốn tay",
    "cuon tay",
    "dang vai",
    "dang tay",
    "đá chân",
    "da chan",
    "bắp chân",
    "bap chan",
    "gập bụng",
    "gap bung",
    "duỗi chân",
    "duoi chan",
    "cuốn đùi",
)


def infer_movement_role(exercise: dict[str, Any]) -> str:
    """Infer movement_role from exercise_type + names."""
    et = str(exercise.get("exercise_type") or "main").lower().strip()
    if et in ("warmup", "cooldown"):
        return "mobility"
    if et == "cardio":
        return "cardio"

    name = " ".join(
        str(exercise.get(k) or "") for k in ("name_vi", "name_en", "name", "slug")
    ).lower()

    if any(k in name for k in _TRUE_COMPOUND_PHRASES):
        if any(k in name for k in ("curl", "raise", "fly", "flye", "kickback", "shrug")):
            if not any(
                k in name
                for k in (
                    "bench press",
                    "overhead press",
                    "shoulder press",
                    "military press",
                    "chest press",
                    "leg press",
                    "incline press",
                    "decline press",
                )
            ):
                return "isolation"
        return "compound"

    if any(k in name for k in _ISOLATION_KEYS):
        return "isolation"

    if any(k in name for k in _COMPOUND_KEYS):
        if any(k in name for k in _ISOLATION_KEYS):
            return "isolation"
        return "compound"

    return "isolation"
