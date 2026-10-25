"""Standard session slot templates (Boostcamp/Hevy/PPL-style) filled from the catalog."""

from __future__ import annotations

from dataclasses import dataclass, replace
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


_GENERIC_SHOULDER_SLUGS = frozenset({"shoulders", "shoulders-deltoids", "co-vai"})
_PUSH_DELT_SLUGS = frozenset({"shoulders-front", "shoulders-lateral"}) | _GENERIC_SHOULDER_SLUGS
_PULL_DELT_SLUGS = frozenset({"shoulders-rear", "shoulders-traps"}) | _GENERIC_SHOULDER_SLUGS
_PUSH_DELT_NAMES = (
    "front raise",
    "nâng tay trước",
    "nang tay truoc",
    "lateral raise",
    "dang ngang",
    "dang vai",
    "nâng tay ngang",
    "nang tay ngang",
)
_PULL_DELT_NAMES = (
    "reverse fly",
    "bay vai sau",
    "shrug",
    "nhún vai",
    "nhun vai",
    "face pull",
    "bả vai",
    "ba vai",
)


def _push_delt_iso(block: str) -> ExerciseSlot:
    """One push-day shoulder: front raise, else lateral raise. Not rear delt or shrug."""
    return _slot(
        "push_delt",
        block=block,
        roles=_ISO_ROLES,
        patterns=("other",),
        muscles=_PUSH_DELT_SLUGS,
        prefer=_PUSH_DELT_NAMES,
        avoid=(
            "reverse",
            "rear",
            "shrug",
            "nhún",
            "nhun",
            "face pull",
            "overhead",
            "pike",
            "đẩy vai",
            "day vai",
            "vai sau",
            "sau vai",
        ),
        relax_muscle=False,
    )


def _pull_isos(block: str) -> list[ExerciseSlot]:
    return [
        _slot(
            "rear_delt",
            block=block,
            roles=_ISO_ROLES,
            patterns=("h_pull", "other"),
            muscles=_PULL_DELT_SLUGS,
            prefer=_PULL_DELT_NAMES,
            avoid=(
                "front raise",
                "lateral raise",
                "nâng tay trước",
                "nang tay truoc",
                "dang ngang",
                "dang vai",
                "overhead",
                "đẩy vai",
                "day vai",
            ),
            relax_muscle=False,
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
    return [ham, quad, extra, finisher, calf]


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


def _triceps_iso(block: str) -> ExerciseSlot:
    return _slot(
        "push_arm_iso",
        block=block,
        roles=_ISO_ROLES,
        patterns=("h_push", "v_push", "other"),
        muscles=TRICEPS_SLUGS,
        prefer=("pushdown", "extension", "kickback", "skull", "tay sau"),
    )


def _shoulder_press(block: str) -> ExerciseSlot:
    return _slot(
        "v_press",
        block=block,
        roles=_COMPOUND_ROLES,
        patterns=("v_push",),
        muscles=PUSH_SHOULDER_SLUGS,
        prefer=("overhead", "shoulder press", "military", "ohp", "đẩy vai", "pike"),
        avoid=_COMPOUND_AVOID,
    )


def _home_slots_for_minutes(
    key: str,
    minutes: int,
    *,
    c_block: str,
    i_block: str,
    experience_level: int,
    day_index: int,
    focus_keys: list[str] | None = None,
) -> list[ExerciseSlot] | None:
    """Required muscles for a home session length. None keeps the count-based template."""
    from app.services.workout_generation.focus import extra_focus_kind, normalize_focus_areas

    extra_kind = extra_focus_kind(key, normalize_focus_areas(focus_keys)) if minutes > 45 else None
    if key == "push":
        chest, _overhead, _extra = _push_compounds(c_block, experience_level=experience_level)
        delt = _push_delt_iso(i_block)
        tri = _triceps_iso(i_block)
        chest_iso = _push_isos(i_block)[0]
        if minutes <= 45:
            return [chest, delt, tri, chest_iso, replace(delt, key="push_side_delt")]
        extra = {
            "chest": chest_iso,
            "shoulder": replace(delt, key="push_delt_focus"),
            "triceps": replace(tri, key="push_arm_iso_focus"),
        }.get(extra_kind or "chest", chest_iso)
        return [chest, delt, tri, extra]
    if key == "pull":
        vertical, horizontal, _extra = _pull_compounds(c_block)
        rear, biceps, _back_iso, _pull_extra = _pull_isos(i_block)
        if minutes <= 45:
            return [vertical, horizontal, rear, biceps, _back_iso]
        extra = {
            "back": horizontal,
            "rear": replace(rear, key="rear_delt_focus"),
            "biceps": replace(biceps, key="biceps_focus"),
        }.get(extra_kind or "back", horizontal)
        return [vertical, rear, biceps, extra]
    if key in {"legs", "lower"}:
        squat, hinge, _extra = _leg_compounds(c_block)
        isos = _leg_isos(i_block)
        ham = next(s for s in isos if s.key == "ham_iso")
        calf = next(s for s in isos if s.key == "calf_iso")
        quad = next(s for s in isos if s.key == "quad_or_glute_iso")
        glute = _slot(
            "glute_iso",
            block=i_block,
            roles=_ISO_ROLES,
            patterns=("hinge", "other"),
            muscles=GLUTE_SLUGS,
            prefer=("bridge", "hip thrust", "kickback", "cầu mông", "mông"),
        )
        if minutes <= 45:
            return [squat, hinge, ham, calf, quad]
        extra = {
            "quad": quad,
            "ham": ham,
            "glute": glute,
            "calf": calf,
        }.get(extra_kind or "", None)
        if extra is None:
            return [squat, hinge, ham, calf]
        return [squat, hinge, ham, extra]
    if key == "upper":
        chest, back, _third = _upper_compounds(
            c_block, day_index=day_index, experience_level=experience_level
        )
        arm = _upper_isos(i_block)[2]
        press = _shoulder_press(c_block)
        if minutes <= 45:
            _vertical, horizontal, _extra_pull = _pull_compounds(c_block)
            return [chest, horizontal, press, arm, _pull_isos(i_block)[1]]
        extra = {
            "chest": _push_isos(i_block)[0],
            "back": _pull_isos(i_block)[2],
            "shoulder": replace(press, key="v_press_focus"),
            "biceps": _pull_isos(i_block)[1],
        }.get(extra_kind or "", arm)
        return [chest, back, press, extra]
    if key in {"fb", "fb_a", "fb_b"}:
        variant = "fb_b" if key == "fb_b" else "fb_a"
        patterns = _fb_pattern_slots(c_block, variant=variant)
        if minutes > 45:
            return patterns[:4]
        slots = list(patterns)
        if any(slot.key == "h_pull" for slot in slots):
            slots.append(
                _slot(
                    "fb_core",
                    block=i_block,
                    roles=_ISO_ROLES,
                    patterns=("core", "other"),
                    muscles=CORE_SLUGS,
                    prefer=("plank", "dead bug", "crunch"),
                )
            )
        else:
            _vertical, horizontal, _extra_pull = _pull_compounds(c_block)
            slots.append(horizontal)
        return slots[:5]
    return None


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
    session_minutes: int | None = None,
    focus_areas: list[str] | None = None,
) -> list[ExerciseSlot]:
    """Ordered strength slots mapped onto compound/accessory (gym) or resistance (home)."""
    loc = (location or "gym").strip().lower()
    _ = no_equipment
    if loc not in {"gym", "home"}:
        loc = "gym"
    c_block = _compound_block(loc)
    i_block = _iso_block(loc)
    key = normalize_split_role(split_role)
    n_c = max(0, int(compound_n))
    n_i = max(0, int(accessory_n))

    if loc == "home" and session_minutes:
        from app.services.schedule_spec_master import snap_session_minutes

        explicit = _home_slots_for_minutes(
            key,
            snap_session_minutes(int(session_minutes)),
            c_block=c_block,
            i_block=i_block,
            experience_level=int(experience_level or 2),
            day_index=int(day_index or 0),
            focus_keys=focus_areas,
        )
        if explicit:
            return _maybe_strip_bar_slots(explicit, allow_bar_moves=allow_bar_moves)

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
        compounds, isos = _pull_compounds(c_block), _pull_isos(i_block)
    elif key in {"legs", "lower"}:
        total_leg = n_c + n_i
        if total_leg >= 2 and n_c < 2:
            n_c = 2
            n_i = max(0, total_leg - 2)
        compounds, isos = _leg_compounds(c_block), _leg_isos(i_block, compound_n=n_c)
    elif key == "upper":
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
    if slot.prefer and blob:
        rank = next((i for i, needle in enumerate(slot.prefer) if needle and needle in blob), None)
        if rank is not None:
            score += 40 + (len(slot.prefer) - rank)
    if not _shoulder_head_ok(slot, d):
        return None
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
    if not _shoulder_head_ok(slot, d):
        return False
    return True


def _shoulder_head_ok(slot: ExerciseSlot, d: dict[str, Any]) -> bool:
    """Generic shoulder slugs only count when the name is the right delt head."""
    if slot.key == "push_delt":
        specific = {"shoulders-front", "shoulders-lateral"}
        names = _PUSH_DELT_NAMES
    elif slot.key == "rear_delt":
        specific = {"shoulders-rear", "shoulders-traps"}
        names = _PULL_DELT_NAMES
    else:
        return True
    muscle = _muscle(d)
    if muscle in specific:
        return True
    if muscle not in _GENERIC_SHOULDER_SLUGS:
        return False
    blob = _blob(d)
    return any(needle in blob for needle in names)


def preferred_shoulder_pick(
    slot_key: str,
    pool: list,
    *,
    blocked: set[int],
) -> int | None:
    """One shoulder per day: front raise before lateral, reverse fly before shrug."""
    needles = _PUSH_DELT_NAMES if slot_key == "push_delt" else _PULL_DELT_NAMES if slot_key == "rear_delt" else None
    if not needles:
        return None
    ranked: list[tuple[int, int, int]] = []
    for raw in pool:
        d = raw if isinstance(raw, dict) else _as_dict(raw)
        try:
            eid = int(d.get("id") or d.get("exercise_id"))
        except (TypeError, ValueError):
            continue
        if eid in blocked:
            continue
        blob = _blob(d)
        rank = next((i for i, needle in enumerate(needles) if needle and needle in blob), None)
        if rank is None:
            continue
        bw = bool(d.get("bw")) or (
            d.get("equipment_slugs") is not None and not d.get("equipment_slugs")
        )
        ranked.append((1 if bw else 0, rank, eid))
    if not ranked:
        return None
    ranked.sort()
    return ranked[0][2]


def slot_prefer_rank(slot: ExerciseSlot, row: dict[str, Any]) -> int:
    """Index of the first matching `prefer` needle (earlier = better); unmatched last."""
    if not slot.prefer:
        return 1
    blob = _blob(row)
    if not blob:
        return len(slot.prefer)
    for i, needle in enumerate(slot.prefer):
        if needle and needle in blob:
            return i
    return len(slot.prefer)


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
        elif slot.key in {"hinge", "push_delt", "rear_delt"}:
            pool.sort(
                key=lambda x: (slot_prefer_rank(slot, x), int(x["id"]))
            )
        else:
            pool.sort(key=lambda x: int(x["id"]))
        out[slot.key] = pool
    return out


_SLOT_LABEL_VI = {
    "h_press": "Ngực compound",
    "v_press": "Vai compound",
    "push_delt": "Vai trước / vai giữa",
    "rear_delt": "Vai sau / cầu vai",
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
    """Serialize session slots + pools for the rule picker."""
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
        out.setdefault("_slot_picks", {}).setdefault(slot.key, []).append(eid)

    return out
