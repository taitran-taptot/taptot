"""Classify exercises into movement patterns (push/pull planes, squat, hinge, core)."""

from __future__ import annotations

from typing import Any

VALID_PATTERNS = frozenset(
    {"h_push", "h_pull", "v_push", "v_pull", "squat", "hinge", "core", "other"}
)

# Isolation accessories — checked before plane rules so fly/raise never fill press slots.
_ISOLATION_OTHER_KEYS: tuple[str, ...] = (
    "lateral raise",
    "front raise",
    "chest fly",
    "cable fly",
    "pec deck",
    "flye",
    "fly",
    "bicep curl",
    "biceps curl",
    "hammer curl",
    "concentration curl",
    "wrist curl",
    "leg extension",
    "leg curl",
    "hamstring curl",
    "calf raise",
    "pushdown",
    "kickback",
    "skull crusher",
    "tricep extension",
    "triceps extension",
    "hip abduction",
    "hip adduction",
    "glute kickback",
    "ép ngực",
    "ep nguc",
    "dang vai",
    "dang tay",
    "cuốn tay",
    "cuon tay",
    "cuốn bắp",
    "bắp chân",
    "bap chan",
    "duỗi chân",
    "duoi chan",
)

# Soft fallback when name keywords miss: muscle_groups.slug → pattern
# Canonical EN + legacy VI aliases.
_MUSCLE_SLUG_PATTERN: dict[str, str] = {
    "chest": "h_push",
    "co-nguc": "h_push",
    "triceps": "h_push",
    "co-tay-sau": "h_push",
    "shoulders": "v_push",
    "shoulders-deltoids": "v_push",
    "co-vai": "v_push",
    "back": "h_pull",
    "co-lung": "h_pull",
    # Isolation arms must not satisfy pull coverage (curl ≠ row).
    "biceps": "other",
    "co-tay-truoc": "other",
    "quads": "squat",
    "co-dui-truoc": "squat",
    "upper-legs": "squat",
    "hamstrings": "hinge",
    "co-dui-sau": "hinge",
    "glutes": "hinge",
    "co-mong": "hinge",
    "core": "core",
    "co-bung": "core",
    "waist": "core",
    "stretch": "other",
}

# Ordered checks: more specific first (see infer_movement_pattern).
_RULES: list[tuple[str, tuple[str, ...]]] = [
    (
        "h_push",
        (
            "chest dip",
            "ring dip",
            "bar dip",
            "bench dip",
            "triceps dip",
            "xà kép",
            "xa kep",
            "hít xà kép",
            "hit xa kep",
            "hít ghế",
            "hit ghe",
            "pike dip",
            "hít kiểu pike",
            "hít ring",
            "hit ring",
            "dip",
        ),
    ),
    (
        "v_pull",
        (
            "lat pulldown",
            "pulldown",
            "pull-up",
            "pullup",
            "pull up",
            "chin-up",
            "chinup",
            "chin up",
            "kéo xô",
            "keo xo",
            "hít xà",
            "hit xa",
            "hít ring",
            "hit ring",
            "treo xà",
        ),
    ),
    (
        "h_pull",
        (
            "face pull",
            "seated cable",
            "cable row",
            "barbell row",
            "dumbbell row",
            "bent over row",
            "t-bar row",
            "seated row",
            "row",
            "chèo",
            "cheo",
            "kéo tạ đơn qua đầu",
            "kéo dây tách",
            "keo day tach",
            "band pull-apart",
            "kéo tạ từ giá",
            "siết bả vai",
            "xoay ngoài vai",
            "xoay trong vai",
            "rear delt",
            "superman",
            "kiểu bơi",
            "chữ y",
            "chu y",
            "chữ t",
            "chu t",
            "chữ w",
            "chu w",
        ),
    ),
    (
        "v_push",
        (
            "pike push-up",
            "pike pushup",
            "pike push up",
            "elevated pike",
            "chống đẩy kiểu pike",
            "chong day kieu pike",
            "chống đẩy pike",
            "chong day pike",
            "overhead press",
            "shoulder press",
            "military press",
            "ohp",
            "ép vai",
            "ep vai",
            "đẩy vai",
            "day vai",
            "đẩy tạ trên đầu",
            "day ta tren dau",
            "đẩy tạ đơn trên đầu",
            "arnold",
            "landmine",
            "trên đầu có bật",
            "đẩy tạ sau gáy",
            "push press",
            "ấm đáy",
            "am day",
        ),
    ),
    (
        "h_push",
        (
            "bench press",
            "chest press",
            "incline press",
            "decline press",
            "floor press",
            "push-up",
            "pushup",
            "push up",
            "dip",
            "đẩy ngực",
            "day nguc",
            "chống đẩy",
            "chong day",
            "hít đất",
            "hit dat",
            "jm press",
            "đẩy jm",
        ),
    ),
    (
        "squat",
        (
            "hack squat",
            "split squat",
            "goblet squat",
            "front squat",
            "back squat",
            "leg press",
            "lunge",
            "squat",
            "ngồi xổm",
            "ngoi xom",
            "đùi trước",
            "dui truoc",
            "step-up",
            "step up",
        ),
    ),
    (
        "hinge",
        (
            "romanian",
            "deadlift",
            "rdl",
            "hip thrust",
            "good morning",
            "back extension",
            "glute bridge",
            "kéo tạ chết",
            "keo ta chet",
            "mông",
            "mong",
            "đùi sau",
            "dui sau",
            "kickback mông",
            "hyperextension",
        ),
    ),
    (
        "core",
        (
            "pallof",
            "ab wheel",
            "plank",
            "crunch",
            "sit-up",
            "situp",
            "cable crunch",
            "leg raise",
            "gập bụng",
            "gap bung",
            "core",
            "trồng chuối",
            "trong chuoi",
            "hollow",
            "dead bug",
            "russian twist",
            "woodchop",
        ),
    ),
]


def infer_movement_pattern(exercise: dict[str, Any]) -> str:
    """Infer movement_pattern from names (+ soft type / muscle slug hints)."""
    et = str(exercise.get("exercise_type") or "main").lower().strip()
    name = " ".join(
        str(exercise.get(k) or "") for k in ("name_vi", "name_en", "name", "slug")
    ).lower()

    if et in ("warmup", "cooldown", "cardio") and not name.strip():
        return "other"

    if any(k in name for k in _ISOLATION_OTHER_KEYS):
        if not any(
            k in name
            for k in (
                "bench press",
                "chest press",
                "overhead press",
                "shoulder press",
                "military press",
                "leg press",
                "floor press",
                "đẩy ngực",
                "day nguc",
                "đẩy vai",
                "day vai",
            )
        ):
            return "other"

    for pattern, keys in _RULES:
        if any(k in name for k in keys):
            return pattern

    if et in ("warmup", "cooldown", "cardio"):
        return "other"

    # Soft fallback: primary muscle group when name keywords miss
    muscle = str(
        exercise.get("muscle_slug")
        or exercise.get("muscle")
        or exercise.get("muscle_group_slug")
        or ""
    ).strip().lower()
    if muscle in _MUSCLE_SLUG_PATTERN:
        return _MUSCLE_SLUG_PATTERN[muscle]

    return "other"
