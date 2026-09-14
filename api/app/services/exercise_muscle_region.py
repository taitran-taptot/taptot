"""Rule-based exercise → granular muscle region classification."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Confidence = Literal["high", "medium", "low"]

PARENT_DEFAULT_LEAF: dict[str, str] = {
    "chest": "chest-mid",
    "co-nguc": "chest-mid",
    "back": "back-middle",
    "co-lung": "back-middle",
    "shoulders": "shoulders-lateral",
    "shoulders-deltoids": "shoulders-lateral",
    "co-vai": "shoulders-lateral",
    "core": "core-upper",
    "co-bung": "core-upper",
    "quads": "quads",
    "co-dui-truoc": "quads",
    "hamstrings": "hamstrings",
    "co-dui-sau": "hamstrings",
    "glutes": "glutes",
    "co-mong": "glutes",
    "calves": "calves",
    "co-bap-chan": "calves",
    "biceps": "biceps",
    "co-tay-truoc": "biceps",
    "triceps": "triceps",
    "co-tay-sau": "triceps",
    "forearms": "forearms",
    "cardio": "cardio",
    "stretch": "stretch",
}

LEAF_SLUGS = frozenset(
    {
        "chest-upper",
        "chest-mid",
        "chest-lower",
        "back-lats",
        "back-middle",
        "back-lower",
        "shoulders-front",
        "shoulders-lateral",
        "shoulders-rear",
        "shoulders-traps",
        "core-upper",
        "core-lower",
        "core-obliques",
        *PARENT_DEFAULT_LEAF.values(),
    }
)

ARM_SLUGS = frozenset({"biceps", "co-tay-truoc", "triceps", "co-tay-sau"})
LEG_SLUGS = frozenset(
    {"quads", "co-dui-truoc", "hamstrings", "co-dui-sau", "glutes", "co-mong", "calves", "co-bap-chan"}
)
SHOULDER_SLUGS = frozenset({"shoulders", "shoulders-deltoids", "co-vai"})
BACK_SLUGS = frozenset({"back", "co-lung"})
CHEST_SLUGS = frozenset({"chest", "co-nguc"})
CORE_SLUGS = frozenset({"core", "co-bung", "abs", "waist"})


@dataclass(frozen=True)
class RegionClassification:
    new_slug: str
    rule: str
    confidence: Confidence


def _blob(name_vi: str | None, name_en: str | None) -> str:
    return f"{name_vi or ''} {name_en or ''}".strip().lower()


def _has(blob: str, *keys: str) -> bool:
    return any(k in blob for k in keys)


def _word(blob: str, token: str) -> bool:
    return re.search(rf"(?<![a-z]){re.escape(token)}(?![a-z])", blob) is not None


def _is_lat_pull(blob: str) -> bool:
    """Match lat/lats as whole word — not inside 'lateral'."""
    if _word(blob, "lats") or _word(blob, "lat"):
        return True
    return _has(blob, "kéo xô", "keo xo", "lat pulldown", "lat pull")


def _is_hamstring_curl(blob: str) -> bool:
    return _has(
        blob,
        "cuốn đùi sau",
        "cuon dui sau",
        "leg curl",
        "gập gối",
        "gap goi",
        "hamstring curl",
        "nordic curl",
        "nordic ham",
    )


def _is_wrist_forearm(blob: str) -> bool:
    """True only for isolated wrist/forearm work — not presses that rotate at the wrist."""
    if _has(
        blob,
        "xoay cổ tay",
        "xoay co tay",
        "arnold press",
        "tate press",
        "đẩy vai xoay",
        "day vai xoay",
        "ép tay sau",
        "ep tay sau",
    ):
        return False
    return _has(
        blob,
        "wrist curl",
        "wrist extension",
        "wrist roller",
        "cuốn cổ tay",
        "cuon co tay",
        "cuộn cổ tay",
        "duỗi cổ tay",
        "duoi co tay",
        "giãn cổ tay",
        "gian co tay",
        "forearm curl",
        "forearm",
        "cẳng tay",
        "cang tay",
    )


def _classify_push_up(blob: str) -> RegionClassification | None:
    if not _has(blob, "chống đẩy", "chong day", "push-up", "push up", "pushup"):
        return None
    if _has(blob, "chân trên", "chan tren", "chân cao", "feet elevated", "foot on"):
        return RegionClassification("chest-upper", "pushup_feet_elevated", "high")
    if _has(blob, "tay trên", "tay cao", "hands elevated", "hand on bench", "tay trên ghế"):
        return RegionClassification("chest-lower", "pushup_hands_elevated", "high")
    if _has(blob, "incline", "dốc lên", "doc len", "dốc cao"):
        return RegionClassification("chest-upper", "pushup_incline", "high")
    if _has(blob, "decline", "dốc xuống", "doc xuong", "dốc dưới"):
        return RegionClassification("chest-lower", "pushup_decline", "high")
    return RegionClassification("chest-mid", "pushup_flat", "high")


def classify_region_slug(
    *,
    name_vi: str | None = None,
    name_en: str | None = None,
    old_slug: str | None = None,
    movement_pattern: str | None = None,
    movement_role: str | None = None,
) -> RegionClassification:
    """Return target leaf slug for an exercise."""
    slug = str(old_slug or "").strip().lower()
    blob = _blob(name_vi, name_en)
    pattern = str(movement_pattern or "").strip().lower()

    if _has(blob, "giãn", "gian", "stretch") and "warm" not in blob:
        return RegionClassification("stretch", "stretch", "high")

    push = _classify_push_up(blob)
    if push:
        return push

    # --- Cardio rowing / steady state (before back row matching) ---
    if _has(
        blob,
        "chèo máy đều",
        "cheo may deu",
        "steady-state row",
        "rowing interval",
        "rowing sprint",
        "chèo thuyền",
        "cheo thuyen",
        "rower",
    ):
        return RegionClassification("cardio", "cardio_row", "high")

    # --- Lower back / erector (override stale leaf tags) ---
    if _has(
        blob,
        "thắt lưng",
        "that lung",
        "lower back",
        "hyperextension",
        "hyper extension",
        "duỗi lưng",
        "duoi lung",
        "superman",
        "back extension",
        "reverse hyper",
    ):
        return RegionClassification("back-lower", "back_lower_early", "high")

    # --- Hamstrings (before arm curl — 'cuốn đùi sau' is leg curl, not biceps) ---
    if slug in {"hamstrings", "co-dui-sau"} or _is_hamstring_curl(blob) or _has(
        blob,
        "hamstring",
        "đùi sau",
        "dui sau",
        "romanian",
        "rdl",
        "good morning",
        "gập hông",
        "gap hong",
    ):
        if _has(blob, "duỗi lưng", "duoi lung", "superman", "back extension", "reverse hyper"):
            return RegionClassification("back-lower", "back_lower_extension", "high")
        if _has(blob, "từ đất", "tu dat", "deadlift") and not _has(blob, "romanian", "rdl", "gập hông", "gap hong"):
            return RegionClassification("back-lower", "back_lower_deadlift", "high")
        return RegionClassification("hamstrings", "leg_hamstrings", "high")

    # --- Forearms (before biceps — wrist curl is not biceps) ---
    if _is_wrist_forearm(blob):
        return RegionClassification("forearms", "arm_forearms", "high")

    # --- Back rows (before arm slug default — row machine is not biceps) ---
    if _has(blob, "chèo", "cheo") and not _has(
        blob, "chèo máy đều", "cheo may deu", "rowing interval", "rowing sprint", "chèo thuyền", "cheo thuyen"
    ):
        return RegionClassification("back-middle", "back_row_early", "high")

    # --- Arms ---
    _is_arm_curl = slug in ARM_SLUGS or _has(
        blob, "curl", "cuốn", "cuon", "biceps", "tay trước", "tay truoc", "hammer"
    )
    if _is_arm_curl and not _has(
        blob,
        "đẩy vai",
        "day vai",
        "arnold",
        "overhead press",
        "ohp",
        "military press",
        "dang vai",
        "dang tay",
        "lateral raise",
    ):
        if _is_hamstring_curl(blob):
            return RegionClassification("hamstrings", "leg_hamstrings_from_curl", "high")
        if _is_wrist_forearm(blob):
            return RegionClassification("forearms", "arm_forearms_from_curl", "high")
        if slug in {"triceps", "co-tay-sau"} or _has(
            blob, "triceps", "pushdown", "extension", "tay sau", "skull", "kickback"
        ):
            if _has(blob, "curl", "cuốn", "cuon", "biceps") and not _has(blob, "tay sau", "triceps"):
                return RegionClassification("biceps", "arm_biceps", "high")
            return RegionClassification("triceps", "arm_triceps", "high")
        return RegionClassification("biceps", "arm_biceps", "high")

    if slug in {"triceps", "co-tay-sau"} or _has(
        blob, "triceps", "pushdown", "push down", "tay sau", "skull crusher"
    ):
        return RegionClassification("triceps", "arm_triceps", "high")

    # --- Shoulders (before back) ---
    if _has(
        blob,
        "nhún vai",
        "nhun vai",
        "shrug",
        "cầu vai",
        "cau vai",
        "kéo vai",
        "keo vai",
        "upright row",
        "neck extension",
        "kéo dài cổ",
        "keo dai co",
    ):
        return RegionClassification("shoulders-traps", "shoulder_traps", "high")

    if _has(
        blob,
        "face pull",
        "về mặt",
        "ve mat",
        "xoay ngoài",
        "xoay ngoai",
        "xoay trong",
        "external rotation",
        "internal rotation",
        "bả vai",
        "ba vai",
        "reverse fly",
        "reverse flye",
    ):
        return RegionClassification("shoulders-rear", "shoulder_rear_early", "high")

    if (
        slug in SHOULDER_SLUGS
        or pattern == "v_push"
        or _has(
            blob,
            "dang vai",
            "dang tay",
            "đá vai",
            "da vai",
            "lateral raise",
            "side raise",
            "front raise",
            "đẩy vai",
            "day vai",
            "overhead press",
            "ohp",
            "military press",
        )
    ):
        if _has(
            blob,
            "rear",
            "sau vai",
            "face pull",
            "bả vai",
            "ba vai",
            "reverse fly",
            "reverse flye",
        ):
            return RegionClassification("shoulders-rear", "shoulder_rear", "high")
        if _has(
            blob,
            "lateral",
            "dang vai",
            "dang tay",
            "đá vai",
            "da vai",
            "side raise",
            "giữa",
            "giua",
        ):
            return RegionClassification("shoulders-lateral", "shoulder_lateral", "high")
        if _has(
            blob,
            "overhead",
            "ohp",
            "military",
            "front raise",
            "đẩy vai",
            "day vai",
            "trước",
            "truoc",
            "press",
        ):
            return RegionClassification("shoulders-front", "shoulder_front", "high")
        return RegionClassification("shoulders-lateral", "shoulder_default", "medium")

    # --- Core lower (before back pull patterns catch hanging raises) ---
    if _has(
        blob,
        "nâng gối",
        "nang goi",
        "knee raise",
        "chân chạm",
        "chan cham",
        "leg raise",
        "giơ chân",
        "gio chan",
        "giơ tay chân",
        "gio tay chan",
        "dead bug",
        "reverse crunch",
        "bụng dưới",
        "bung duoi",
        "flutter",
        "dragon flag",
    ) and _has(blob, "treo", "xà", "xa", "hanging", "ghế", "ghe", "leo núi", "leo nui"):
        return RegionClassification("core-lower", "core_lower_early", "high")

    # --- Calves ---
    if slug in {"calves", "co-bap-chan"} or _has(
        blob, "bắp chân", "bap chan", "calf raise", "nhón bắp", "nhon bap", "donkey calf", "soleus", " gastroc"
    ):
        return RegionClassification("calves", "leg_calves", "high")

    # --- Quads (before glutes) ---
    if slug in {"quads", "co-dui-truoc"} or _has(
        blob, "quad", "đùi trước", "dui truoc", "squat", "lunge", "chùng chân", "chung chan", "leg press", "ngồi xổm"
    ):
        if _has(blob, "bắp chân", "bap chan", "calf"):
            return RegionClassification("calves", "leg_calves_from_name", "high")
        return RegionClassification("quads", "leg_quads", "high")

    # --- Glutes ---
    if slug in {"glutes", "co-mong"} or _has(
        blob,
        "mông",
        "mong ",
        "glute",
        "hip thrust",
        "frog pump",
        "bơm mông",
        "bom mong",
        "cầu mông",
        "cau mong",
        "kickback",
        "đá mông",
        "da mong",
    ):
        if _has(blob, "hamstring", "đùi sau", "dui sau", "glute-ham", "glute ham"):
            return RegionClassification("hamstrings", "leg_hamstrings", "medium")
        return RegionClassification("glutes", "leg_glutes", "high")

    # --- Chest ---
    if slug in CHEST_SLUGS or (pattern == "h_push" and _has(blob, "ngực", "nguc", "chest", "pec", "fly")):
        if _has(blob, "incline", "dốc lên", "doc len", "dốc cao", "upper chest"):
            return RegionClassification("chest-upper", "chest_incline", "high")
        if _has(blob, "decline", "dốc xuống", "doc xuong", "dốc dưới", "dip"):
            return RegionClassification("chest-lower", "chest_decline", "high")
        if _has(blob, "fly", "ép ngực", "ep nguc", "pec deck", "crossover"):
            if _has(blob, "incline", "dốc lên", "doc len"):
                return RegionClassification("chest-upper", "chest_fly_incline", "medium")
            if _has(blob, "decline", "dốc xuong", "dốc xuống"):
                return RegionClassification("chest-lower", "chest_fly_decline", "medium")
            return RegionClassification("chest-mid", "chest_fly", "medium")
        if _has(blob, "bench", "flat", "press", "đẩy ngực", "day nguc"):
            return RegionClassification("chest-mid", "chest_flat", "high")
        return RegionClassification("chest-mid", "chest_default", "low")

    # --- Core (lower/obliques before upper default) ---
    if not _has(blob, "deadlift", "clean and press", "clean & press") and (
        slug in CORE_SLUGS
        or pattern == "core"
        or _has(blob, "bụng", "bung", "abs", "core", "plank", "chống người", "chong nguoi")
    ):
        if _has(
            blob,
            "oblique",
            "nghiêng",
            "nghien",
            "twist",
            "wood chop",
            "chẻ gỗ",
            "che go",
            "side bend",
            "russian",
            "xoay người",
            "xoay nguoi",
            "cối xay",
            "coi xay",
            "windmill",
        ):
            return RegionClassification("core-obliques", "core_obliques", "high")
        elif _has(
            blob,
            "nâng gối",
            "nang goi",
            "knee raise",
            "chân chạm",
            "chan cham",
            "leg raise",
            "giơ chân",
            "gio chan",
            "hanging",
            "treo",
            "reverse crunch",
            "bụng dưới",
            "bung duoi",
            "dead bug",
            "giơ tay chân",
            "gio tay chan",
            "flutter",
            "dragon flag",
            "leo núi",
            "leo nui",
        ):
            return RegionClassification("core-lower", "core_lower", "high")
        elif _has(blob, "crunch", "sit-up", "sit up", "bụng trên", "bung tren", "gập bụng", "gap bung"):
            return RegionClassification("core-upper", "core_upper", "high")
        elif _has(blob, "plank", "chống người", "chong nguoi"):
            return RegionClassification("core-upper", "core_upper", "high")
        elif slug in CORE_SLUGS or pattern == "core":
            return RegionClassification("core-upper", "core_default", "low")

    if _has(blob, "clean and press", "clean & press", "cối xay và đẩy"):
        return RegionClassification("shoulders-front", "shoulder_clean_press", "medium")

    if _has(blob, "deadlift không tạ", "deadlift khong ta", "deadlift (mô phỏng)", "mo phong"):
        return RegionClassification("back-lower", "back_lower_sim", "medium")

    # --- Back (strict) ---
    is_back = slug in BACK_SLUGS or pattern in {"h_pull", "v_pull"} or _has(
        blob, "chèo", "cheo", "row", "pulldown", "pull-up", "pull up", "pullup", "chin-up", "chin up"
    )
    if is_back or (_is_lat_pull(blob) and not _has(blob, "dang tay", "lateral")):
        if _has(
            blob,
            "duỗi lưng",
            "duoi lung",
            "superman",
            "back extension",
            "reverse hyper",
        ):
            return RegionClassification("back-lower", "back_lower", "high")
        if _has(blob, "chèo", "cheo", "row") and not _has(
            blob, "kéo xô", "keo xo", "pulldown", "pull up", "pullup", "hít xà", "hit xa", "lat pulldown"
        ):
            return RegionClassification("back-middle", "back_row", "high")
        if _has(
            blob,
            "pulldown",
            "pull-up",
            "pull up",
            "pullup",
            "chin",
            "kéo xô",
            "keo xo",
            "hít xà",
            "hit xa",
        ) or _is_lat_pull(blob):
            return RegionClassification("back-lats", "back_lats", "high")
        if slug in BACK_SLUGS or pattern in {"h_pull", "v_pull"}:
            return RegionClassification("back-middle", "back_default", "medium")

    # --- Stale leaf overrides ---
    if slug.startswith("back-"):
        if _has(blob, "chèo", "cheo", "row") and not _has(
            blob, "kéo xô", "keo xo", "pulldown", "pull up", "pullup", "hít xà", "hit xa"
        ):
            return RegionClassification("back-middle", "back_row_override", "high")
        if _has(blob, "kéo xô", "keo xo", "pulldown", "pull up", "pullup", "hít xà", "hit xa", "lat pulldown"):
            return RegionClassification("back-lats", "back_lats_override", "high")

    if slug.startswith("core-"):
        if _has(blob, "nâng gối", "chân chạm", "giơ tay chân", "treo", "leo núi"):
            return RegionClassification("core-lower", "core_lower_override", "high")

    if slug == "forearms" and not _is_wrist_forearm(blob):
        if _has(blob, "arnold", "đẩy vai", "day vai", "overhead press", "ohp", "military"):
            return RegionClassification("shoulders-front", "forearm_stale_shoulder", "high")
        if _has(blob, "tate", "ép tay sau", "ep tay sau", "triceps"):
            return RegionClassification("triceps", "forearm_stale_triceps", "high")

    if slug in PARENT_DEFAULT_LEAF:
        return RegionClassification(PARENT_DEFAULT_LEAF[slug], "parent_default", "medium")

    if slug in LEAF_SLUGS:
        return RegionClassification(slug, "already_leaf", "low")

    return RegionClassification(
        PARENT_DEFAULT_LEAF.get(slug, slug or "chest-mid"),
        "unknown_fallback",
        "low",
    )
