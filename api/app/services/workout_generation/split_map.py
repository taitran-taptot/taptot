"""Map schedule-frame split_role → preferred movement patterns + muscle slug hints."""

from __future__ import annotations

import re
from typing import Any

# Patterns from exercises.movement_pattern classifier
SPLIT_PATTERNS: dict[str, frozenset[str]] = {
    "push": frozenset({"h_push", "v_push"}),
    "pull": frozenset({"h_pull", "v_pull"}),
    "legs": frozenset({"squat", "hinge"}),
    "lower": frozenset({"squat", "hinge"}),
    "upper": frozenset({"h_push", "h_pull", "v_push", "v_pull"}),
    "fb": frozenset({"h_push", "h_pull", "v_push", "v_pull", "squat", "hinge", "core"}),
    "fb_a": frozenset({"h_push", "h_pull", "squat", "hinge", "core"}),
    "fb_b": frozenset({"v_push", "v_pull", "squat", "hinge", "core"}),
    "conditioning": frozenset({"other", "core", "squat"}),
    "core": frozenset({"core"}),
    "mobility": frozenset({"other", "core"}),
    "recovery": frozenset({"other", "core", "hinge"}),
}

# Canonical EN slugs preferred; keep VI / legacy aliases for DBs not yet remapped.
_UPPER_MUSCLE = frozenset(
    {
        "chest",
        "co-nguc",
        "back",
        "co-lung",
        "shoulders",
        "shoulders-deltoids",
        "co-vai",
        "triceps",
        "co-tay-sau",
        "biceps",
        "co-tay-truoc",
    }
)
_LEG_MUSCLE = frozenset(
    {
        "quads",
        "hamstrings",
        "glutes",
        "calves",
        "co-dui-truoc",
        "co-dui-sau",
        "co-mong",
        "co-bap-chan",
        "upper-legs",
        "lower-legs",
    }
)

# Optional muscle_groups.slug preferences (soft filter boost, not hard reject)
SPLIT_MUSCLE_SLUG_HINTS: dict[str, frozenset[str]] = {
    "push": frozenset(
        {
            "chest",
            "shoulders",
            "shoulders-deltoids",
            "triceps",
            "co-nguc",
            "co-vai",
            "co-tay-sau",
        }
    ),
    "pull": frozenset(
        {
            "back",
            "co-lung",
            "biceps",
            "co-tay-truoc",
            "shoulders",
            "shoulders-deltoids",
            "shoulders-rear",
            "co-vai",
        }
    ),
    "legs": _LEG_MUSCLE,
    "lower": _LEG_MUSCLE,
    "upper": _UPPER_MUSCLE,
    "fb": _UPPER_MUSCLE | _LEG_MUSCLE | frozenset({"core", "co-bung", "waist"}),
    "fb_a": _UPPER_MUSCLE | _LEG_MUSCLE | frozenset({"core", "co-bung", "waist"}),
    "fb_b": _UPPER_MUSCLE | _LEG_MUSCLE | frozenset({"core", "co-bung", "waist"}),
    "core": frozenset({"core", "co-bung", "waist"}),
    "mobility": frozenset({"stretch", "gian-co", "core", "co-bung", "waist"}),
    "recovery": frozenset({"stretch", "gian-co", "core", "co-bung", "waist"}),
}

# Aliases → canonical split_role (future / typos); keep frames stable.
SPLIT_ROLE_ALIASES: dict[str, str] = {
    "full": "fb",
    "full_body": "fb",
    "fullbody": "fb",
    "ul": "upper",
    "leg": "legs",
}

# Hard rejects so focus scoring cannot leak laterals onto leg days.
DENIED_PATTERNS: dict[str, frozenset[str]] = {
    "legs": frozenset({"h_push", "v_push", "h_pull", "v_pull"}),
    "lower": frozenset({"h_push", "v_push", "h_pull", "v_pull"}),
    "push": frozenset({"h_pull", "v_pull", "squat", "hinge"}),
    "pull": frozenset({"h_push", "v_push", "squat", "hinge"}),
    "upper": frozenset({"squat", "hinge"}),
}

DENIED_MUSCLE_SLUGS: dict[str, frozenset[str]] = {
    "legs": frozenset(
        {
            "chest",
            "co-nguc",
            "back",
            "co-lung",
            "shoulders",
            "shoulders-deltoids",
            "co-vai",
            "biceps",
            "co-tay-truoc",
            "triceps",
            "co-tay-sau",
        }
    ),
    "lower": frozenset(
        {
            "chest",
            "co-nguc",
            "back",
            "co-lung",
            "shoulders",
            "shoulders-deltoids",
            "co-vai",
            "biceps",
            "co-tay-truoc",
            "triceps",
            "co-tay-sau",
        }
    ),
    "upper": _LEG_MUSCLE,
    # Push = chest / front-lateral shoulders / triceps — not back or rear-delt pulls.
    "push": _LEG_MUSCLE
    | frozenset(
        {
            "biceps",
            "co-tay-truoc",
            "back",
            "co-lung",
            "back-lats",
            "back-middle",
            "back-lower",
            "shoulders-rear",
            "shoulders-traps",
        }
    ),
    # Pull = back / biceps / rear delt — not chest presses.
    "pull": _LEG_MUSCLE
    | frozenset(
        {
            "triceps",
            "co-tay-sau",
            "chest",
            "co-nguc",
            "chest-upper",
            "chest-mid",
            "chest-lower",
            "shoulders-front",
            "delts-front",
            "anterior-deltoid",
            "shoulders-anterior",
            "shoulders-lateral",
        }
    ),
}


def normalize_split_role(split_role: str | None) -> str:
    key = (split_role or "").strip().lower()
    if not key:
        return "fb"
    return SPLIT_ROLE_ALIASES.get(key, key)


def patterns_for_split(split_role: str | None) -> frozenset[str]:
    key = normalize_split_role(split_role)
    return SPLIT_PATTERNS.get(key, SPLIT_PATTERNS["fb"])


def muscle_hints_for_split(split_role: str | None) -> frozenset[str]:
    key = normalize_split_role(split_role)
    return SPLIT_MUSCLE_SLUG_HINTS.get(key, frozenset())


_STRETCH_SLUGS = frozenset({"stretch", "gian-co"})
_PREP_MUSCLE_SLUGS: dict[str, frozenset[str]] = {
    "push": frozenset(
        {"chest", "co-nguc", "shoulders", "shoulders-deltoids", "co-vai", "triceps", "co-tay-sau"}
    ),
    "pull": frozenset(
        {"back", "co-lung", "shoulders", "shoulders-deltoids", "co-vai", "biceps", "co-tay-truoc"}
    ),
    "legs": _LEG_MUSCLE,
    "lower": _LEG_MUSCLE,
    "upper": _UPPER_MUSCLE,
    "fb": _UPPER_MUSCLE | _LEG_MUSCLE,
    "fb_a": _UPPER_MUSCLE | _LEG_MUSCLE,
    "fb_b": _UPPER_MUSCLE | _LEG_MUSCLE,
    "core": frozenset({"core", "co-bung", "waist", "stretch", "gian-co"}),
}
_PREP_NAME_KEYS: dict[str, tuple[str, ...]] = {
    "push": ("ngực", "vai", "tay sau", "chest", "shoulder", "tricep"),
    "pull": ("lưng", "vai", "tay trước", "back", "lat", "bicep"),
    "legs": ("đùi", "mông", "bắp", "hông", "gối", "quad", "hamstring", "calf", "glute", "hip"),
    "lower": ("đùi", "mông", "bắp", "hông", "gối", "quad", "hamstring", "calf", "glute", "hip"),
    "upper": ("ngực", "lưng", "vai", "tay", "chest", "back", "shoulder"),
    "fb": ("hông", "vai", "lưng", "ngực", "đùi"),
    "fb_a": ("hông", "vai", "lưng", "ngực", "đùi"),
    "fb_b": ("hông", "vai", "lưng", "ngực", "đùi"),
    "core": ("bụng", "lưng", "core", "plank"),
}


def prep_muscle_slugs_for_split(split_role: str | None) -> frozenset[str]:
    key = normalize_split_role(split_role)
    return _PREP_MUSCLE_SLUGS.get(key, _UPPER_MUSCLE | _LEG_MUSCLE)


def is_stretch_slug(muscle_slug: str | None) -> bool:
    return str(muscle_slug or "").strip().lower() in _STRETCH_SLUGS


_REGION_BY_SLUG: dict[str, str] = {
    "chest": "chest",
    "co-nguc": "chest",
    "chest-upper": "chest",
    "chest-mid": "chest",
    "chest-lower": "chest",
    "shoulders": "shoulders",
    "shoulders-deltoids": "shoulders",
    "co-vai": "shoulders",
    "shoulders-front": "shoulders",
    "shoulders-lateral": "shoulders",
    "shoulders-rear": "shoulders",
    "shoulders-traps": "shoulders",
    "triceps": "triceps",
    "co-tay-sau": "triceps",
    "back": "back",
    "co-lung": "back",
    "back-lats": "back",
    "back-middle": "back",
    "back-lower": "back",
    "biceps": "biceps",
    "co-tay-truoc": "biceps",
    "quads": "quads",
    "quad": "quads",
    "co-dui-truoc": "quads",
    "upper-legs": "quads",
    "hamstrings": "hamstrings",
    "co-dui-sau": "hamstrings",
    "glutes": "glutes",
    "co-mong": "glutes",
    "calves": "calves",
    "co-bap-chan": "calves",
    "lower-legs": "calves",
}
_REGION_NAME_KEYS: dict[str, tuple[str, ...]] = {
    "chest": ("ngực", "nguc", "chest", "pec"),
    "shoulders": ("vai", "shoulder", "delt"),
    "triceps": ("tay sau", "tricep"),
    "back": ("lưng", "lung", "back", "lat", "xô", "xo "),
    "biceps": ("tay trước", "tay truoc", "bicep"),
    "quads": ("đùi trước", "dui truoc", "quad"),
    "hamstrings": ("đùi sau", "dui sau", "hamstring"),
    "glutes": ("mông", "mong", "glute"),
    "calves": ("bắp chân", "bap chan", "calf"),
}


def region_for_muscle(muscle_slug: str | None) -> str | None:
    return _REGION_BY_SLUG.get(str(muscle_slug or "").strip().lower())


def is_stretch_item(item: Any) -> bool:
    slug = ""
    name = ""
    if isinstance(item, dict):
        slug = str(item.get("muscle_slug") or item.get("muscle") or "")
        name = f"{item.get('name_vi') or ''} {item.get('name_en') or ''}"
    else:
        slug = str(getattr(item, "muscle_slug", None) or getattr(item, "muscle", None) or "")
        name = f"{getattr(item, 'name_vi', '') or ''} {getattr(item, 'name_en', '') or ''}"
    blob = name.lower()
    return is_stretch_slug(slug) or "giãn" in blob or "gian " in blob or "stretch" in blob


# Bodyweight stretches whose catalog muscle is just "stretch", so the name is the region.
CANONICAL_STRETCH_NAMES: dict[str, tuple[str, ...]] = {
    "back": (
        "child's pose",
        "childs pose",
        "tư thế em bé",
        "tu the em be",
        "seated spinal twist",
        "spinal twist",
        "xoay cột sống",
        "xoay cot song",
        "cat-cow",
        "cat cow",
        "mèo bò",
        "meo bo",
    ),
    "chest": (
        "doorway chest",
        "giãn ngực tại khung",
        "gian nguc tai khung",
        "floor chest",
        "standing chest opener",
        "chest opener",
    ),
}


def _name_key_hit(key: str, blob: str) -> bool:
    if key == "lat":
        return re.search(r"(?<![a-z])lat(?![a-z])", blob) is not None
    return key in blob


def stretch_matches_region(item: Any, region: str) -> bool:
    keys = _REGION_NAME_KEYS.get(region, ())
    if isinstance(item, dict):
        slug = str(item.get("muscle_slug") or item.get("muscle") or "")
        blob = f"{item.get('name_vi') or ''} {item.get('name_en') or ''}".lower()
    else:
        slug = str(getattr(item, "muscle_slug", None) or getattr(item, "muscle", None) or "")
        blob = f"{getattr(item, 'name_vi', '') or ''} {getattr(item, 'name_en', '') or ''}".lower()
    if any(needle in blob for needle in CANONICAL_STRETCH_NAMES.get(region, ())):
        return True
    if region_for_muscle(slug) == region and not is_stretch_slug(slug):
        return True
    return any(_name_key_hit(k, blob) for k in keys)


_SLUG_NAME_KEYS: dict[str, tuple[str, ...]] = {
    "chest": ("ngực", "chest"),
    "co-nguc": ("ngực", "chest"),
    "back": ("lưng", "back", "lat"),
    "co-lung": ("lưng", "back", "lat"),
    "shoulders": ("vai", "shoulder"),
    "shoulders-deltoids": ("vai", "shoulder"),
    "co-vai": ("vai", "shoulder"),
    "triceps": ("tay sau", "tricep"),
    "co-tay-sau": ("tay sau", "tricep"),
    "biceps": ("tay trước", "bicep"),
    "co-tay-truoc": ("tay trước", "bicep"),
    "quads": ("đùi trước", "quad"),
    "co-dui-truoc": ("đùi trước", "quad"),
    "hamstrings": ("đùi sau", "hamstring", "ham"),
    "co-dui-sau": ("đùi sau", "hamstring", "ham"),
    "glutes": ("mông", "glute"),
    "co-mong": ("mông", "glute"),
    "calves": ("bắp chân", "calf"),
    "co-bap-chan": ("bắp chân", "calf"),
}


def _name_keys_for_slugs(slugs: frozenset[str]) -> tuple[str, ...]:
    keys: list[str] = []
    seen: set[str] = set()
    for slug in slugs:
        for k in _SLUG_NAME_KEYS.get(slug, ()):
            if k not in seen:
                seen.add(k)
                keys.append(k)
    return tuple(keys)


def mobility_match_rank(
    *,
    muscle_slug: str | None,
    name_vi: str | None = None,
    split_role: str | None = None,
    cooldown: bool = False,
    trained_slugs: frozenset[str] | None = None,
    gear_match: bool | None = None,
) -> int:
    """Lower is better. Prefers muscles trained today, then the split region."""
    slug = str(muscle_slug or "").strip().lower()
    name = str(name_vi or "").strip().lower()
    region = prep_muscle_slugs_for_split(split_role)
    split_keys = _PREP_NAME_KEYS.get(normalize_split_role(split_role), ())
    trained = frozenset(s.strip().lower() for s in (trained_slugs or ()) if s)
    trained_keys = _name_keys_for_slugs(trained) if trained else ()
    split_hit = any(k in name for k in split_keys)
    trained_hit = slug in trained or any(k in name for k in trained_keys)
    in_split = slug in region or split_hit
    stretch = is_stretch_slug(slug) or "giãn" in name
    if cooldown:
        if stretch and trained_hit:
            return -1 if gear_match else 0
        if stretch and (in_split or split_hit):
            return 1
        if stretch:
            return 2
        if trained_hit:
            return 3
        if in_split:
            return 4
        return 5
    if trained_hit and not stretch:
        return 0
    if in_split and not stretch:
        return 1
    if trained_hit:
        return 2
    if in_split:
        return 3
    if stretch:
        return 4
    return 5


def is_denied_for_split(
    split_role: str | None,
    *,
    pattern: str | None = None,
    muscle_slug: str | None = None,
) -> bool:
    key = normalize_split_role(split_role)
    pat = str(pattern or "").strip().lower()
    slug = str(muscle_slug or "").strip().lower()
    if pat and pat in DENIED_PATTERNS.get(key, frozenset()):
        return True
    if slug and slug in DENIED_MUSCLE_SLUGS.get(key, frozenset()):
        return True
    return False


def all_seed_split_roles() -> frozenset[str]:
    return frozenset(SPLIT_PATTERNS.keys())
