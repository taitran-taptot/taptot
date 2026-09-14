"""Challenge-100-day exercise variation: chest A/B angles + per-phase swaps.

Only used when curriculum / challenge_100_days is on. Angle is inferred from
exercise names (no DB column). Does not re-call OpenAI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.schemas.plans import PlanDayIn, PlanExerciseIn
from app.services.workout_generation.muscle_quotas import (
    BACK_SLUGS,
    CHEST_SLUGS,
    HINGE_MUSCLE_SLUGS,
    QUAD_SLUGS,
    SHOULDER_SLUGS,
    TRICEPS_SLUGS,
)

BenchAngle = Literal["flat", "incline", "decline", "unknown"]
ChestVariant = Literal["A", "B"]  # A=flat+incline; B=flat+incline other implement

_DECLINE_KEYS = (
    "decline",
    "dốc xuống",
    "doc xuong",
    "dốc dưới",
    "doc duoi",
)
_INCLINE_KEYS = (
    "incline",
    "dốc lên",
    "doc len",
    "dốc cao",
    "doc cao",
    "dốc trên",
    "doc tren",
)
_FLAT_KEYS = (
    "flat",
    "ngang",
    "bench press",
    "chest press",
    "đẩy ngực",
    "day nguc",
    "barbell bench",
    "dumbbell bench",
    "đẩy ngực nằm",
)
_DIP_KEYS = ("dip", "dips", "song song", "xà kép", "xa kep")
_TRICEPS_PRESS_NEEDLES = (
    "tate",
    "skull",
    "extension",
    "pushdown",
    "kickback",
    "ép tay sau",
    "ep tay sau",
    "jm press",
)
_EASY_ISO_KEYS = ("cable", "cáp", "cap ", "machine", "máy", "may ", "fly", "pec", "ép ngực", "ep nguc")


@dataclass(frozen=True)
class VariationCandidate:
    id: int
    name_vi: str = ""
    name_en: str | None = None
    muscle_slug: str = ""
    movement_pattern: str = ""
    movement_role: str = ""
    angle: BenchAngle = "unknown"

    @property
    def blob(self) -> str:
        return f"{self.name_vi or ''} {self.name_en or ''}".strip().lower()


@dataclass
class ChallengeVariationReport:
    chest_ab: list[dict[str, Any]] = field(default_factory=list)
    fallbacks: list[str] = field(default_factory=list)
    swaps_per_phase: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def as_insight(self) -> dict[str, Any]:
        return {
            "chest_ab": list(self.chest_ab),
            "fallbacks": list(self.fallbacks),
            "swaps_per_phase": {k: list(v) for k, v in self.swaps_per_phase.items()},
        }


def classify_bench_angle(name_vi: str | None = None, name_en: str | None = None) -> BenchAngle:
    blob = f"{name_vi or ''} {name_en or ''}".strip().lower()
    if not blob:
        return "unknown"
    if any(k in blob for k in _DECLINE_KEYS):
        return "decline"
    if any(k in blob for k in _INCLINE_KEYS):
        return "incline"
    if any(k in blob for k in _DIP_KEYS):
        # Dips approximate decline / lower-chest bias when decline is missing.
        return "decline"
    if any(k in blob for k in _FLAT_KEYS):
        return "flat"
    # Generic chest press without angle → treat as flat anchor.
    if "press" in blob and ("chest" in blob or "ngực" in blob or "nguc" in blob):
        return "flat"
    if "đẩy ngực" in blob or "day nguc" in blob:
        return "flat"
    return "unknown"


def candidate_from_meta(eid: int, meta: dict[str, Any]) -> VariationCandidate:
    name_vi = str(meta.get("name_vi") or "")
    name_en = meta.get("name_en")
    name_en_s = str(name_en) if name_en else None
    return VariationCandidate(
        id=int(eid),
        name_vi=name_vi,
        name_en=name_en_s,
        muscle_slug=str(meta.get("muscle_slug") or "").strip().lower(),
        movement_pattern=str(meta.get("movement_pattern") or "").strip().lower(),
        movement_role=str(meta.get("movement_role") or "").strip().lower(),
        angle=classify_bench_angle(name_vi, name_en_s),
    )


def build_variation_pool(
    *,
    meta_by_id: dict[int, dict[str, Any]] | None = None,
    extra_items: list[dict[str, Any]] | None = None,
) -> list[VariationCandidate]:
    """Build candidate pool from meta map and/or shortlist-like dicts."""
    by_id: dict[int, VariationCandidate] = {}
    for eid, meta in (meta_by_id or {}).items():
        by_id[int(eid)] = candidate_from_meta(int(eid), meta or {})
    for raw in extra_items or []:
        try:
            eid = int(raw.get("id") or raw.get("exercise_id"))
        except (TypeError, ValueError):
            continue
        meta = {
            "name_vi": raw.get("name_vi") or raw.get("name") or "",
            "name_en": raw.get("name_en"),
            "muscle_slug": raw.get("muscle_slug") or raw.get("muscle") or "",
            "movement_pattern": raw.get("movement_pattern") or "",
            "movement_role": raw.get("movement_role") or "",
        }
        by_id[eid] = candidate_from_meta(eid, meta)
    return list(by_id.values())


def pool_from_day_shortlists(
    day_contexts: list[dict[str, Any]] | None,
    meta_by_id: dict[int, dict[str, Any]],
) -> list[VariationCandidate]:
    extras: list[dict[str, Any]] = []
    for ctx in day_contexts or []:
        shortlists = ctx.get("shortlists") or {}
        if isinstance(shortlists, dict):
            for items in shortlists.values():
                for item in items or []:
                    if isinstance(item, dict):
                        extras.append(item)
                    else:
                        extras.append(
                            {
                                "id": getattr(item, "id", None),
                                "name_vi": getattr(item, "name_vi", ""),
                                "name_en": getattr(item, "name_en", None),
                                "muscle_slug": getattr(item, "muscle_slug", None)
                                or getattr(item, "muscle", None),
                                "movement_pattern": getattr(item, "movement_pattern", None),
                                "movement_role": getattr(item, "movement_role", None),
                            }
                        )
    return build_variation_pool(meta_by_id=meta_by_id, extra_items=extras)


_FINISHER_ROLES = frozenset({"cardio", "conditioning", "mobility"})
_ROTATABLE_ROLES = frozenset({"isolation", "accessory", "secondary", "resistance"})


def _is_main(ex: PlanExerciseIn) -> bool:
    return (ex.section or "main") in {"main", "exercises"}


def _role(meta: dict[str, Any]) -> str:
    return str(meta.get("movement_role") or "").strip().lower()


def _session_neo_index(day: PlanDayIn, meta_by_id: dict[int, dict[str, Any]]) -> int | None:
    """First strength slot stays as the session neo; later mains may rotate by phase."""
    for i, ex in enumerate(day.exercises):
        if not _is_main(ex):
            continue
        if _role(_meta(meta_by_id, int(ex.exercise_id))) in _FINISHER_ROLES:
            continue
        return i
    return None


def _rotatable_indices(day: PlanDayIn, meta_by_id: dict[int, dict[str, Any]]) -> list[int]:
    neo = _session_neo_index(day, meta_by_id)
    out: list[int] = []
    for i, ex in enumerate(day.exercises):
        if i == neo or not _is_main(ex):
            continue
        if _role(_meta(meta_by_id, int(ex.exercise_id))) in _FINISHER_ROLES:
            continue
        out.append(i)
    return out


def _meta(meta_by_id: dict[int, dict[str, Any]], eid: int) -> dict[str, Any]:
    return meta_by_id.get(int(eid)) or {}


def _is_chest_h_push(meta: dict[str, Any]) -> bool:
    slug = str(meta.get("muscle_slug") or "").strip().lower()
    pattern = str(meta.get("movement_pattern") or "").strip().lower()
    return slug in CHEST_SLUGS and pattern == "h_push"


def _triceps_press_blob(blob: str) -> bool:
    b = (blob or "").lower()
    return any(n in b for n in _TRICEPS_PRESS_NEEDLES)


def _is_triceps_press_meta(meta: dict[str, Any]) -> bool:
    slug = str(meta.get("muscle_slug") or meta.get("muscle") or "").strip().lower()
    blob = f"{meta.get('name_vi') or ''} {meta.get('name_en') or ''}".lower()
    if _triceps_press_blob(blob):
        return True
    return slug in TRICEPS_SLUGS


def _is_real_chest_press(meta: dict[str, Any]) -> bool:
    if _is_triceps_press_meta(meta):
        return False
    blob = f"{meta.get('name_vi') or ''} {meta.get('name_en') or ''}".lower()
    if _is_chest_h_push(meta) and _is_compound(meta):
        return True
    return any(
        n in blob
        for n in ("chest press", "bench", "đẩy ngực", "day nguc", "push-up", "chống đẩy")
    )


def _is_compound(meta: dict[str, Any]) -> bool:
    role = str(meta.get("movement_role") or "").strip().lower()
    return role in {"compound", "primary", "main"} or role == ""


def _is_isolation(meta: dict[str, Any]) -> bool:
    return _role(meta) in _ROTATABLE_ROLES


def is_chest_session_day(day: PlanDayIn, meta_by_id: dict[int, dict[str, Any]]) -> bool:
    role = str(day.split_role or "").strip().lower()
    if role == "push":
        return True
    if role == "upper":
        for ex in day.exercises:
            if not _is_main(ex):
                continue
            if _is_chest_h_push(_meta(meta_by_id, int(ex.exercise_id))):
                return True
    return False


def _implement_family(blob: str) -> str:
    b = (blob or "").lower()
    if any(k in b for k in ("dumbbell", "tạ đơn", "ta don", "db ")):
        return "db"
    if any(k in b for k in ("barbell", "tạ đòn", "bb ")):
        return "bb"
    if any(k in b for k in ("machine", "máy", "may ")):
        return "machine"
    return "other"


def chest_variant_for_index(chest_index: int) -> ChestVariant:
    """0-based chest session index in the week → A or B."""
    return "A" if int(chest_index) % 2 == 0 else "B"


def _secondary_angle(variant: ChestVariant) -> BenchAngle:
    # Both variants are flat + incline; B prefers a different implement.
    return "incline"


def _pick_from_pool(
    pool: list[VariationCandidate],
    *,
    angle: BenchAngle | None = None,
    angles: set[BenchAngle] | None = None,
    muscle_slugs: frozenset[str] | None = None,
    patterns: set[str] | None = None,
    compound: bool | None = None,
    exclude_ids: set[int] | None = None,
    prefer_easy_iso: bool = False,
    require_angle: bool = False,
    prefer_implement_not: str | None = None,
) -> VariationCandidate | None:
    exclude = exclude_ids or set()
    wanted_angles = angles or ({angle} if angle else None)
    scored: list[tuple[int, VariationCandidate]] = []
    for c in pool:
        if c.id in exclude:
            continue
        if muscle_slugs is not None and c.muscle_slug not in muscle_slugs:
            continue
        if patterns is not None and c.movement_pattern not in patterns:
            continue
        if (
            compound is True
            and muscle_slugs
            and (muscle_slugs & CHEST_SLUGS)
            and (
                c.muscle_slug in TRICEPS_SLUGS
                or _triceps_press_blob(c.blob)
            )
        ):
            continue
        if compound is True and not (
            c.movement_role in {"compound", "primary", "main", ""} or c.movement_role == ""
        ):
            # empty role allowed for compounds from incomplete meta
            if c.movement_role in {"isolation", "accessory", "mobility", "cardio"}:
                continue
        if compound is False and c.movement_role in {"compound", "primary"}:
            continue
        if wanted_angles is not None:
            if c.angle not in wanted_angles:
                if require_angle:
                    continue
                # soft: unknown allowed only if not require_angle — skip unknowns for angle picks
                continue
        score = 0
        if prefer_easy_iso and any(k in c.blob for k in _EASY_ISO_KEYS):
            score += 10
        if c.angle in (wanted_angles or set()):
            score += 5
        if angle == "incline" and c.muscle_slug == "chest-upper":
            score += 8
        if prefer_implement_not and _implement_family(c.blob) != prefer_implement_not:
            score += 12
        if angles and "incline" in wanted_angles and c.muscle_slug == "chest-upper":
            score += 6
        scored.append((score, c))
    if not scored:
        return None
    scored.sort(key=lambda t: (-t[0], t[1].id))
    return scored[0][1]


def _replace_exercise_id(
    ex: PlanExerciseIn,
    new_id: int,
    *,
    meta_by_id: dict[int, dict[str, Any]],
    pool: list[VariationCandidate],
) -> PlanExerciseIn:
    e = ex.model_copy(deep=True)
    e.exercise_id = int(new_id)
    # Keep prescription; enrich meta if candidate known.
    cand = next((c for c in pool if c.id == int(new_id)), None)
    if cand and int(new_id) not in meta_by_id:
        meta_by_id[int(new_id)] = {
            "name_vi": cand.name_vi,
            "name_en": cand.name_en,
            "muscle_slug": cand.muscle_slug,
            "movement_pattern": cand.movement_pattern,
            "movement_role": cand.movement_role,
        }
    elif cand:
        m = meta_by_id.setdefault(int(new_id), {})
        m.setdefault("name_vi", cand.name_vi)
        m.setdefault("name_en", cand.name_en)
        m.setdefault("muscle_slug", cand.muscle_slug)
        m.setdefault("movement_pattern", cand.movement_pattern)
        m.setdefault("movement_role", cand.movement_role)
    return e


def _chest_compound_indices(
    day: PlanDayIn, meta_by_id: dict[int, dict[str, Any]]
) -> list[int]:
    idxs: list[int] = []
    for i, ex in enumerate(day.exercises):
        if not _is_main(ex):
            continue
        meta = _meta(meta_by_id, int(ex.exercise_id))
        if _is_triceps_press_meta(meta):
            continue
        if _is_chest_h_push(meta) and _is_compound(meta):
            idxs.append(i)
        elif _is_chest_h_push(meta) and not _is_isolation(meta):
            # Treat unspecified role + h_push chest as compound slot.
            idxs.append(i)
    return idxs


def ensure_chest_session_angles(
    day: PlanDayIn,
    *,
    variant: ChestVariant,
    pool: list[VariationCandidate],
    meta_by_id: dict[int, dict[str, Any]],
    report: ChallengeVariationReport | None = None,
) -> PlanDayIn:
    """Ensure two chest compounds cover flat + incline for the variant."""
    secondary = _secondary_angle(variant)
    idxs = _chest_compound_indices(day, meta_by_id)
    if not idxs:
        return day

    used: set[int] = {int(day.exercises[i].exercise_id) for i in idxs}
    exercises = list(day.exercises)
    flat_cand = _pick_from_pool(
        pool,
        angle="flat",
        muscle_slugs=CHEST_SLUGS,
        patterns={"h_push"},
        compound=True,
        exclude_ids=set(),
        require_angle=True,
    )
    # Prefer keeping an existing flat if already present.
    existing_flat_i: int | None = None
    for i in idxs:
        eid = int(exercises[i].exercise_id)
        meta = _meta(meta_by_id, eid)
        ang = classify_bench_angle(meta.get("name_vi"), meta.get("name_en"))
        if ang == "flat":
            existing_flat_i = i
            flat_cand = candidate_from_meta(eid, meta)
            break

    if flat_cand is None:
        # Fallback: keep first chest compound as flat neo even if unclassified.
        existing_flat_i = idxs[0]
        flat_cand = candidate_from_meta(
            int(exercises[idxs[0]].exercise_id),
            _meta(meta_by_id, int(exercises[idxs[0]].exercise_id)),
        )
        if report is not None:
            report.fallbacks.append(
                f"day{day.day_number}: no flat in pool; kept exercise {flat_cand.id} as neo"
            )

    flat_i = existing_flat_i if existing_flat_i is not None else idxs[0]
    if int(exercises[flat_i].exercise_id) != flat_cand.id:
        exercises[flat_i] = _replace_exercise_id(
            exercises[flat_i], flat_cand.id, meta_by_id=meta_by_id, pool=pool
        )
    used = {int(exercises[i].exercise_id) for i in idxs}
    used.add(flat_cand.id)

    # Secondary slot: another chest compound index, else skip (cannot invent slots).
    sec_i: int | None = None
    for i in idxs:
        if i != flat_i:
            sec_i = i
            break

    if sec_i is None:
        if report is not None:
            report.fallbacks.append(
                f"day{day.day_number}: only one chest compound; cannot place {secondary}"
            )
        return day.model_copy(update={"exercises": exercises})

    sec_cand = _pick_from_pool(
        pool,
        angle=secondary,
        muscle_slugs=CHEST_SLUGS,
        patterns={"h_push"},
        compound=True,
        exclude_ids={flat_cand.id},
        require_angle=True,
        prefer_implement_not=(
            _implement_family(flat_cand.blob) if variant == "B" else None
        ),
    )
    if sec_cand is None:
        if report is not None:
            report.fallbacks.append(
                f"day{day.day_number}: no {secondary} candidate; left exercise "
                f"{exercises[sec_i].exercise_id}"
            )
        return day.model_copy(update={"exercises": exercises})

    if int(exercises[sec_i].exercise_id) != sec_cand.id:
        exercises[sec_i] = _replace_exercise_id(
            exercises[sec_i], sec_cand.id, meta_by_id=meta_by_id, pool=pool
        )

    # Avoid two flats: if any remaining chest compound is flat, swap to unused angle.
    for i in idxs:
        if i in {flat_i, sec_i}:
            continue
        eid = int(exercises[i].exercise_id)
        meta = _meta(meta_by_id, eid)
        ang = classify_bench_angle(meta.get("name_vi"), meta.get("name_en"))
        if ang == "flat":
            alt = _pick_from_pool(
                pool,
                angles={"incline"},
                muscle_slugs=CHEST_SLUGS,
                patterns={"h_push"},
                compound=True,
                exclude_ids={flat_cand.id, sec_cand.id},
                require_angle=True,
            )
            if alt:
                exercises[i] = _replace_exercise_id(
                    exercises[i], alt.id, meta_by_id=meta_by_id, pool=pool
                )

    return day.model_copy(update={"exercises": exercises})


def apply_challenge_within_week_chest_ab(
    plan_days: list[PlanDayIn],
    *,
    pool: list[VariationCandidate],
    meta_by_id: dict[int, dict[str, Any]],
    report: ChallengeVariationReport | None = None,
) -> list[PlanDayIn]:
    """Number chest sessions in week order and apply A/B angle policy."""
    rep = report if report is not None else ChallengeVariationReport()
    out: list[PlanDayIn] = []
    chest_i = 0
    for day in plan_days:
        d = day.model_copy(deep=True)
        if is_chest_session_day(d, meta_by_id):
            variant = chest_variant_for_index(chest_i)
            d = ensure_chest_session_angles(
                d,
                variant=variant,
                pool=pool,
                meta_by_id=meta_by_id,
                report=rep,
            )
            rep.chest_ab.append(
                {
                    "day_number": d.day_number,
                    "split_role": d.split_role,
                    "chest_index": chest_i,
                    "variant": variant,
                    "angles": ["flat", _secondary_angle(variant)],
                }
            )
            chest_i += 1
        out.append(d)
    return out


def _swap_slot_to_candidate(
    exercises: list[PlanExerciseIn],
    index: int,
    cand: VariationCandidate,
    *,
    meta_by_id: dict[int, dict[str, Any]],
    pool: list[VariationCandidate],
    phase_key: str,
    report: ChallengeVariationReport,
) -> None:
    old_id = int(exercises[index].exercise_id)
    if old_id == cand.id:
        return
    exercises[index] = _replace_exercise_id(
        exercises[index], cand.id, meta_by_id=meta_by_id, pool=pool
    )
    report.swaps_per_phase.setdefault(phase_key, []).append(
        {"from": old_id, "to": cand.id, "day_exercise_index": index}
    )


def _phase_swap_day(
    day: PlanDayIn,
    *,
    phase_key: str,
    pool: list[VariationCandidate],
    meta_by_id: dict[int, dict[str, Any]],
    focus_slugs: set[str],
    report: ChallengeVariationReport,
    prefer_easy_iso: bool = False,
    swap_secondary: bool = False,
    swap_isos: int = 0,
    bias_incline_secondary: bool = False,
    avoid_ids: set[int] | None = None,
) -> PlanDayIn:
    exercises = [e.model_copy(deep=True) for e in day.exercises]
    used = {int(e.exercise_id) for e in exercises} | {int(i) for i in (avoid_ids or set())}
    working = day.model_copy(update={"exercises": exercises})
    if is_chest_session_day(working, meta_by_id):
        neo_i = _session_neo_index(working, meta_by_id)
        if neo_i is not None:
            neo_meta = _meta(meta_by_id, int(exercises[neo_i].exercise_id))
            if _is_triceps_press_meta(neo_meta):
                old_id = int(exercises[neo_i].exercise_id)
                cand = _pick_from_pool(
                    pool,
                    muscle_slugs=CHEST_SLUGS,
                    patterns={"h_push"},
                    compound=True,
                    exclude_ids=used,
                )
                if cand is not None and cand.id != old_id:
                    _swap_slot_to_candidate(
                        exercises,
                        neo_i,
                        cand,
                        meta_by_id=meta_by_id,
                        pool=pool,
                        phase_key=phase_key,
                        report=report,
                    )
                    used.discard(old_id)
                    used.add(cand.id)
                    for i, ex in enumerate(exercises):
                        if i == neo_i:
                            continue
                        if (
                            int(ex.exercise_id) == old_id
                            and str(ex.section or "") == "warmup"
                        ):
                            exercises[i] = _replace_exercise_id(
                                ex, cand.id, meta_by_id=meta_by_id, pool=pool
                            )

    chest_idxs = _chest_compound_indices(
        day.model_copy(update={"exercises": exercises}), meta_by_id
    )

    # Identify flat neo vs secondary among chest compounds.
    flat_i: int | None = None
    sec_i: int | None = None
    for i in chest_idxs:
        meta = _meta(meta_by_id, int(exercises[i].exercise_id))
        ang = classify_bench_angle(meta.get("name_vi"), meta.get("name_en"))
        if ang == "flat" and flat_i is None:
            flat_i = i
        elif sec_i is None:
            sec_i = i
    if flat_i is None and chest_idxs:
        flat_i = chest_idxs[0]
    if sec_i is None and len(chest_idxs) > 1:
        sec_i = next(i for i in chest_idxs if i != flat_i)

    if swap_secondary and sec_i is not None:
        want: BenchAngle = "incline"
        exclude = {int(exercises[flat_i].exercise_id)} if flat_i is not None else set()
        exclude.add(int(exercises[sec_i].exercise_id))
        cand = _pick_from_pool(
            pool,
            angle=want,
            muscle_slugs=CHEST_SLUGS,
            patterns={"h_push"},
            compound=True,
            exclude_ids=exclude,
            require_angle=True,
        )
        if cand is not None:
            _swap_slot_to_candidate(
                exercises,
                sec_i,
                cand,
                meta_by_id=meta_by_id,
                pool=pool,
                phase_key=phase_key,
                report=report,
            )
            used.add(cand.id)

    # Rotate later strength slots (2nd compound, isolation, home resistance).
    iso_budget = max(0, int(swap_isos))
    if prefer_easy_iso and iso_budget == 0:
        iso_budget = 1
    swapped = 0
    working = day.model_copy(update={"exercises": exercises})
    for i in _rotatable_indices(working, meta_by_id):
        if swapped >= iso_budget:
            break
        if flat_i is not None and i == flat_i:
            continue
        if sec_i is not None and i == sec_i and swap_secondary:
            continue
        ex = exercises[i]
        meta = _meta(meta_by_id, int(ex.exercise_id))
        role = _role(meta)
        slug = str(meta.get("muscle_slug") or "").strip().lower()
        pattern = str(meta.get("movement_pattern") or "").strip().lower()
        want_compound = role in {"compound", "primary", "main", ""}

        if focus_slugs and slug in focus_slugs:
            target_slugs: frozenset[str] = frozenset(focus_slugs)
        elif slug in CHEST_SLUGS:
            target_slugs = CHEST_SLUGS
        elif slug in BACK_SLUGS:
            target_slugs = BACK_SLUGS
        elif slug in SHOULDER_SLUGS | TRICEPS_SLUGS:
            target_slugs = frozenset(SHOULDER_SLUGS | TRICEPS_SLUGS)
        elif slug in QUAD_SLUGS | HINGE_MUSCLE_SLUGS:
            target_slugs = frozenset(QUAD_SLUGS | HINGE_MUSCLE_SLUGS)
        else:
            target_slugs = frozenset({slug}) if slug else frozenset()

        if not target_slugs:
            continue

        patterns = {pattern} if pattern else None
        cand = _pick_from_pool(
            pool,
            muscle_slugs=target_slugs,
            patterns=patterns,
            compound=True if want_compound else False,
            exclude_ids=used,
            prefer_easy_iso=prefer_easy_iso and not want_compound,
            require_angle=False,
        )
        if cand is None:
            cand = _pick_from_pool(
                pool,
                muscle_slugs=target_slugs,
                compound=True if want_compound else False,
                exclude_ids=used,
                prefer_easy_iso=prefer_easy_iso and not want_compound,
                require_angle=False,
            )
        if cand is None:
            cand = _pick_from_pool(
                pool,
                muscle_slugs=target_slugs,
                exclude_ids=used,
                prefer_easy_iso=prefer_easy_iso and not want_compound,
                require_angle=False,
            )
        if cand is None or cand.id == int(ex.exercise_id):
            continue
        _swap_slot_to_candidate(
            exercises,
            i,
            cand,
            meta_by_id=meta_by_id,
            pool=pool,
            phase_key=phase_key,
            report=report,
        )
        used.add(cand.id)
        swapped += 1

    return day.model_copy(update={"exercises": exercises})


def apply_phase_exercise_swaps(
    plan_days: list[PlanDayIn],
    *,
    phase_key: str,
    pool: list[VariationCandidate],
    meta_by_id: dict[int, dict[str, Any]],
    focus_slugs: set[str] | frozenset[str] | None = None,
    report: ChallengeVariationReport | None = None,
    avoid_ids: set[int] | frozenset[int] | None = None,
) -> list[PlanDayIn]:
    """Swap secondary/iso exercises for a mesocycle phase (challenge only)."""
    rep = report if report is not None else ChallengeVariationReport()
    focus = {str(s).strip().lower() for s in (focus_slugs or set()) if str(s).strip()}
    chest_focus = bool(focus & CHEST_SLUGS)
    avoid = {int(i) for i in (avoid_ids or set())}

    prefer_easy = phase_key == "accumulation"
    swap_secondary = phase_key in {"intensification", "specialization"}
    if phase_key == "accumulation":
        swap_isos = 1
        bias_incline = False
    elif phase_key == "intensification":
        swap_isos = 2
        bias_incline = False
    else:  # specialization
        swap_isos = 2
        bias_incline = chest_focus

    out: list[PlanDayIn] = []
    week_ids = {int(e.exercise_id) for d in plan_days for e in d.exercises}
    locked = set(avoid)
    for day in plan_days:
        day_ids = {int(e.exercise_id) for e in day.exercises}
        d = day.model_copy(deep=True)
        d = _phase_swap_day(
            d,
            phase_key=phase_key,
            pool=pool,
            meta_by_id=meta_by_id,
            focus_slugs=focus,
            report=rep,
            prefer_easy_iso=prefer_easy,
            swap_secondary=swap_secondary and is_chest_session_day(d, meta_by_id),
            swap_isos=swap_isos,
            bias_incline_secondary=bias_incline and is_chest_session_day(d, meta_by_id),
            avoid_ids=locked | (week_ids - day_ids),
        )
        new_ids = {int(e.exercise_id) for e in d.exercises}
        locked |= new_ids - day_ids
        week_ids |= new_ids
        out.append(d)
    return out
