"""Build exercise shortlists per session block."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import not_, or_
from sqlalchemy.orm import Session

from app.models.entities import Equipment, Exercise, ExerciseEquipment, MuscleGroup
from app.services.exercise_catalog_classify import (
    difficulty_band_for_experience,
    roles_for_block,
    target_difficulty_for_experience,
    venues_for_location,
)
from app.services.session_blocks import BlockSpec
from app.services.workout_generation.focus import FOCUS_SHORTLIST_BONUS, is_focus_muscle
from app.services.workout_generation.gym_implements import has_gym_load, is_gym_load_slug
from app.services.workout_generation.injury_filters import InjuryConstraints
from app.services.workout_generation.cardio_finishers import (
    filter_challenge_cardio_items,
    is_challenge_cardio_name,
)
from app.services.workout_generation.split_map import (
    is_denied_for_split,
    is_stretch_slug,
    muscle_hints_for_split,
    patterns_for_split,
)
from app.services.workout_generation.weekly_volume import fold_lift_name

def _prefer_easy_home_cardio(
    *,
    location: str | None,
    split_role: str | None,
    block_key: str,
    experience_level: int,
    user_slugs: Iterable[str] | None,
    duration_min: int | None,
) -> bool:
    if block_key not in {"cardio", "conditioning"}:
        return False
    role = (split_role or "").strip().lower()
    if role == "core" and int(duration_min or 0) >= 30:
        return True
    if (location or "").strip().lower() != "home":
        return False
    if int(experience_level or 2) <= 1:
        return True
    user = {str(s).strip().lower() for s in (user_slugs or ()) if str(s).strip()}
    return "jump-rope" not in user


SHORTLIST_CAP = 40
_BAND_FAMILY = frozenset({"resistance-band", "resistance-band-1", "resistance-band-2"})
_BAR_SLUGS = frozenset({"pull-up-bar", "parallel-bars"})
_STRENGTH_PICK_BLOCKS = frozenset({"compound", "accessory", "resistance", "conditioning"})
_GYM_LOADED_MIN = 6
_HOME_DENIED_NAME_KEYS = ("xe trượt", "xe truot", "sled")
# Specialty implements treated as bodyweight when unlinked; allow only if user has the slug.
_SPECIALTY_GEAR_RULES: tuple[tuple[tuple[str, ...], frozenset[str]], ...] = (
    (
        ("wall ball", "ném bóng", "nem bong"),
        frozenset({"wall-ball"}),
    ),
    (
        ("medicine ball",),
        frozenset({"medicine-ball"}),
    ),
    (
        ("slam ball",),
        frozenset({"slam-ball"}),
    ),
    (
        ("stability ball", "swiss ball", "bóng ổn định", "bong on dinh", "bóng yoga", "bong yoga"),
        frozenset(),
    ),
    (
        (
            "captain's chair",
            "captains chair",
            "captain chair",
            "captains-chair",
            "ghế captain",
            "ghe captain",
            "nâng gối ghế treo",
            "nang goi ghe treo",
        ),
        frozenset({"parallel-bars"}),
    ),
    (
        (
            "gymnastic ring",
            "gymnastic rings",
            "gymnastics ring",
            "ring dip",
            "ring row",
            "ring push",
            "ring pull",
            "ring hang",
            "ring stretch",
            "ring pec",
            "ring lat",
            "ring face",
            "ring hold",
            "vòng treo",
            "vong treo",
            "giãn ngực vòng",
            "gian nguc vong",
            "giãn xô vòng",
            "gian xo vong",
            "bay vai sau vòng",
            "giữ vòng treo",
            "giu vong treo",
        ),
        frozenset({"gymnastic-rings"}),
    ),
)
_BAR_NAME_KEYS = (
    "xà đơn",
    "xa don",
    "xà kép",
    "xa kep",
    "hít xà",
    "hit xa",
    "kéo xà",
    "keo xa",
    "pull-up",
    "pullup",
    "pull up",
    "chin-up",
    "chinup",
    "chin up",
    "hanging",
    "treo người",
    "treo nguoi",
    "muscle-up",
    "muscle up",
)
_ROW_NAME_KEYS = (
    "chèo người",
    "cheo nguoi",
    "chèo",
    "cheo",
    "lying row",
    "inverted row",
    "australian row",
    "inverted",
    "australian",
)
_INVERTED_ROW_KEYS = (
    "lying row",
    "inverted row",
    "australian row",
    "inverted",
    "australian",
    "chèo người",
    "cheo nguoi",
)
_CABLE_BB_ROW_KEYS = (
    "cable row",
    "seated cable",
    "barbell row",
    "chèo tạ đòn",
    "cheo ta don",
    "chèo cáp",
    "cheo cap",
    "machine row",
    "máy chèo",
    "may cheo",
)
_BAND_ROW_KEYS = (
    "band row",
    "band-row",
    "chèo dây",
    "cheo day",
    "kéo ngang dây",
    "keo ngang day",
    "face pull dây",
    "face pull day",
)
_HOME_IMPROVISED_NEEDLES = (
    "towel",
    "table",
    "backpack",
    "self-resisted",
    "improvised",
    "khăn",
    "khan",
    "bàn",
    "ban ",
    "ba lô",
    "ba lo",
    "tự cản",
    "tu can",
)


def expand_equipment_aliases(slugs: Iterable[str] | None) -> set[str]:
    """Bidirectional band aliases so UI `-1`/`-2` matches catalog `resistance-band`."""
    out: set[str] = set()
    for raw in slugs or ():
        s = str(raw or "").strip().lower()
        if not s:
            continue
        out.add(s)
        if s in _BAND_FAMILY:
            out.update(_BAND_FAMILY)
    return out


def expand_selected_equipment(slugs: Iterable[str] | None) -> list[str]:
    """Public 'Dây kháng lực' uses both loop (-1) and tube (-2) catalogs when generating."""
    out: list[str] = []
    seen: set[str] = set()
    has_band = False
    for raw in slugs or ():
        s = str(raw or "").strip().lower()
        if not s:
            continue
        if s in _BAND_FAMILY:
            has_band = True
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    if has_band:
        for slug in ("resistance-band-1", "resistance-band-2"):
            if slug in seen:
                continue
            seen.add(slug)
            out.append(slug)
    return out


def exercise_gear_allowed(exercise_slugs: Iterable[str] | None, user_expanded: set[str]) -> bool:
    """True when every linked slug is covered by the user's gear (after aliases)."""
    required = {str(s or "").strip().lower() for s in (exercise_slugs or ()) if str(s or "").strip()}
    if not required:
        return True
    if not user_expanded:
        return False
    for slug in required:
        aliases = expand_equipment_aliases((slug,))
        if aliases.isdisjoint(user_expanded):
            return False
    return True


def _blob_has_row_name(blob: str) -> bool:
    """True for chèo / inverted / a standalone 'row' token (not 'throw')."""
    if any(k in blob for k in _ROW_NAME_KEYS):
        return True
    padded = f" {blob.replace('-', ' ')} "
    return " row " in padded


def is_home_improvised_exercise(
    name_vi: str | None = None, name_en: str | None = None
) -> bool:
    """Towel / table / backpack home pulls — eligible without gym gear."""
    blob = f"{name_vi or ''} {name_en or ''}".strip().lower()
    if not blob:
        return False
    return any(k in blob for k in _HOME_IMPROVISED_NEEDLES)


def is_bar_rings_denied_home_exercise(
    name_vi: str | None = None, name_en: str | None = None
) -> bool:
    """Table/bar inverted row and backpack good-morning — not for bar/rings plans."""
    blob = fold_lift_name(f"{name_vi or ''} {name_en or ''}")
    if not blob:
        return False
    return any(k in blob for k in _BAR_RINGS_DENIED_NEEDLES)


def _is_allowed_band_row(blob: str, user: set[str], *, no_equipment: bool) -> bool:
    """Tube/loop band rows are OK at home when the user selected a band."""
    if no_equipment or not (user & _BAND_FAMILY):
        return False
    if any(k in blob for k in _INVERTED_ROW_KEYS):
        return False
    if any(k in blob for k in _CABLE_BB_ROW_KEYS):
        return False
    if any(k in blob for k in _BAND_ROW_KEYS):
        return True
    has_row = "row" in blob or "chèo" in blob or "cheo" in blob
    has_band = "band" in blob or "dây" in blob or " day" in f" {blob} "
    return has_row and has_band


_FREE_WEIGHT_ROW_SLUGS = frozenset({"dumbbell", "kettlebell"})
_FREE_WEIGHT_ROW_NEEDLES = ("tạ đơn", "ta don", "dumbbell", "tạ ấm", "ta am", "kettlebell")
_RING_SLUGS = frozenset({"gymnastic-rings"})
_BAR_RINGS_GEAR_SLUGS = frozenset({"pull-up-bar", "gymnastic-rings"})
# Improvised / bar-lying rows — drop when the user already has a bar or rings.
_BAR_RINGS_DENIED_NEEDLES = (
    "keo nguoi nam tren xa",
    "bar inverted",
    "pull-up bar inverted",
    "pull up bar inverted",
    "keo nguoi duoi ban",
    "table inverted",
    "cui nguoi om balo",
    "backpack good morning",
)
_RING_PULL_NAME_NEEDLES = (
    "gymnastic ring",
    "gymnastic rings",
    "ring row",
    "ring pull",
    "ring chin",
    "chèo vòng",
    "cheo vong",
    "hít xà vòng",
    "hit xa vong",
    "kéo vòng",
    "keo vong",
    "vòng treo",
    "vong treo",
)
# Pull-up family only (not dips) — used for weak pullups_max gating.
_PULLUP_FAMILY_NEEDLES = (
    "hít xà",
    "hit xa",
    "kéo xà",
    "keo xa",
    "pull-up",
    "pullup",
    "pull up",
    "chin-up",
    "chinup",
    "chin up",
    "muscle-up",
    "muscle up",
)


def _is_allowed_free_weight_row(
    blob: str, linked: set[str], user: set[str], *, no_equipment: bool
) -> bool:
    """Dumbbell / kettlebell rows are home-legal when the user owns that implement."""
    if no_equipment or not user:
        return False
    if any(k in blob for k in _INVERTED_ROW_KEYS):
        return False
    if any(k in blob for k in _CABLE_BB_ROW_KEYS):
        return False
    if linked:
        if not (linked & _FREE_WEIGHT_ROW_SLUGS):
            return False
        return exercise_gear_allowed(linked, user)
    return any(k in blob for k in _FREE_WEIGHT_ROW_NEEDLES) and bool(
        user & _FREE_WEIGHT_ROW_SLUGS
    )


def _is_allowed_ring_pull(
    blob: str, linked: set[str], user: set[str], *, no_equipment: bool
) -> bool:
    """Ring row / ring pull-up are home-legal when the user owns gymnastic rings."""
    if no_equipment or not (user & _RING_SLUGS):
        return False
    if linked:
        if not (linked & _RING_SLUGS):
            return False
        return exercise_gear_allowed(linked, user)
    return any(k in blob for k in _RING_PULL_NAME_NEEDLES)


def _pullups_too_weak(fitness_baseline: dict[str, Any] | None) -> bool:
    """True only when pullups_max is present and ≤ 2 (missing/null = unknown, not weak)."""
    if not isinstance(fitness_baseline, dict) or "pullups_max" not in fitness_baseline:
        return False
    raw = fitness_baseline.get("pullups_max")
    if raw is None:
        return False
    try:
        return int(raw) <= 2
    except (TypeError, ValueError):
        return False


def _is_unassisted_pullup_family(
    name_vi: str | None = None, name_en: str | None = None
) -> bool:
    """Raw pull-up / chin-up / muscle-up — not dips or inverted rows."""
    blob = f"{name_vi or ''} {name_en or ''}".strip().lower()
    if not blob:
        return False
    if any(k in blob for k in _L1_BAR_OK_NEEDLES):
        return False
    return any(k in blob for k in _PULLUP_FAMILY_NEEDLES)


_L1_BAR_OK_NEEDLES = (
    "assisted",
    "trợ lực",
    "tro luc",
    "band-assist",
    "band assist",
    "scapular",
    "inverted",
    "australian",
    "chèo người",
    "cheo nguoi",
    "ring row",
    "chèo vòng",
    "cheo vong",
)
_JUMP_ROPE_NEEDLES = (
    "jump rope",
    "jump-rope",
    "jumprope",
    "nhảy dây",
    "nhay day",
    "dây nhảy",
    "day nhay",
    "skipping rope",
    "skipping",
)


def is_jump_rope_name(name_vi: str | None = None, name_en: str | None = None) -> bool:
    blob = f"{name_vi or ''} {name_en or ''}".strip().lower()
    return any(k in blob for k in _JUMP_ROPE_NEEDLES)


_HIIT_CARDIO_KEYS = (
    "high knee",
    "gối cao",
    "goi cao",
    "burpee",
    "sprint",
    "jumping",
    "mountain climber",
    "leo núi",
    "leo nui",
    "nhảy dang",
    "nhay dang",
    "nhảy",
    "nhay",
)


def is_hiit_cardio_name(
    name_vi: str | None = None,
    name_en: str | None = None,
    *,
    pattern: str | None = None,
    muscle_slug: str | None = None,
) -> bool:
    """True for high-intensity bodyweight cardio names (not jump rope)."""
    if is_jump_rope_name(name_vi, name_en):
        return False
    blob = " ".join(
        str(x or "").lower() for x in (pattern, muscle_slug, name_vi, name_en)
    )
    return any(k in blob for k in _HIIT_CARDIO_KEYS)


_L1_UNASSISTED_NEEDLES = (
    "hít xà",
    "hit xa",
    "kéo xà",
    "keo xa",
    "pull-up",
    "pullup",
    "pull up",
    "chin-up",
    "chinup",
    "chin up",
    "muscle-up",
    "muscle up",
    "xà kép",
    "xa kep",
)


def is_unassisted_bar_skill(name_vi: str | None = None, name_en: str | None = None) -> bool:
    """True for raw pull-up / chin-up / dip / muscle-up (not assisted or inverted row)."""
    blob = f"{name_vi or ''} {name_en or ''}".strip().lower()
    if not blob:
        return False
    if any(k in blob for k in _L1_BAR_OK_NEEDLES):
        return False
    if any(k in blob for k in _L1_UNASSISTED_NEEDLES):
        return True
    padded = f" {blob.replace('-', ' ')} "
    if " dip " in padded or padded.startswith("dip ") or " dips " in padded:
        return True
    return False


def is_home_denied_exercise(
    *,
    name_vi: str | None = None,
    name_en: str | None = None,
    location: str | None,
    no_equipment: bool,
    user_slugs: Iterable[str] | None = None,
    experience_level: int | None = None,
    exercise_slugs: Iterable[str] | None = None,
    fitness_baseline: dict[str, Any] | None = None,
) -> bool:
    """Sled / bar-required names must not appear on home plans without that gear.

    ``exercise_slugs`` (linked `exercise_equipment`) lets a row that only needs gear
    the user selected — e.g. "Chèo tạ đơn" with dumbbells — pass the home row denial.
    Gymnastic-rings rows/pull-ups are allowed when the user owns rings.
    Unassisted pull-ups are denied at L1 unless the fitness test allows pull-up
    progress (``pullups_max > 0`` or an inverted-row regression). Dips / muscle-up
    stay L1-denied. Weak ``pullups_max`` (present and ≤ 2) still blocks raw pull-ups.
    """
    loc = (location or "").strip().lower()
    if loc != "home" and not no_equipment:
        return False
    blob = f"{name_vi or ''} {name_en or ''}".strip().lower()
    if any(k in blob for k in _HOME_DENIED_NAME_KEYS):
        return True
    user = expand_equipment_aliases(user_slugs)
    linked = {str(s or "").strip().lower() for s in (exercise_slugs or ()) if str(s or "").strip()}
    if (user & _BAR_RINGS_GEAR_SLUGS) and is_bar_rings_denied_home_exercise(
        name_vi, name_en
    ):
        return True
    for needles, slugs in _SPECIALTY_GEAR_RULES:
        if any(k in blob for k in needles) and (no_equipment or not (user & slugs)):
            return True
    has_bar = bool(user & _BAR_SLUGS)
    if (no_equipment or loc == "home") and not has_bar:
        bar_hit = any(k in blob for k in _BAR_NAME_KEYS) or (
            "xà" in blob or " xa " in f" {blob} "
        )
        row_hit = _blob_has_row_name(blob)
        if bar_hit or row_hit:
            if _is_allowed_ring_pull(blob, linked, user, no_equipment=no_equipment):
                pass
            elif row_hit and (
                is_home_improvised_exercise(name_vi, name_en)
                or _is_allowed_band_row(blob, user, no_equipment=no_equipment)
                or _is_allowed_free_weight_row(
                    blob, linked, user, no_equipment=no_equipment
                )
            ):
                pass
            else:
                return True
    if loc == "home" and is_unassisted_bar_skill(name_vi, name_en):
        from app.services.workout_generation.skill_gate import (
            allow_unassisted_pull_progress,
            is_l1_forever_bar_skill,
        )

        if is_l1_forever_bar_skill(name_vi, name_en):
            if int(experience_level or 99) <= 1:
                return True
            return False
        if _is_unassisted_pullup_family(name_vi, name_en):
            if _pullups_too_weak(fitness_baseline):
                return True
            if allow_unassisted_pull_progress(fitness_baseline):
                return False
            if int(experience_level or 99) <= 1:
                return True
            return False
        if int(experience_level or 99) <= 1:
            return True
    return False


def normalize_location_gear(
    location: str | None,
    *,
    no_equipment: bool = False,
    equipment_slugs: Iterable[str] | None = None,
) -> tuple[str | None, bool, list[str]]:
    """Normalize wizard location/gear. Home with an empty list is treated as bodyweight."""
    loc = (location or "").strip().lower() or None
    if loc not in {"home", "gym"}:
        loc = None
    raw = [str(s).strip().lower() for s in (equipment_slugs or ()) if str(s).strip()]
    no_eq = bool(no_equipment)
    if loc == "home" and not no_eq and not raw:
        no_eq = True
    return loc, no_eq, raw


def location_from_venue(venue: str | None) -> str | None:
    """Infer home/gym from a source exercise when plan insights are missing."""
    v = (venue or "").strip().lower()
    if v == "home":
        return "home"
    if v == "gym":
        return "gym"
    return None


def venue_sql_filter(location: str | None, *, no_equipment: bool = False):
    """Strict venue clause when location is known — null/empty venue does not pass."""
    loc = (location or "").strip().lower()
    if loc in {"home", "gym"} or no_equipment:
        allowed = venues_for_location(loc if loc in {"home", "gym"} else location, no_equipment=no_equipment)
        return Exercise.venue.in_(sorted(allowed))
    return or_(
        Exercise.venue.in_(["gym", "home", "both"]),
        Exercise.venue.is_(None),
        Exercise.venue == "",
    )


def exercise_passes_location_gear(
    *,
    venue: str | None,
    equipment_slugs: Iterable[str] | None,
    name_vi: str | None = None,
    name_en: str | None = None,
    location: str | None,
    no_equipment: bool = False,
    user_slugs: Iterable[str] | None = None,
    experience_level: int | None = None,
    fitness_baseline: dict[str, Any] | None = None,
) -> bool:
    """True when the exercise matches venue + equipment for this plan context."""
    loc, no_eq, raw = normalize_location_gear(
        location, no_equipment=no_equipment, equipment_slugs=user_slugs
    )
    if loc in {"home", "gym"} or no_eq:
        allowed = venues_for_location(loc, no_equipment=no_eq)
        v = (venue or "").strip().lower()
        if v not in allowed:
            return False
    linked = {str(s).strip().lower() for s in (equipment_slugs or ()) if str(s).strip()}
    if is_home_denied_exercise(
        name_vi=name_vi,
        name_en=name_en,
        location=loc or location,
        no_equipment=no_eq,
        user_slugs=raw,
        experience_level=experience_level,
        exercise_slugs=linked,
        fitness_baseline=fitness_baseline,
    ):
        return False
    if no_eq:
        return not linked
    user_expanded = expand_equipment_aliases(raw)
    if loc == "home" and raw:
        return exercise_gear_allowed(linked, user_expanded)
    if loc == "gym" and raw:
        if not linked:
            return False
        return bool(expand_equipment_aliases(linked) & user_expanded)
    return True


def apply_catalog_location_sql(
    q,
    db: Session,
    *,
    location: str | None,
    no_equipment: bool = False,
    equipment_slugs: Iterable[str] | None = None,
    ai_suggest_equipment: bool = False,
):
    """Apply venue + equipment SQL to an Exercise query. Returns (q, loc, no_eq, raw, expanded)."""
    loc, no_eq, raw = normalize_location_gear(
        location, no_equipment=no_equipment, equipment_slugs=equipment_slugs
    )
    if loc == "home":
        ai_suggest_equipment = False
    q = q.filter(venue_sql_filter(loc, no_equipment=no_eq))
    user_expanded = expand_equipment_aliases(raw)
    if no_eq:
        linked = db.query(ExerciseEquipment.exercise_id)
        q = q.filter(not_(Exercise.id.in_(linked)))
    elif loc == "home" and not ai_suggest_equipment and raw:
        eq_ids = [
            r[0]
            for r in db.query(Equipment.id).filter(Equipment.slug.in_(sorted(user_expanded))).all()
        ]
        unlinked = db.query(ExerciseEquipment.exercise_id)
        if eq_ids:
            linked_selected = db.query(ExerciseEquipment.exercise_id).filter(
                ExerciseEquipment.equipment_id.in_(eq_ids)
            )
            q = q.filter(
                or_(
                    Exercise.id.in_(linked_selected),
                    not_(Exercise.id.in_(unlinked)),
                )
            )
        else:
            q = q.filter(not_(Exercise.id.in_(unlinked)))
    elif loc == "gym" and not ai_suggest_equipment and raw:
        eq_ids = [
            r[0]
            for r in db.query(Equipment.id).filter(Equipment.slug.in_(sorted(user_expanded))).all()
        ]
        if eq_ids:
            q = q.filter(
                Exercise.id.in_(
                    db.query(ExerciseEquipment.exercise_id).filter(
                        ExerciseEquipment.equipment_id.in_(eq_ids)
                    )
                )
            )
    return q, loc, no_eq, raw, user_expanded


@dataclass(frozen=True)
class ShortlistItem:
    id: int
    name_vi: str
    movement_role: str | None
    movement_pattern: str | None
    muscle_slug: str
    difficulty: int
    name_en: str | None = None
    # Linked `exercise_equipment` slugs; empty = bodyweight. Drives home gear-first tiering.
    equipment_slugs: frozenset[str] = frozenset()


def score_candidate(
    *,
    pattern: str,
    muscle_slug: str,
    difficulty: int,
    movement_role: str | None,
    venue: str | None,
    equipment_slugs: set[str],
    preferred_patterns: frozenset[str],
    muscle_hints: frozenset[str],
    focus_slugs: frozenset[str] | None,
    allowed_diff: frozenset[int],
    experience_level: int,
    block_role: str | None,
    block_key: str,
    location: str | None,
    goal: str | None = None,
    name_vi: str | None = None,
    name_en: str | None = None,
    no_equipment: bool = False,
    prefer_easy_cardio: bool = False,
    user_slugs: Iterable[str] | None = None,
    fitness_baseline: dict[str, Any] | None = None,
) -> int:
    """Higher is better. Gym strength work prefers loaded implements over calisthenics."""
    score = 0
    if pattern in preferred_patterns:
        score += 30
    if muscle_slug in muscle_hints:
        score += 15
    if block_key in {"compound", "resistance"}:
        pass
    elif focus_slugs and is_focus_muscle(muscle_slug, focus_slugs):
        if not muscle_hints or muscle_slug in muscle_hints:
            score += FOCUS_SHORTLIST_BONUS
    if difficulty in allowed_diff:
        target = target_difficulty_for_experience(experience_level)
        delta = abs(int(difficulty) - target)
        if delta == 0:
            score += 8
        elif delta == 1:
            score += 4
        else:
            score += 1
    ex_role = (movement_role or "").strip().lower()
    if block_role and ex_role == block_role:
        score += 10
    if block_key in _STRENGTH_PICK_BLOCKS and preferred_patterns:
        if pattern not in preferred_patterns and block_key != "core":
            score -= 40
    loc = (location or "").strip().lower()
    user = expand_equipment_aliases(user_slugs)
    if loc == "gym" and block_key in _STRENGTH_PICK_BLOCKS:
        if has_gym_load(equipment_slugs):
            score += 24
        else:
            score -= 30
        v = (venue or "").strip().lower()
        if v == "gym":
            score += 8
    if loc == "home" and block_key in _STRENGTH_PICK_BLOCKS:
        if equipment_slugs & _BAND_FAMILY:
            score += 12
        blob_names = f"{name_vi or ''} {name_en or ''}".lower()
        if any(k in blob_names for k in ("band", "dây kháng", "day khang")):
            score += 8
        if user:
            if expand_equipment_aliases(equipment_slugs) & user:
                score += 16
            if is_home_improvised_exercise(name_vi, name_en):
                score -= 12
        weak_pu = _pullups_too_weak(fitness_baseline)
        if int(experience_level or 2) <= 1 or weak_pu:
            from app.services.workout_generation.skill_gate import (
                allow_unassisted_pull_progress,
                is_l1_forever_bar_skill,
            )

            pull_ok = allow_unassisted_pull_progress(fitness_baseline)
            if is_l1_forever_bar_skill(name_vi, name_en) and int(experience_level or 2) <= 1:
                score -= 120
            elif _is_unassisted_pullup_family(name_vi, name_en) and (
                not pull_ok or weak_pu
            ):
                score -= 120
            elif is_unassisted_bar_skill(name_vi, name_en) and not (
                _is_unassisted_pullup_family(name_vi, name_en) and pull_ok and not weak_pu
            ):
                if int(experience_level or 2) <= 1 or _is_unassisted_pullup_family(
                    name_vi, name_en
                ):
                    score -= 120
            elif any(
                k in blob_names
                for k in (
                    "assisted",
                    "scapular",
                    "inverted",
                    "australian",
                    "band row",
                    "chèo dây",
                    "cheo day",
                    "ring row",
                    "chèo vòng",
                    "cheo vong",
                    "vòng treo",
                    "vong treo",
                )
            ):
                score += 20
    g = (goal or "").strip().lower()
    if block_key in {"cardio", "conditioning"}:
        blob = " ".join(
            str(x or "").lower()
            for x in (pattern, muscle_slug, name_vi, name_en)
        )
        rope = is_jump_rope_name(name_vi, name_en)
        hiit = is_hiit_cardio_name(
            name_vi,
            name_en,
            pattern=pattern,
            muscle_slug=muscle_slug,
        )
        easy = any(
            k in blob
            for k in (
                "xe đạp",
                "xe dap",
                "bike",
                "đi bộ",
                "di bo",
                "walk",
                "march",
                "tread",
                "elliptic",
                "máy chèo",
                "may cheo",
            )
        )
        if rope and "jump-rope" in user:
            score += 80
        elif prefer_easy_cardio:
            if easy:
                score += 60
            if hiit:
                score -= 80
        elif g in {"gain_weight", "gain_muscle"}:
            if easy:
                score += 24
            if hiit:
                score -= 40
        elif loc == "home":
            if easy:
                score += 40
            if hiit:
                score -= 40
    if block_key == "cooldown":
        blob = (name_vi or "").lower()
        if is_stretch_slug(muscle_slug) or "giãn" in blob or "gian" in blob:
            score += 20
        if muscle_slug in muscle_hints:
            score += 10
    return score


def _equipment_slugs_by_exercise(db: Session, ids: list[int]) -> dict[int, set[str]]:
    out: dict[int, set[str]] = {i: set() for i in ids}
    if not ids:
        return out
    rows = (
        db.query(ExerciseEquipment.exercise_id, Equipment.slug)
        .join(Equipment, Equipment.id == ExerciseEquipment.equipment_id)
        .filter(ExerciseEquipment.exercise_id.in_(ids))
        .all()
    )
    for eid, slug in rows:
        out.setdefault(int(eid), set()).add(str(slug or "").strip().lower())
    return out


def _gym_load_equipment_ids(db: Session) -> list[int]:
    cached = db.info.get("_gym_load_equipment_ids")
    if cached is not None:
        return cached
    ids: list[int] = []
    for eid, slug in db.query(Equipment.id, Equipment.slug).all():
        if is_gym_load_slug(slug):
            ids.append(int(eid))
    db.info["_gym_load_equipment_ids"] = ids
    return ids


def _item_from_row(
    ex: Exercise, mg: MuscleGroup, eq_slugs: Iterable[str] | None = None
) -> ShortlistItem:
    return ShortlistItem(
        id=ex.id,
        name_vi=ex.name_vi,
        movement_role=ex.movement_role,
        movement_pattern=ex.movement_pattern,
        muscle_slug=mg.slug,
        difficulty=int(ex.difficulty),
        name_en=getattr(ex, "name_en", None),
        equipment_slugs=frozenset(
            str(s).strip().lower() for s in (eq_slugs or ()) if str(s).strip()
        ),
    )


def _load_filtered_rows(
    db: Session,
    *,
    split_role: str | None,
    experience_level: int,
    equipment_slugs: list[str] | None,
    no_equipment: bool,
    ai_suggest_equipment: bool,
    exclude_ids: set[int] | None = None,
    location: str | None = None,
    injury: InjuryConstraints | None = None,
    movement_roles: Iterable[str] | None = None,
    block_key: str | None = None,
    count_max: int = 0,
    fitness_baseline: dict[str, Any] | None = None,
) -> list[tuple[Exercise, MuscleGroup, set[str]]]:
    """SQL + venue/gear/injury/split filters. No ranking or SHORTLIST_CAP."""
    exclude_ids = exclude_ids or set()
    allowed_diff = difficulty_band_for_experience(experience_level)
    loc, no_equipment, raw_user = normalize_location_gear(
        location, no_equipment=no_equipment, equipment_slugs=equipment_slugs
    )
    if loc == "home":
        ai_suggest_equipment = False
    injury = injury or InjuryConstraints()
    key = str(block_key or "")
    roles = {str(r).strip().lower() for r in (movement_roles or ()) if str(r).strip()}

    q = (
        db.query(Exercise, MuscleGroup)
        .join(MuscleGroup, MuscleGroup.id == Exercise.muscle_group_id)
        .filter(
            Exercise.is_active.is_(True),
            Exercise.difficulty.in_(sorted(allowed_diff)),
        )
    )
    q, loc, no_equipment, raw_user, _user_expanded = apply_catalog_location_sql(
        q,
        db,
        location=loc,
        no_equipment=no_equipment,
        equipment_slugs=raw_user,
        ai_suggest_equipment=ai_suggest_equipment,
    )
    if roles:
        q = q.filter(Exercise.movement_role.in_(sorted(roles)))

    preferred_patterns = patterns_for_split(split_role)
    if key == "core":
        q = q.filter(
            (Exercise.movement_pattern == "core")
            | (MuscleGroup.slug.in_(["core", "co-bung", "waist"]))
        )

    strength_pick = key in _STRENGTH_PICK_BLOCKS or bool(
        roles & {"compound", "isolation", "resistance", "conditioning"}
    )
    if (
        loc == "gym"
        and not no_equipment
        and not ai_suggest_equipment
        and not raw_user
        and strength_pick
    ):
        load_eq = _gym_load_equipment_ids(db)
        if load_eq:
            loaded_ex = db.query(ExerciseEquipment.exercise_id).filter(
                ExerciseEquipment.equipment_id.in_(load_eq)
            )
            n_loaded = q.filter(Exercise.id.in_(loaded_ex)).count()
            if n_loaded >= max(_GYM_LOADED_MIN, int(count_max or 0) * 2, 4):
                q = q.filter(Exercise.id.in_(loaded_ex))

    rows = q.all()
    if not isinstance(rows, (list, tuple)):
        return []
    ids = [int(ex.id) for ex, _mg in rows if ex.id not in exclude_ids]
    eq_map = _equipment_slugs_by_exercise(db, ids)

    relax_patterns = False
    while True:
        out: list[tuple[Exercise, MuscleGroup, set[str]]] = []
        for ex, mg in rows:
            if ex.id in exclude_ids:
                continue
            eq_slugs = eq_map.get(int(ex.id), set())
            if not exercise_passes_location_gear(
                venue=ex.venue,
                equipment_slugs=eq_slugs,
                name_vi=ex.name_vi,
                name_en=getattr(ex, "name_en", None),
                location=loc,
                no_equipment=no_equipment,
                user_slugs=raw_user,
                experience_level=experience_level,
                fitness_baseline=fitness_baseline,
            ):
                continue
            pattern = (ex.movement_pattern or "").strip().lower()
            if strength_pick and is_denied_for_split(
                split_role, pattern=pattern, muscle_slug=mg.slug
            ):
                continue
            if injury.blocks_exercise(
                pattern=pattern,
                muscle_slug=mg.slug,
                name_vi=ex.name_vi,
                ignore_patterns=relax_patterns,
            ):
                continue
            out.append((ex, mg, eq_slugs))
        if out or relax_patterns or not (injury.denied_patterns or injury.denied_families):
            return out
        relax_patterns = True
        if not injury.relaxed_patterns:
            injury.relaxed_patterns = True
            injury.notes_vi.append("Đã nới lọc khớp để vẫn đủ bài an toàn.")


def query_filtered_exercises(
    db: Session,
    *,
    split_role: str | None,
    experience_level: int,
    equipment_slugs: list[str] | None,
    no_equipment: bool,
    ai_suggest_equipment: bool,
    exclude_ids: set[int] | None = None,
    location: str | None = None,
    injury: InjuryConstraints | None = None,
    pushups_max: int | None = None,
    fitness_baseline: dict[str, Any] | None = None,
    movement_roles: Iterable[str] | None = None,
    block_key: str | None = None,
    count_max: int = 0,
    challenge: bool = False,
) -> list[ShortlistItem]:
    """Every catalog exercise matching user filters. No SHORTLIST_CAP."""
    from app.services.workout_generation.weekly_volume import (
        drop_standard_pushups_if_knee_available,
        prefer_knee_pushups,
    )

    loc, no_eq, _raw = normalize_location_gear(
        location, no_equipment=no_equipment, equipment_slugs=equipment_slugs
    )
    rows = _load_filtered_rows(
        db,
        split_role=split_role,
        experience_level=experience_level,
        equipment_slugs=equipment_slugs,
        no_equipment=no_equipment,
        ai_suggest_equipment=ai_suggest_equipment,
        exclude_ids=exclude_ids,
        location=location,
        injury=injury,
        movement_roles=movement_roles,
        block_key=block_key,
        count_max=count_max,
        fitness_baseline=fitness_baseline,
    )
    items = [_item_from_row(ex, mg, eq) for ex, mg, eq in rows]
    if challenge and str(block_key or "") in {"cardio", "conditioning"}:
        items = filter_challenge_cardio_items(items)
    want_knee = prefer_knee_pushups(
        location=loc or location,
        no_equipment=no_eq,
        pushups_max=pushups_max,
        fitness_baseline=fitness_baseline,
    )
    key = str(block_key or "")
    roles = {str(r).strip().lower() for r in (movement_roles or ()) if str(r).strip()}
    strength_pick = key in _STRENGTH_PICK_BLOCKS or bool(
        roles & {"compound", "isolation", "resistance", "conditioning"}
    )
    if want_knee and strength_pick and not challenge:
        items = drop_standard_pushups_if_knee_available(items, name_of=lambda it: it.name_vi)
    from app.services.workout_generation.skill_ladder import filter_pool_by_ladder

    items = filter_pool_by_ladder(items, fitness_baseline, phase_i=0)
    items.sort(key=lambda it: int(it.id))
    return items


def narrow_preferred_shortlist(
    scored: list[tuple[int, ShortlistItem]],
    *,
    block_key: str,
    preferred_patterns: frozenset[str],
    split_role: str | None,
    count_max: int,
) -> list[tuple[int, ShortlistItem]]:
    """Keep isolation/quota extras when shrinking to preferred patterns.

    Skip the shrink if the merged pool would be thinner than the recipe needs.
    """
    if block_key not in _STRENGTH_PICK_BLOCKS or not preferred_patterns:
        return scored
    preferred_scored = [
        (s, it) for s, it in scored if (it.movement_pattern or "") in preferred_patterns
    ]
    from app.services.workout_generation.muscle_quotas import keep_outside_preferred_pattern

    quota_scored = [
        (s, it)
        for s, it in scored
        if keep_outside_preferred_pattern(
            split_role,
            muscle_slug=it.muscle_slug,
            pattern=it.movement_pattern,
        )
    ]
    if len(preferred_scored) < min(3, SHORTLIST_CAP // 2):
        return scored
    merged: dict[int, tuple[int, ShortlistItem]] = {}
    for s, it in preferred_scored + quota_scored:
        merged[it.id] = (s, it)
    min_keep = max(int(count_max or 0) * 2, 8)
    if len(merged) < min_keep:
        return scored
    return list(merged.values())


def build_shortlist(
    db: Session,
    *,
    block: BlockSpec,
    split_role: str | None,
    experience_level: int,
    equipment_slugs: list[str] | None,
    no_equipment: bool,
    ai_suggest_equipment: bool,
    exclude_ids: set[int] | None = None,
    location: str | None = None,
    focus_slugs: frozenset[str] | None = None,
    goal: str | None = None,
    injury: InjuryConstraints | None = None,
    pushups_max: int | None = None,
    fitness_baseline: dict[str, Any] | None = None,
    challenge: bool = False,
) -> list[ShortlistItem]:
    """Candidate exercises for one block (max SHORTLIST_CAP)."""
    if block.count_max <= 0 and block.block_key == "ramp_sets":
        return []

    exclude_ids = exclude_ids or set()
    preferred_patterns = patterns_for_split(split_role)
    muscle_hints = muscle_hints_for_split(split_role)
    allowed_diff = difficulty_band_for_experience(experience_level)
    loc, no_equipment, raw_user = normalize_location_gear(
        location, no_equipment=no_equipment, equipment_slugs=equipment_slugs
    )
    from app.services.workout_generation.weekly_volume import (
        drop_standard_pushups_if_knee_available,
        is_knee_pushup_name,
        prefer_knee_pushups,
    )

    want_knee = prefer_knee_pushups(
        location=loc or location,
        no_equipment=no_equipment,
        pushups_max=pushups_max,
        fitness_baseline=fitness_baseline,
    )
    allowed_roles = roles_for_block(block.movement_role, location=loc or location)
    role = (block.movement_role or "").strip().lower() or None
    rows = _load_filtered_rows(
        db,
        split_role=split_role,
        experience_level=experience_level,
        equipment_slugs=equipment_slugs,
        no_equipment=no_equipment,
        ai_suggest_equipment=ai_suggest_equipment,
        exclude_ids=exclude_ids,
        location=location,
        injury=injury,
        movement_roles=allowed_roles,
        block_key=block.block_key,
        count_max=int(block.count_max or 0),
        fitness_baseline=fitness_baseline,
    )

    scored: list[tuple[int, ShortlistItem]] = []
    prefer_easy = _prefer_easy_home_cardio(
        location=loc or location,
        split_role=split_role,
        block_key=block.block_key,
        experience_level=experience_level,
        user_slugs=raw_user,
        duration_min=block.duration_min_minutes,
    )
    deny_hiit = block.block_key in {"cardio", "conditioning"} and (
        prefer_easy or (bool(no_equipment) and (loc or location or "").strip().lower() == "home")
    )
    challenge_cardio = challenge and block.block_key in {"cardio", "conditioning"}
    user_has_rope = "jump-rope" in expand_equipment_aliases(raw_user)
    for ex, mg, eq_slugs in rows:
        allowlisted = challenge_cardio and is_challenge_cardio_name(
            ex.name_vi, getattr(ex, "name_en", None)
        )
        if not allowlisted:
            if deny_hiit and is_hiit_cardio_name(
                ex.name_vi,
                getattr(ex, "name_en", None),
                pattern=(ex.movement_pattern or "").strip().lower(),
                muscle_slug=mg.slug,
            ):
                continue
            if (
                deny_hiit
                and is_jump_rope_name(ex.name_vi, getattr(ex, "name_en", None))
                and not user_has_rope
            ):
                continue
        pattern = (ex.movement_pattern or "").strip().lower()
        score = score_candidate(
            pattern=pattern,
            muscle_slug=mg.slug,
            difficulty=int(ex.difficulty),
            movement_role=ex.movement_role,
            venue=ex.venue,
            equipment_slugs=eq_slugs,
            preferred_patterns=preferred_patterns,
            muscle_hints=muscle_hints,
            focus_slugs=focus_slugs,
            allowed_diff=allowed_diff,
            experience_level=experience_level,
            block_role=role,
            block_key=block.block_key,
            location=loc or location,
            goal=goal,
            name_vi=ex.name_vi,
            name_en=getattr(ex, "name_en", None),
            no_equipment=no_equipment,
            user_slugs=raw_user,
            prefer_easy_cardio=prefer_easy,
            fitness_baseline=fitness_baseline,
        )
        if want_knee and is_knee_pushup_name(ex.name_vi, getattr(ex, "name_en", None)):
            score += 40
        scored.append((-score, _item_from_row(ex, mg, eq_slugs)))

    scored = narrow_preferred_shortlist(
        scored,
        block_key=block.block_key,
        preferred_patterns=preferred_patterns,
        split_role=split_role,
        count_max=int(block.count_max or 0),
    )

    scored.sort(key=lambda x: (x[0], x[1].id))
    ranked = [item for _, item in scored]
    if challenge and block.block_key in {"cardio", "conditioning"}:
        ranked = filter_challenge_cardio_items(ranked)

    if want_knee and block.block_key in _STRENGTH_PICK_BLOCKS and not challenge:
        ranked = drop_standard_pushups_if_knee_available(ranked, name_of=lambda it: it.name_vi)

    from app.services.workout_generation.skill_ladder import filter_pool_by_ladder

    ranked = filter_pool_by_ladder(ranked, fitness_baseline, phase_i=0)

    if block.block_key in _STRENGTH_PICK_BLOCKS and preferred_patterns and ranked:
        from app.services.workout_generation.coverage import family_of

        divers: list[ShortlistItem] = []
        seen_fam: set[str] = set()
        for it in ranked:
            fam = family_of(it.movement_pattern)
            if fam and fam not in seen_fam and (it.movement_pattern or "") in preferred_patterns:
                divers.append(it)
                seen_fam.add(fam)
            if len(divers) >= SHORTLIST_CAP:
                break
        for it in ranked:
            if it in divers:
                continue
            divers.append(it)
            if len(divers) >= SHORTLIST_CAP:
                break
        return divers[:SHORTLIST_CAP]

    return ranked[:SHORTLIST_CAP]


def shortlist_to_prompt_dicts(
    items: list[ShortlistItem], *, mark_bw: bool = False
) -> list[dict]:
    """Prompt rows. `mark_bw` adds `bw: 1` on bodyweight items only (home + gear)."""
    out: list[dict] = []
    for i in items:
        row: dict = {
            "id": i.id,
            "name_vi": i.name_vi,
            "movement_role": i.movement_role,
            "movement_pattern": i.movement_pattern,
            "muscle": i.muscle_slug,
            "muscle_slug": i.muscle_slug,
            "difficulty": i.difficulty,
        }
        if i.name_en:
            row["name_en"] = i.name_en
        if mark_bw and not i.equipment_slugs:
            row["bw"] = 1
        out.append(row)
    return out
