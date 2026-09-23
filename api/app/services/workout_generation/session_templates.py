"""Standard session slot templates (Boostcamp/Hevy/PPL-style) filled from the catalog."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from app.services.workout_generation.muscle_quotas import (
    BACK_SLUGS,
    BICEPS_SLUGS,
    CALF_SLUGS,
    CHEST_SLUGS,
    CORE_SLUGS,
    GLUTE_SLUGS,
    HAMSTRING_SLUGS,
    HINGE_MUSCLE_SLUGS,
    PUSH_SHOULDER_SLUGS,
    QUAD_SLUGS,
    SHOULDER_SLUGS,
    TRICEPS_SLUGS,
    uses_muscle_quotas,
)
from app.services.workout_generation.split_map import (
    is_denied_for_split,
    muscle_hints_for_split,
    normalize_split_role,
)

TEMPLATE_ROLES = frozenset({"push", "pull", "legs", "lower", "upper", "fb", "fb_a", "fb_b"})
# Deterministic slot fill: prefer rows that use the user's home gear over bodyweight.
HOME_GEAR_SLOT_BONUS = 35

_COMPOUND_ROLES = frozenset({"compound", "resistance"})
_ISO_ROLES = frozenset({"isolation", "resistance"})
_FB_ROLES = frozenset({"compound", "isolation", "resistance"})

_COMPOUND_AVOID = (
    "fly",
    "flye",
    "raise",
    "curl",
    "pushdown",
    "kickback",
    "pec deck",
    "face pull",
    "skull",
    "ép ngực",
    "ep nguc",
    "lateral",
    "front raise",
)

_BAR_PREFER_NEEDLES = ("pull-up", "pullup", "chin", "hít xà", "hit xa")

# Home no-equip back compounds: table / backpack rows, not gym pulldown/bar.
_HOME_NO_EQUIP_BACK_PATTERNS = ("h_pull", "v_pull", "other", "core")
_HOME_NO_EQUIP_BACK_PREFER = (
    "table inverted",
    "backpack",
    "ba lô",
    "ba lo",
    "dưới bàn",
    "duoi ban",
    "kéo người dưới bàn",
    "keo nguoi duoi ban",
    "chèo ba lô",
    "cheo ba lo",
)
_CHEST_COMPOUND_KEYS = frozenset({"h_press", "extra_press"})
_CHEST_DECLINE_AVOID = ("decline", "dốc xuống", "doc xuong", "dốc dưới", "doc duoi", "dip")
_CHEST_TRICEPS_AVOID = (
    "tate",
    "skull",
    "extension",
    "pushdown",
    "kickback",
    "ép tay sau",
    "ep tay sau",
    "jm press",
)
_CHEST_L1_IMPLEMENT = ("machine", "máy", "chest press")
_CHEST_L2_IMPLEMENT = ("dumbbell", "barbell", "tạ đơn", "tạ đòn")
_CHEST_FLAT_PREFER = (
    "flat",
    "nằm",
    "bench",
    "chest press",
    "đẩy ngực",
    "day nguc",
    "push-up",
    "push up",
    "chống đẩy",
)
_CHEST_INCLINE_PREFER = ("incline", "dốc lên", "dốc cao", "doc len")


def _chest_implement_prefer(experience_level: int) -> tuple[str, ...]:
    if int(experience_level or 2) <= 1:
        return _CHEST_L1_IMPLEMENT
    return _CHEST_L2_IMPLEMENT


def _chest_compound_avoid() -> tuple[str, ...]:
    return _COMPOUND_AVOID + _CHEST_DECLINE_AVOID + _CHEST_TRICEPS_AVOID


def _catalog_blob(item: Any) -> str:
    if isinstance(item, dict):
        return " ".join(
            str(item.get(k) or "") for k in ("name_vi", "name_en", "name", "slug")
        ).lower()
    return " ".join(
        str(getattr(item, k, "") or "") for k in ("name_vi", "name_en", "name", "slug")
    ).lower()


def _catalog_muscle(item: Any) -> str:
    if isinstance(item, dict):
        raw = item.get("muscle") or item.get("muscle_slug")
    else:
        raw = getattr(item, "muscle_slug", None) or getattr(item, "muscle", None)
    return str(raw or "").strip().lower()


def is_decline_chest_compound(item: Any) -> bool:
    """True when a chest compound name is decline or dip (treated as decline)."""
    blob = _catalog_blob(item)
    if any(n in blob for n in ("decline", "dốc xuống", "doc xuong", "dốc dưới", "doc duoi")):
        return True
    return "dip" in blob


def is_triceps_press_imposter(item: Any) -> bool:
    """True when a press is triceps work (Tate, skull crusher, JM, …), not chest."""
    blob = _catalog_blob(item)
    if any(n in blob for n in _CHEST_TRICEPS_AVOID):
        return True
    return _catalog_muscle(item) in TRICEPS_SLUGS


def is_free_weight_chest_press(item: Any) -> bool:
    """Barbell/dumbbell chest press — not machine, decline, or triceps imposters."""
    if is_triceps_press_imposter(item) or is_decline_chest_compound(item):
        return False
    blob = _catalog_blob(item)
    impl = any(n in blob for n in _CHEST_L2_IMPLEMENT)
    press = any(
        n in blob
        for n in (
            "chest press",
            "bench",
            "đẩy ngực",
            "day nguc",
            "push-up",
            "push up",
            "chống đẩy",
            "press",
        )
    )
    return impl and press


def _strip_bar_prefers(prefer: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        p for p in prefer if not any(n in p.lower() for n in _BAR_PREFER_NEEDLES)
    )


def _maybe_strip_bar_slots(slots: list[ExerciseSlot], *, allow_bar_moves: bool) -> list[ExerciseSlot]:
    if allow_bar_moves:
        return slots
    return [
        ExerciseSlot(
            key=s.key,
            block=s.block,
            roles=s.roles,
            patterns=s.patterns,
            muscles=s.muscles,
            prefer=_strip_bar_prefers(s.prefer),
            avoid=s.avoid,
            required=s.required,
            relax_muscle=s.relax_muscle,
        )
        for s in slots
    ]


@dataclass(frozen=True)
class ExerciseSlot:
    key: str
    block: str
    roles: frozenset[str]
    patterns: tuple[str, ...]
    muscles: frozenset[str]
    prefer: tuple[str, ...] = ()
    avoid: tuple[str, ...] = ()
    required: bool = True
    relax_muscle: bool = True


def uses_session_templates(split_role: str | None) -> bool:
    key = normalize_split_role(split_role)
    return key in TEMPLATE_ROLES or uses_muscle_quotas(split_role)


def _slot(
    key: str,
    *,
    block: str,
    roles: frozenset[str],
    patterns: tuple[str, ...],
    muscles: frozenset[str],
    prefer: tuple[str, ...] = (),
    avoid: tuple[str, ...] = (),
    relax_muscle: bool = True,
) -> ExerciseSlot:
    return ExerciseSlot(
        key=key,
        block=block,
        roles=roles,
        patterns=patterns,
        muscles=muscles,
        prefer=prefer,
        avoid=avoid,
        relax_muscle=relax_muscle,
    )


def _compound_block(location: str) -> str:
    return "resistance" if location == "home" else "compound"


def _iso_block(location: str) -> str:
    return "resistance" if location == "home" else "accessory"


def _push_compounds(block: str, *, experience_level: int = 2) -> list[ExerciseSlot]:
    impl = _chest_implement_prefer(experience_level)
    chest_avoid = _chest_compound_avoid()
    return [
        _slot(
            "h_press",
            block=block,
            roles=_COMPOUND_ROLES,
            patterns=("h_push",),
            muscles=CHEST_SLUGS,
            prefer=impl + _CHEST_FLAT_PREFER,
            avoid=chest_avoid,
        ),
        _slot(
            "v_press",
            block=block,
            roles=_COMPOUND_ROLES,
            patterns=("v_push",),
            muscles=PUSH_SHOULDER_SLUGS,
            prefer=("overhead", "shoulder press", "military", "ohp", "đẩy vai", "pike"),
            avoid=_COMPOUND_AVOID,
        ),
        _slot(
            "extra_press",
            block=block,
            roles=_COMPOUND_ROLES,
            patterns=("h_push",),
            muscles=CHEST_SLUGS,
            prefer=impl + _CHEST_INCLINE_PREFER,
            avoid=chest_avoid,
        ),
    ]


def _push_isos(block: str) -> list[ExerciseSlot]:
    return [
        _slot(
            "chest_iso",
            block=block,
            roles=_ISO_ROLES,
            patterns=("h_push", "other"),
            muscles=CHEST_SLUGS,
            prefer=("fly", "pec", "ép ngực", "ep nguc"),
        ),
        _slot(
            "push_arm_iso",
            block=block,
            roles=_ISO_ROLES,
            patterns=("h_push", "v_push", "other"),
            muscles=TRICEPS_SLUGS | PUSH_SHOULDER_SLUGS,
            prefer=("pushdown", "extension", "kickback", "lateral", "raise", "đá tay", "dang vai"),
        ),
        _slot(
            "push_extra_iso",
            block=block,
            roles=_ISO_ROLES,
            patterns=("h_push", "v_push", "other"),
            muscles=CHEST_SLUGS | TRICEPS_SLUGS | PUSH_SHOULDER_SLUGS,
            prefer=("fly", "raise", "pushdown", "kickback", "đá tay"),
        ),
        _slot(
            "push_finisher_iso",
            block=block,
            roles=_ISO_ROLES,
            patterns=("h_push", "v_push", "other"),
            muscles=CHEST_SLUGS | TRICEPS_SLUGS | PUSH_SHOULDER_SLUGS,
        ),
    ]


def _pull_compounds(block: str) -> list[ExerciseSlot]:
    return [
        _slot(
            "v_pull",
            block=block,
            roles=_COMPOUND_ROLES,
            patterns=("v_pull",),
            muscles=BACK_SLUGS,
            prefer=("pulldown", "pull-up", "pullup", "pull up", "chin", "kéo xô", "hít xà"),
            avoid=_COMPOUND_AVOID,
        ),
        _slot(
            "h_pull",
            block=block,
            roles=_COMPOUND_ROLES,
            patterns=("h_pull",),
            muscles=BACK_SLUGS,
            prefer=("row", "chèo", "cheo"),
            avoid=_COMPOUND_AVOID,
        ),
        _slot(
            "extra_pull",
            block=block,
            roles=_COMPOUND_ROLES,
            patterns=("v_pull", "h_pull"),
            muscles=BACK_SLUGS,
            prefer=("row", "pulldown", "pull"),
            avoid=_COMPOUND_AVOID,
        ),
    ]


def _pull_isos(block: str) -> list[ExerciseSlot]:
    return [
        _slot(
            "rear_delt",
            block=block,
            roles=_ISO_ROLES,
            patterns=("h_pull", "other"),
            muscles=SHOULDER_SLUGS,
            prefer=("face pull", "rear", "bả vai", "pull-apart"),
        ),
        _slot(
            "biceps",
            block=block,
            roles=_ISO_ROLES,
            patterns=("other", "h_pull"),
            muscles=BICEPS_SLUGS,
            prefer=("curl", "cuốn"),
        ),
        _slot(
            "back_iso",
            block=block,
            roles=_ISO_ROLES,
            patterns=("h_pull", "v_pull", "other"),
            muscles=BACK_SLUGS,
            prefer=("row", "pulldown", "straight arm"),
        ),
        _slot(
            "pull_extra_iso",
            block=block,
            roles=_ISO_ROLES,
            patterns=("h_pull", "v_pull", "other"),
            muscles=BACK_SLUGS | BICEPS_SLUGS | SHOULDER_SLUGS,
        ),
    ]


def _leg_compounds(block: str) -> list[ExerciseSlot]:
    return [
        _slot(
            "squat",
            block=block,
            roles=_COMPOUND_ROLES,
            patterns=("squat",),
            muscles=QUAD_SLUGS,
            prefer=("squat", "leg press", "lunge", "ngồi xổm"),
            avoid=_COMPOUND_AVOID,
        ),
        _slot(
            "hinge",
            block=block,
            roles=_COMPOUND_ROLES,
            patterns=("hinge",),
            muscles=HINGE_MUSCLE_SLUGS | GLUTE_SLUGS,
            prefer=("deadlift", "rdl", "romanian", "hip thrust", "hinge", "bridge"),
            avoid=_COMPOUND_AVOID,
        ),
        _slot(
            "extra_leg",
            block=block,
            roles=_COMPOUND_ROLES,
            patterns=("squat", "hinge"),
            muscles=QUAD_SLUGS | HINGE_MUSCLE_SLUGS | GLUTE_SLUGS,
            prefer=("lunge", "split squat", "step"),
            avoid=_COMPOUND_AVOID,
        ),
    ]


def _leg_isos(block: str, *, compound_n: int = 2) -> list[ExerciseSlot]:
    ham = _slot(
        "ham_iso",
        block=block,
        roles=_ISO_ROLES,
        patterns=("hinge", "other"),
        muscles=HAMSTRING_SLUGS,
        prefer=("curl", "leg curl", "đùi sau", "hamstring"),
        avoid=("calf", "bắp chân"),
    )
    quad = _slot(
        "quad_or_glute_iso",
        block=block,
        roles=_ISO_ROLES,
        patterns=("squat", "hinge", "other"),
        muscles=QUAD_SLUGS | GLUTE_SLUGS,
        prefer=("extension", "kickback", "abduct", "lunge"),
    )
    calf = _slot(
        "calf_iso",
        block=block,
        roles=_ISO_ROLES,
        patterns=("other",),
        muscles=CALF_SLUGS,
        prefer=("calf", "bắp chân"),
    )
    extra = _slot(
        "leg_extra_iso",
        block=block,
        roles=_ISO_ROLES,
        patterns=("squat", "hinge", "other"),
        muscles=QUAD_SLUGS | HINGE_MUSCLE_SLUGS | GLUTE_SLUGS,
        avoid=("calf", "bắp chân"),
    )
    finisher = _slot(
        "leg_finisher_iso",
        block=block,
        roles=_ISO_ROLES,
        patterns=("squat", "hinge", "other"),
        muscles=QUAD_SLUGS | HINGE_MUSCLE_SLUGS | GLUTE_SLUGS,
        avoid=("calf", "bắp chân"),
    )
    if compound_n <= 1:
        return [ham, quad, extra, finisher, calf]
    return [quad, ham, extra, finisher, calf]


def _upper_compounds(
    block: str, *, day_index: int, experience_level: int = 2
) -> list[ExerciseSlot]:
    """Upper A (UL day 1): flat press + row. Upper B: flat press + pulldown."""
    variant_b = (int(day_index) // 2) % 2 == 1
    impl = _chest_implement_prefer(experience_level)
    chest = _slot(
        "h_press",
        block=block,
        roles=_COMPOUND_ROLES,
        patterns=("h_push",),
        muscles=CHEST_SLUGS,
        prefer=impl + _CHEST_FLAT_PREFER,
        avoid=_chest_compound_avoid(),
        relax_muscle=False,
    )
    if variant_b:
        back = _slot(
            "v_pull",
            block=block,
            roles=_COMPOUND_ROLES,
            patterns=("v_pull",),
            muscles=BACK_SLUGS,
            prefer=("pulldown", "pull-up", "pullup", "chin", "kéo xô"),
            avoid=_COMPOUND_AVOID,
            relax_muscle=False,
        )
        third = _slot(
            "h_pull",
            block=block,
            roles=_COMPOUND_ROLES,
            patterns=("h_pull",),
            muscles=BACK_SLUGS,
            prefer=("row", "chèo"),
            avoid=_COMPOUND_AVOID,
        )
    else:
        back = _slot(
            "h_pull",
            block=block,
            roles=_COMPOUND_ROLES,
            patterns=("h_pull",),
            muscles=BACK_SLUGS,
            prefer=("row", "chèo"),
            avoid=_COMPOUND_AVOID,
            relax_muscle=False,
        )
        third = _slot(
            "v_press",
            block=block,
            roles=_COMPOUND_ROLES,
            patterns=("v_push",),
            muscles=SHOULDER_SLUGS,
            prefer=("overhead", "shoulder press"),
            avoid=_COMPOUND_AVOID,
        )
    return [chest, back, third]


def _upper_isos(block: str) -> list[ExerciseSlot]:
    return [
        _slot(
            "chest_iso",
            block=block,
            roles=_ISO_ROLES,
            patterns=("h_push", "other"),
            muscles=CHEST_SLUGS,
            prefer=("fly", "pec", "ép ngực", "ep nguc", "mở ngực"),
            avoid=("pullover", "shrug", "face pull", "nhún", "kéo dây về mặt"),
            relax_muscle=False,
        ),
        _slot(
            "upper_pull_iso",
            block=block,
            roles=_ISO_ROLES,
            patterns=("h_pull", "other"),
            muscles=BACK_SLUGS | BICEPS_SLUGS | SHOULDER_SLUGS,
            prefer=("curl", "face pull", "rear", "cuốn"),
        ),
        _slot(
            "upper_shoulder_tri_iso",
            block=block,
            roles=_ISO_ROLES,
            patterns=("v_push", "h_push", "other"),
            muscles=SHOULDER_SLUGS | TRICEPS_SLUGS,
            prefer=("raise", "dang vai", "pushdown", "extension"),
            avoid=("face pull", "shrug", "nhún", "pullover"),
        ),
        _slot(
            "upper_finisher_iso",
            block=block,
            roles=_ISO_ROLES,
            patterns=("h_push", "h_pull", "v_push", "other"),
            muscles=CHEST_SLUGS | BACK_SLUGS | BICEPS_SLUGS | TRICEPS_SLUGS | SHOULDER_SLUGS,
            relax_muscle=False,
        ),
    ]


def _upper_bw_compounds(block: str) -> list[ExerciseSlot]:
    """No-equip Upper: push-up + BW back/core — no gym v_pull/h_pull slots."""
    return [
        _slot(
            "h_press",
            block=block,
            roles=_COMPOUND_ROLES | _ISO_ROLES | _FB_ROLES,
            patterns=("h_push",),
            muscles=CHEST_SLUGS,
            prefer=("push-up", "push up", "chống đẩy", "chong day", "pike"),
            avoid=_chest_compound_avoid(),
        ),
        _slot(
            "back_bw",
            block=block,
            roles=_COMPOUND_ROLES | _ISO_ROLES | _FB_ROLES,
            patterns=_HOME_NO_EQUIP_BACK_PATTERNS,
            muscles=BACK_SLUGS | CORE_SLUGS,
            prefer=_HOME_NO_EQUIP_BACK_PREFER,
        ),
        _slot(
            "core_bw",
            block=block,
            roles=_ISO_ROLES | _FB_ROLES,
            patterns=("core", "other"),
            muscles=CORE_SLUGS,
            prefer=("plank", "sit-up", "crunch", "gập bụng", "gap bung"),
        ),
    ]


def _pull_bw_compounds(block: str) -> list[ExerciseSlot]:
    """No-equip Pull: back + core bodyweight — not gym v_pull/h_pull."""
    return [
        _slot(
            "back_bw",
            block=block,
            roles=_COMPOUND_ROLES | _ISO_ROLES | _FB_ROLES,
            patterns=_HOME_NO_EQUIP_BACK_PATTERNS,
            muscles=BACK_SLUGS | CORE_SLUGS,
            prefer=_HOME_NO_EQUIP_BACK_PREFER,
        ),
        _slot(
            "core_bw",
            block=block,
            roles=_COMPOUND_ROLES | _ISO_ROLES | _FB_ROLES,
            patterns=("core", "other"),
            muscles=CORE_SLUGS,
            prefer=("plank", "bird dog", "dead bug", "hollow"),
        ),
        _slot(
            "back_bw_2",
            block=block,
            roles=_COMPOUND_ROLES | _ISO_ROLES | _FB_ROLES,
            patterns=_HOME_NO_EQUIP_BACK_PATTERNS,
            muscles=BACK_SLUGS,
            prefer=_HOME_NO_EQUIP_BACK_PREFER,
        ),
    ]


def _pull_bw_isos(block: str) -> list[ExerciseSlot]:
    return [
        _slot(
            "rear_delt_bw",
            block=block,
            roles=_ISO_ROLES | _FB_ROLES,
            patterns=("other", "h_pull"),
            muscles=SHOULDER_SLUGS | BACK_SLUGS,
            prefer=("y raise", "t raise", "w raise", "reverse snow"),
        ),
        _slot(
            "core_bw_iso",
            block=block,
            roles=_ISO_ROLES | _FB_ROLES,
            patterns=("core", "other"),
            muscles=CORE_SLUGS,
            prefer=("plank", "dead bug", "hollow", "bird dog"),
        ),
        _slot(
            "back_iso_bw",
            block=block,
            roles=_ISO_ROLES | _FB_ROLES,
            patterns=_HOME_NO_EQUIP_BACK_PATTERNS,
            muscles=BACK_SLUGS,
            prefer=_HOME_NO_EQUIP_BACK_PREFER,
        ),
        _slot(
            "pull_extra_iso",
            block=block,
            roles=_ISO_ROLES | _FB_ROLES,
            patterns=("other", "core"),
            muscles=BACK_SLUGS | CORE_SLUGS | SHOULDER_SLUGS,
        ),
    ]


def _upper_bw_isos(block: str) -> list[ExerciseSlot]:
    return [
        _slot(
            "core_bw_iso",
            block=block,
            roles=_ISO_ROLES | _FB_ROLES,
            patterns=("core", "other"),
            muscles=CORE_SLUGS,
            prefer=("plank", "sit-up", "crunch", "gập bụng", "hollow"),
        ),
        _slot(
            "chest_iso",
            block=block,
            roles=_ISO_ROLES | _FB_ROLES,
            patterns=("h_push", "other"),
            muscles=CHEST_SLUGS,
            prefer=("push-up", "pike", "diamond"),
        ),
        _slot(
            "back_iso_bw",
            block=block,
            roles=_ISO_ROLES | _FB_ROLES,
            patterns=_HOME_NO_EQUIP_BACK_PATTERNS,
            muscles=BACK_SLUGS,
            prefer=_HOME_NO_EQUIP_BACK_PREFER,
        ),
        _slot(
            "upper_bw_extra",
            block=block,
            roles=_ISO_ROLES | _FB_ROLES,
            patterns=("h_push", "core", "other"),
            muscles=CHEST_SLUGS | CORE_SLUGS | SHOULDER_SLUGS,
        ),
    ]


def _fb_pattern_slots(block: str, *, variant: str) -> list[ExerciseSlot]:
    if variant == "fb_b":
        specs = (
            ("squat", ("squat",), QUAD_SLUGS, ("squat", "lunge", "leg press")),
            ("v_push", ("v_push",), SHOULDER_SLUGS, ("overhead", "shoulder press", "pike")),
            ("hinge", ("hinge",), HINGE_MUSCLE_SLUGS | GLUTE_SLUGS, ("deadlift", "rdl", "hip thrust", "bridge")),
            ("v_pull", ("v_pull",), BACK_SLUGS, ("pulldown", "pull-up", "chin")),
        )
    else:
        specs = (
            ("squat", ("squat",), QUAD_SLUGS, ("squat", "lunge", "leg press")),
            ("h_push", ("h_push",), CHEST_SLUGS, ("bench", "chest press", "push-up", "đẩy ngực")),
            ("hinge", ("hinge",), HINGE_MUSCLE_SLUGS | GLUTE_SLUGS, ("deadlift", "rdl", "hip thrust", "bridge")),
            ("h_pull", ("h_pull",), BACK_SLUGS, ("row", "chèo")),
        )
    return [
        _slot(
            key,
            block=block,
            roles=_FB_ROLES,
            patterns=pats,
            muscles=muscles,
            prefer=prefer,
            avoid=_COMPOUND_AVOID,
        )
        for key, pats, muscles, prefer in specs
    ]


def _fb_isos(block: str) -> list[ExerciseSlot]:
    return [
        _slot(
            "fb_iso_a",
            block=block,
            roles=_ISO_ROLES,
            patterns=("h_push", "h_pull", "v_push", "v_pull", "core", "other"),
            muscles=CHEST_SLUGS | BACK_SLUGS | SHOULDER_SLUGS | BICEPS_SLUGS | TRICEPS_SLUGS,
        ),
        _slot(
            "fb_iso_b",
            block=block,
            roles=_ISO_ROLES,
            patterns=("squat", "hinge", "core", "other"),
            muscles=QUAD_SLUGS | HINGE_MUSCLE_SLUGS | GLUTE_SLUGS | CALF_SLUGS,
        ),
    ]


def _focus_iso_slot(block: str, focus_slugs: frozenset[str]) -> ExerciseSlot | None:
    if not focus_slugs:
        return None
    return _slot(
        "focus_iso",
        block=block,
        roles=_ISO_ROLES,
        patterns=("h_push", "h_pull", "v_push", "v_pull", "squat", "hinge", "other", "core"),
        muscles=frozenset(focus_slugs),
    )


def slots_for_session(
    split_role: str | None,
    *,
    compound_n: int,
    accessory_n: int,
    location: str = "gym",
    focus_slugs: frozenset[str] | None = None,
    day_index: int = 0,
    allow_bar_moves: bool = True,
    experience_level: int = 2,
    no_equipment: bool = False,
) -> list[ExerciseSlot]:
    """Ordered strength slots mapped onto compound/accessory (gym) or resistance (home)."""
    loc = (location or "gym").strip().lower()
    if loc not in {"gym", "home"}:
        loc = "gym"
    c_block = _compound_block(loc)
    i_block = _iso_block(loc)
    key = normalize_split_role(split_role)
    n_c = max(0, int(compound_n))
    n_i = max(0, int(accessory_n))

    if key in {"fb", "fb_a", "fb_b"}:
        variant = "fb_b" if key == "fb_b" else "fb_a"
        pattern_slots = _fb_pattern_slots(c_block, variant=variant)
        # First n_c stay on the compound/resistance block; leftover patterns fill accessory.
        assigned: list[ExerciseSlot] = []
        for i, slot in enumerate(pattern_slots):
            block = c_block if i < n_c else i_block
            assigned.append(
                ExerciseSlot(
                    key=slot.key,
                    block=block,
                    roles=slot.roles,
                    patterns=slot.patterns,
                    muscles=slot.muscles,
                    prefer=slot.prefer,
                    avoid=slot.avoid,
                )
            )
        leftover_iso = max(0, n_c + n_i - len(assigned))
        assigned.extend(_fb_isos(i_block)[:leftover_iso])
        return _maybe_strip_bar_slots(assigned[: n_c + n_i], allow_bar_moves=allow_bar_moves)

    if key == "push":
        compounds, isos = (
            _push_compounds(c_block, experience_level=experience_level),
            _push_isos(i_block),
        )
    elif key == "pull":
        if no_equipment:
            compounds, isos = _pull_bw_compounds(c_block), _pull_bw_isos(i_block)
        else:
            compounds, isos = _pull_compounds(c_block), _pull_isos(i_block)
    elif key in {"legs", "lower"}:
        compounds, isos = _leg_compounds(c_block), _leg_isos(i_block, compound_n=n_c)
    elif key == "upper":
        if no_equipment:
            compounds, isos = _upper_bw_compounds(c_block), _upper_bw_isos(i_block)
        else:
            compounds, isos = (
                _upper_compounds(
                    c_block, day_index=day_index, experience_level=experience_level
                ),
                _upper_isos(i_block),
            )
    else:
        return []

    extra = _focus_iso_slot(i_block, frozenset(focus_slugs or ()))
    if extra and n_i >= 3:
        hints = muscle_hints_for_split(key)
        if hints & frozenset(s.strip().lower() for s in (focus_slugs or ())):
            isos = isos[:2] + [extra] + isos[2:]

    if key in {"legs", "lower"} and n_i > 0:
        calf_slots = [s for s in isos if s.key == "calf_iso"]
        rest_iso = [s for s in isos if s.key != "calf_iso"]
        focus_slots = [s for s in rest_iso if s.key == "focus_iso"]
        body = [s for s in rest_iso if s.key != "focus_iso"]
        if n_i == 1:
            isos = calf_slots[:1] or rest_iso[:1]
        elif focus_slots:
            isos = body[: max(0, n_i - 2)] + focus_slots[:1] + calf_slots[:1]
        else:
            isos = body[: max(0, n_i - 1)] + calf_slots[:1]

    assigned = compounds[:n_c] + isos[:n_i]
    return _maybe_strip_bar_slots(assigned, allow_bar_moves=allow_bar_moves)


def _as_dict(item: Any, *, source_block: str | None = None) -> dict[str, Any]:
    if isinstance(item, dict):
        d = dict(item)
    else:
        d = {
            "id": int(item.id),
            "movement_pattern": getattr(item, "movement_pattern", None),
            "movement_role": getattr(item, "movement_role", None),
            "muscle": getattr(item, "muscle_slug", None) or getattr(item, "muscle", None),
            "name_vi": getattr(item, "name_vi", ""),
            "name_en": getattr(item, "name_en", ""),
        }
        eq = getattr(item, "equipment_slugs", None)
        if eq:
            d["equipment_slugs"] = sorted(str(s) for s in eq)
    if source_block and not d.get("_block"):
        d["_block"] = source_block
    if not str(d.get("movement_role") or "").strip():
        src = str(d.get("_block") or source_block or "")
        if src == "compound":
            d["movement_role"] = "compound"
        elif src == "accessory":
            d["movement_role"] = "isolation"
        elif src == "resistance":
            d["movement_role"] = "resistance"
    return d


def _eid(d: dict[str, Any]) -> int:
    return int(d["id"])


def _blob(d: dict[str, Any]) -> str:
    return " ".join(
        str(d.get(k) or "") for k in ("name_vi", "name_en", "name", "slug")
    ).lower()


def _role(d: dict[str, Any]) -> str:
    return str(d.get("movement_role") or "").strip().lower()


def _pattern(d: dict[str, Any]) -> str:
    return str(d.get("movement_pattern") or "").strip().lower()


def _muscle(d: dict[str, Any]) -> str:
    return str(d.get("muscle") or d.get("muscle_slug") or "").strip().lower()


def _is_compoundish(d: dict[str, Any]) -> bool:
    role = _role(d)
    if role == "isolation":
        return False
    if role == "compound":
        return True
    # Home resistance: treat as compound unless the name is clearly isolation.
    blob = _blob(d)
    return not any(k in blob for k in _COMPOUND_AVOID)


def _role_ok(slot: ExerciseSlot, d: dict[str, Any], *, strict: bool) -> bool:
    if not slot.roles:
        return True
    role = _role(d)
    if role in slot.roles:
        return True
    if role == "resistance" and slot.roles & {"compound", "isolation"}:
        return True
    if not role:
        return not strict
    return not strict


def _pattern_ok(slot: ExerciseSlot, d: dict[str, Any], *, strict: bool) -> bool:
    if not slot.patterns:
        return True
    if _pattern(d) in slot.patterns:
        return True
    return not strict


def _muscle_ok(slot: ExerciseSlot, d: dict[str, Any], *, strict: bool) -> bool:
    if not slot.muscles:
        return True
    muscle = _muscle(d)
    if not muscle:
        return True
    if muscle in slot.muscles:
        return True
    return not strict


def _avoid_hit(slot: ExerciseSlot, d: dict[str, Any]) -> bool:
    if not slot.avoid:
        return False
    blob = _blob(d)
    if not blob.strip():
        return False
    if not any(k in blob for k in slot.avoid):
        return False
    # "ép ngực" in _COMPOUND_AVOID targets pec deck / machine fly; a dumbbell or barbell
    # bench press ("Đẩy ngực tạ đơn" / "Ép ngực tạ đòn") must stay a chest compound.
    if slot.key in _CHEST_COMPOUND_KEYS and is_free_weight_chest_press(d):
        return False
    return True


def _score_slot(
    slot: ExerciseSlot,
    d: dict[str, Any],
    *,
    strict_role: bool,
    strict_pattern: bool,
    strict_muscle: bool,
    focus_slugs: frozenset[str] | None,
) -> int | None:
    if _avoid_hit(slot, d):
        return None
    if not _role_ok(slot, d, strict=strict_role):
        return None
    if not _pattern_ok(slot, d, strict=strict_pattern):
        return None
    if not _muscle_ok(slot, d, strict=strict_muscle):
        return None
    score = 0
    if _role(d) in slot.roles:
        score += 20
    elif _role(d) == "resistance":
        score += 12
    if slot.patterns and _pattern(d) in slot.patterns:
        score += 30
    if slot.muscles and _muscle(d) in slot.muscles:
        score += 18
    blob = _blob(d)
    if slot.prefer and blob and any(k in blob for k in slot.prefer):
        score += 40
    if d.get("_block") == slot.block:
        score += 8
    if focus_slugs and _muscle(d) in focus_slugs and "iso" in slot.key:
        score += 12
    # Home + gear: rows flagged by home_gear_priority (internal `_gear`) or prompt `bw`.
    if d.get("_gear"):
        score += HOME_GEAR_SLOT_BONUS
    elif d.get("bw"):
        score -= HOME_GEAR_SLOT_BONUS
    try:
        score -= int(d.get("id") or 0) % 7
    except (TypeError, ValueError):
        pass
    return score


def candidate_matches_slot(
    slot: ExerciseSlot,
    d: dict[str, Any],
    *,
    split_role: str | None = None,
) -> bool:
    """Strict muscle/pattern/role/avoid match for GPT slot pools."""
    if is_denied_for_split(split_role, pattern=_pattern(d), muscle_slug=_muscle(d)):
        return False
    if _avoid_hit(slot, d):
        return False
    if not _role_ok(slot, d, strict=True):
        return False
    if not _pattern_ok(slot, d, strict=True):
        return False
    if not _muscle_ok(slot, d, strict=True):
        return False
    return True


def slot_prefer_rank(slot: ExerciseSlot, row: dict[str, Any]) -> int:
    """0 when the row name hits the slot's `prefer` needles, else 1 (for bodyweight top-up order)."""
    if not slot.prefer:
        return 1
    blob = _blob(row)
    return 0 if blob and any(k in blob for k in slot.prefer) else 1


def _chest_pool_sort_key(
    slot: ExerciseSlot, row: dict[str, Any], experience_level: int
) -> tuple[int, int, int]:
    blob = " ".join(
        str(row.get(k) or "") for k in ("name_vi", "name_en", "name")
    ).lower()
    impl = _chest_implement_prefer(experience_level)
    if int(experience_level or 2) <= 1:
        if any(n in blob for n in ("machine", "máy")):
            impl_rank = 0
        elif "chest press" in blob:
            impl_rank = 1
        else:
            impl_rank = 2
    else:
        impl_rank = 0 if any(n.lower() in blob for n in impl) else 1
    if slot.key == "extra_press":
        angle_rank = 0 if any(n in blob for n in _CHEST_INCLINE_PREFER) else 1
    elif any(n in blob for n in ("incline", "dốc lên", "dốc cao", "doc len")):
        angle_rank = 2
    elif any(n in blob for n in ("flat", "nằm", "bench", "chống đẩy", "push-up", "push up")):
        angle_rank = 0
    else:
        angle_rank = 1
    try:
        eid = int(row["id"])
    except (KeyError, TypeError, ValueError):
        eid = 0
    return (impl_rank, angle_rank, eid)


def pools_for_slots(
    candidates: Iterable[Any],
    slots: list[ExerciseSlot],
    *,
    split_role: str | None = None,
    experience_level: int = 2,
) -> dict[str, list[dict[str, Any]]]:
    """Partition filtered catalog into per-slot pools (strict match, no score pick)."""
    items = [_as_dict(x) for x in candidates]
    out: dict[str, list[dict[str, Any]]] = {}
    for slot in slots:
        pool: list[dict[str, Any]] = []
        seen: set[int] = set()
        for d in items:
            try:
                eid = _eid(d)
            except (KeyError, TypeError, ValueError):
                continue
            if eid in seen:
                continue
            if not candidate_matches_slot(slot, d, split_role=split_role):
                continue
            if slot.key in _CHEST_COMPOUND_KEYS and (
                is_decline_chest_compound(d) or is_triceps_press_imposter(d)
            ):
                continue
            seen.add(eid)
            row: dict[str, Any] = {
                "id": eid,
                "name_vi": str(d.get("name_vi") or ""),
                "movement_role": d.get("movement_role"),
                "pattern": _pattern(d) or d.get("movement_pattern"),
                "muscle": _muscle(d),
            }
            if d.get("name_en"):
                row["name_en"] = d.get("name_en")
            if d.get("equipment_slugs"):
                row["equipment_slugs"] = list(d.get("equipment_slugs") or [])
            pool.append(row)
        if slot.key in _CHEST_COMPOUND_KEYS:
            pool.sort(key=lambda x: _chest_pool_sort_key(slot, x, experience_level))
        else:
            pool.sort(key=lambda x: int(x["id"]))
        out[slot.key] = pool
    return out


_SLOT_LABEL_VI = {
    "h_press": "Ngực compound",
    "v_press": "Vai compound",
    "extra_press": "Push compound phụ",
    "chest_iso": "Ngực isolation",
    "push_arm_iso": "Vai / tay sau isolation",
    "push_extra_iso": "Push isolation phụ",
    "push_finisher_iso": "Push finisher",
    "v_pull": "Kéo dọc (lưng)",
    "h_pull": "Kéo ngang (lưng)",
    "extra_pull": "Pull compound phụ",
    "back_iso": "Lưng isolation",
    "pull_arm_iso": "Tay trước isolation",
    "rear_delt_iso": "Sau vai isolation",
    "squat": "Squat / đùi trước",
    "hinge": "Hinge / sau đùi",
    "quad_iso": "Đùi trước isolation",
    "ham_iso": "Đùi sau isolation",
    "glute_iso": "Mông isolation",
    "calf_iso": "Bắp chân",
}


_POOL_INTERNAL_KEYS = frozenset({"equipment_slugs"})


def prompt_pool_row(row: dict[str, Any], *, mark_bw: bool = False) -> dict[str, Any]:
    """Strip internal keys (`_*`, equipment_slugs); `mark_bw` flags bodyweight rows."""
    out = {
        k: v
        for k, v in row.items()
        if not str(k).startswith("_") and k not in _POOL_INTERNAL_KEYS
    }
    if mark_bw and not row.get("equipment_slugs"):
        out["bw"] = 1
    return out


def slots_to_prompt(
    slots: list[ExerciseSlot],
    pools: dict[str, list[dict[str, Any]]],
    *,
    mark_bw: bool = False,
) -> list[dict[str, Any]]:
    """Serialize session slots + pools for the OpenAI picker."""
    out: list[dict[str, Any]] = []
    for slot in slots:
        out.append(
            {
                "key": slot.key,
                "block_key": slot.block,
                "label": _SLOT_LABEL_VI.get(slot.key) or slot.key,
                "pick": 1,
                "required": bool(slot.required),
                "pool": [
                    prompt_pool_row(r, mark_bw=mark_bw) for r in (pools.get(slot.key) or [])
                ],
            }
        )
    return out


def slot_allows_week_b_swap(slot: dict[str, Any] | ExerciseSlot) -> bool:
    """True for isolation/cardio/core slots — compounds stay on week A."""
    if isinstance(slot, ExerciseSlot):
        key = slot.key
        block = slot.block
    else:
        key = str(slot.get("key") or "")
        block = str(slot.get("block_key") or slot.get("block") or "")
    if "iso" in key:
        return True
    return block in {"accessory", "conditioning", "core", "cardio"}


def fill_strength_slots(
    split_role: str | None,
    slots: list[ExerciseSlot],
    pool: Iterable[Any],
    *,
    used_ids: set[int] | None = None,
    avoid_compound_patterns: frozenset[str] | None = None,
    focus_slugs: frozenset[str] | None = None,
    avoid_ids: set[int] | frozenset[int] | None = None,
    avoid_stems: set[str] | frozenset[str] | None = None,
    prefer_knee: bool = False,
) -> dict[str, list[int]]:
    """Fill slots in order. Returns exercise ids grouped by destination block."""
    items = [_as_dict(x) for x in pool]
    picked_ids: set[int] = set(used_ids or ())
    avoid_eids = {int(i) for i in (avoid_ids or ())}
    avoid_stem_keys = {str(s) for s in (avoid_stems or ()) if str(s).strip()}
    avoid_pats = frozenset(
        str(p).strip().lower() for p in (avoid_compound_patterns or ()) if str(p).strip()
    )
    out: dict[str, list[int]] = {}
    seen_compound_pats: set[str] = set()
    seen_stems: set[str] = set()

    passes = (
        (True, True, True),
        (True, True, False),
        (True, False, False),
        (False, False, False),
    )

    from app.services.workout_generation.weekly_volume import lift_stem

    def _cand_stem(d: dict[str, Any]) -> str | None:
        return lift_stem(str(d.get("name_vi") or ""), str(d.get("name_en") or "") or None)

    def _is_phase_avoided(d: dict[str, Any]) -> bool:
        try:
            eid = _eid(d)
        except (KeyError, TypeError, ValueError):
            return False
        if eid in avoid_eids:
            return True
        stem = _cand_stem(d)
        return bool(stem and stem in avoid_stem_keys)

    def _is_standard_pushup(d: dict[str, Any]) -> bool:
        from app.services.workout_generation.weekly_volume import is_standard_pushup_name

        return is_standard_pushup_name(
            str(d.get("name_vi") or ""), str(d.get("name_en") or "") or None
        )

    for slot in slots:
        chosen: dict[str, Any] | None = None
        std_passes = (False, True) if prefer_knee else (True,)
        for allow_avoided in (False, True):
            for allow_standard_pu in std_passes:
                for strict_role, strict_pattern, strict_muscle in passes:
                    if not slot.relax_muscle:
                        strict_muscle = True
                    best: tuple[int, dict[str, Any]] | None = None
                    for d in items:
                        try:
                            eid = _eid(d)
                        except (KeyError, TypeError, ValueError):
                            continue
                        if eid in picked_ids:
                            continue
                        if not allow_avoided and _is_phase_avoided(d):
                            continue
                        if prefer_knee and not allow_standard_pu and _is_standard_pushup(d):
                            continue
                        if is_denied_for_split(
                            split_role, pattern=_pattern(d), muscle_slug=_muscle(d)
                        ):
                            continue
                        if _is_compoundish(d) and _pattern(d) in avoid_pats:
                            continue
                        if (
                            _is_compoundish(d)
                            and _pattern(d)
                            and _pattern(d) in seen_compound_pats
                        ):
                            continue
                        stem = _cand_stem(d)
                        if _is_compoundish(d) and stem and stem in seen_stems:
                            continue
                        scored = _score_slot(
                            slot,
                            d,
                            strict_role=strict_role,
                            strict_pattern=strict_pattern,
                            strict_muscle=strict_muscle,
                            focus_slugs=focus_slugs,
                        )
                        if scored is None:
                            continue
                        if prefer_knee:
                            from app.services.workout_generation.weekly_volume import (
                                is_knee_pushup_name,
                            )

                            if is_knee_pushup_name(
                                str(d.get("name_vi") or ""), str(d.get("name_en") or "")
                            ):
                                scored += 25
                        if best is None or scored > best[0]:
                            best = (scored, d)
                    if best:
                        chosen = best[1]
                        break
                if chosen:
                    break
            if chosen:
                break
        if not chosen:
            if slot.required:
                continue
            continue
        eid = _eid(chosen)
        picked_ids.add(eid)
        if _is_compoundish(chosen):
            pat = _pattern(chosen)
            if pat:
                seen_compound_pats.add(pat)
            stem = _cand_stem(chosen)
            if stem:
                seen_stems.add(stem)
        out.setdefault(slot.block, []).append(eid)

    return out
