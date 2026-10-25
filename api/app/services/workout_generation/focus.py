"""Map UI focus_areas → muscle slugs."""

from __future__ import annotations

from typing import Any

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

MAX_FOCUS_AREAS = 3
FOCUS_CANONICAL: tuple[str, ...] = (
    "nguc",
    "lung",
    "mong",
    "chan",
    "bung",
    "vai",
    "tay",
)
FOCUS_ALIAS: dict[str, str] = {
    "eo": "bung",
    "mo_lung": "lung",
    "vai_thon": "vai",
    "tay_to": "tay",
}

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
    "nguc": "ngực",
    "lung": "lưng",
    "mong": "mông",
    "chan": "chân",
    "bung": "bụng",
    "vai": "vai",
    "tay": "tay",
    "eo": "bụng",
    "mo_lung": "lưng",
    "vai_thon": "vai",
    "tay_to": "tay",
}

FOCUS_SHORTLIST_BONUS = 20

_ROLE_EXTRA_KIND: dict[str, dict[str, str]] = {
    "push": {"nguc": "chest", "vai": "shoulder", "tay": "triceps"},
    "pull": {"lung": "back", "vai": "rear", "tay": "biceps"},
    "legs": {"chan": "quad", "mong": "glute"},
    "lower": {"chan": "quad", "mong": "glute"},
    "upper": {"nguc": "chest", "lung": "back", "vai": "shoulder", "tay": "biceps"},
}

_ROLE_BASE_KINDS: dict[str, list[str]] = {
    "push": ["chest", "shoulder", "triceps"],
    "pull": ["back", "rear", "biceps"],
    "legs": ["legs", "quad", "ham"],
    "lower": ["legs", "quad", "ham"],
    "upper": ["chest", "back", "shoulder"],
}

_ROLE_DEFAULT_EXTRA: dict[str, str] = {
    "push": "chest",
    "pull": "back",
    "legs": "calf",
    "lower": "calf",
    "upper": "biceps",
}

_KIND_FOCUS: dict[str, str] = {
    "chest": "nguc",
    "shoulder": "vai",
    "triceps": "tay",
    "back": "lung",
    "rear": "vai",
    "biceps": "tay",
    "legs": "chan",
    "quad": "chan",
    "ham": "chan",
    "calf": "chan",
    "glute": "mong",
    "hinge": "mong",
    "abs": "bung",
}


def normalize_focus_key(raw: Any) -> str | None:
    key = str(raw or "").strip().lower()
    if not key:
        return None
    key = FOCUS_ALIAS.get(key, key)
    if key in FOCUS_CANONICAL:
        return key
    return None


def normalize_focus_areas(focus_areas: list[str] | None) -> list[str]:
    out: list[str] = []
    for raw in focus_areas or []:
        key = normalize_focus_key(raw)
        if key and key not in out:
            out.append(key)
        if len(out) >= MAX_FOCUS_AREAS:
            break
    return out


def extra_focus_kind(role: str | None, focus_keys: list[str] | None) -> str | None:
    mapping = _ROLE_EXTRA_KIND.get(str(role or "").strip().lower()) or {}
    for key in focus_keys or []:
        kind = mapping.get(str(key).strip().lower())
        if kind:
            return kind
    return None


def sixty_push_pull_kinds(role: str | None, extra: str | None) -> list[str] | None:
    """60-minute push/pull layout: 2–2–1, or swap one shoulder for arms."""
    key = str(role or "").strip().lower()
    if key == "push":
        if extra == "triceps":
            return ["chest", "chest", "shoulder", "triceps", "triceps"]
        return ["chest", "chest", "shoulder", "shoulder", "triceps"]
    if key == "pull":
        if extra == "biceps":
            return ["back", "back", "rear", "biceps", "biceps"]
        return ["back", "back", "rear", "rear", "biceps"]
    return None


def resistance_kind_list(
    role: str | None,
    slots: int,
    focus_keys: list[str] | None = None,
) -> list[str]:
    """Ordered kit kinds for a home session. Extra isolation only when slots >= 4."""
    key = str(role or "").strip().lower()
    n = max(1, int(slots or 1))
    base = list(_ROLE_BASE_KINDS.get(key) or [])
    if not base:
        return []
    if n <= 3:
        return base[:n]
    extra = extra_focus_kind(key, focus_keys)
    sixty = sixty_push_pull_kinds(key, extra)
    if sixty:
        return sixty
    if n >= 5 and key in {"legs", "lower"}:
        return ["legs", "quad", "ham", "glute", "calf"]
    if n >= 5 and key == "upper":
        return ["chest", "back", "back", "shoulder", "biceps"]
    if key in {"legs", "lower"}:
        extra = _ROLE_DEFAULT_EXTRA.get(key)
    else:
        extra = extra or _ROLE_DEFAULT_EXTRA.get(key)
    if not extra:
        return base[:n]
    out = list(base)
    last = max((i for i, kind in enumerate(out) if kind == extra), default=None)
    if last is None:
        out.append(extra)
    else:
        out.insert(last + 1, extra)
    return out[:n]


def focus_muscle_slugs(focus_areas: list[str] | None) -> frozenset[str]:
    slugs: set[str] = set()
    for key in normalize_focus_areas(list(focus_areas or [])):
        slugs |= FOCUS_TO_SLUGS.get(key, frozenset())
    return frozenset(slugs)


def focus_labels_vi(focus_areas: list[str] | None) -> list[str]:
    out: list[str] = []
    for key in normalize_focus_areas(list(focus_areas or [])):
        label = FOCUS_LABEL_VI.get(key)
        if label and label not in out:
            out.append(label)
    return out


def is_focus_muscle(muscle_slug: str | None, focus_slugs: frozenset[str]) -> bool:
    if not focus_slugs:
        return False
    return str(muscle_slug or "").strip().lower() in focus_slugs


def _meta_slug(meta: Any) -> str:
    if isinstance(meta, dict):
        return str(meta.get("muscle_slug") or meta.get("muscle") or "").strip().lower()
    return str(getattr(meta, "muscle_slug", None) or getattr(meta, "muscle", None) or "").strip().lower()


def _slug_matches_focus(slug: str, focus_key: str) -> bool:
    wanted = FOCUS_TO_SLUGS.get(focus_key) or frozenset()
    if slug in wanted:
        return True
    parent = slug.split("-", 1)[0] if slug else ""
    return bool(parent and (parent in wanted or any(parent == w.split("-", 1)[0] for w in wanted)))


def _is_core_focus_slug(slug: str) -> bool:
    s = str(slug or "").strip().lower()
    if not s:
        return False
    if s in CORE_SLUGS or s in {"bung", "core"}:
        return True
    parent = s.split("-", 1)[0]
    return parent in {"core", "bung"} or s.startswith("core")


def bump_focus_sets(
    plan_days: list[Any],
    *,
    session_minutes: int,
    focus_keys: list[str] | None,
    meta_by_id: dict[int, Any] | None,
    experience_level: int = 2,
    skip_test_lift: bool = False,
) -> None:
    """45-minute sessions: +1 set on focus-region mains when an extra lift does not fit.

    ``skip_test_lift`` prefers an accessory in the same region (P3 challenge).
    """
    keys = normalize_focus_areas(list(focus_keys or []))
    if not keys:
        return
    try:
        minutes = int(session_minutes or 45)
    except (TypeError, ValueError):
        minutes = 45
    if minutes > 45:
        return
    from app.services.schedule_spec_master import snap_session_minutes
    from app.services.workout_generation.dose_bounds import dose_bounds_for_item

    if snap_session_minutes(minutes) > 45:
        return
    meta = meta_by_id or {}
    level = max(1, int(experience_level or 2))

    def _bump(ex: Any, *, eid: int, section: str, ceiling_floor: int) -> None:
        try:
            current = max(1, int(getattr(ex, "sets", 0) or 0))
        except (TypeError, ValueError):
            current = 1
        bounds = dose_bounds_for_item(
            meta.get(eid) or {},
            experience_level=level,
            plan_section=section,
            home_session=True,
            challenge=True,
        )
        ceiling = int(bounds.get("sets_max") or (3 if level <= 1 else 4))
        if skip_test_lift:
            ceiling = max(ceiling, ceiling_floor, 4)
        ex.sets = min(ceiling, current + 1)

    for day in plan_days or []:
        items = list(getattr(day, "exercises", None) or [])
        test_id: int | None = None
        if skip_test_lift:
            for ex in items:
                section = str(getattr(ex, "section", "main") or "main")
                if section not in {"main", "exercises"}:
                    continue
                try:
                    eid = int(ex.exercise_id)
                except (TypeError, ValueError):
                    continue
                if _is_core_focus_slug(_meta_slug(meta.get(eid))):
                    continue
                test_id = eid
                break
        bumped: set[str] = set()
        for prefer_accessory in (True, False) if skip_test_lift else (False,):
            if bumped and prefer_accessory:
                continue
            for ex in items:
                section = str(getattr(ex, "section", "main") or "main")
                if section not in {"main", "core"}:
                    continue
                try:
                    eid = int(ex.exercise_id)
                except (TypeError, ValueError):
                    continue
                if skip_test_lift and prefer_accessory and test_id is not None and eid == test_id:
                    continue
                if skip_test_lift and (not prefer_accessory) and eid != test_id:
                    continue
                slug = _meta_slug(meta.get(eid))
                for focus_key in keys:
                    if focus_key in bumped:
                        continue
                    if not _slug_matches_focus(slug, focus_key):
                        continue
                    _bump(ex, eid=eid, section=section, ceiling_floor=4)
                    bumped.add(focus_key)
                    break
