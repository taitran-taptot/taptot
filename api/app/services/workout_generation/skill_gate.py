"""Phase skill gates: knee push-up → floor, ring row → pull-up."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from app.services.workout_generation.shortlist import (
    _is_unassisted_pullup_family,
    is_unassisted_bar_skill,
)
from app.services.workout_generation.weekly_volume import (
    is_knee_pushup_name,
    is_standard_pushup_name,
    lift_stem,
    prefer_knee_pushups,
)


@dataclass(frozen=True)
class SkillSignals:
    want_knee: bool
    want_ring_row_progress: bool
    can_pullup: bool
    fitness_baseline: dict[str, Any] | None = None


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def can_do_pullups(fitness_baseline: dict[str, Any] | None) -> bool:
    n = _as_int((fitness_baseline or {}).get("pullups_max"))
    return n is not None and n > 0


def want_ring_row_progress(fitness_baseline: dict[str, Any] | None) -> bool:
    base = fitness_baseline or {}
    variant = str(base.get("pull_test_variant") or "").strip().lower()
    if can_do_pullups(base):
        return False
    return variant.startswith("inverted") or _as_int(base.get("inverted_rows_max")) is not None


def resolve_skill_signals(
    fitness_baseline: dict[str, Any] | None,
    *,
    location: str | None = None,
    no_equipment: bool = False,
    pushups_max: int | None = None,
) -> SkillSignals:
    base = fitness_baseline if isinstance(fitness_baseline, dict) else {}
    pu = pushups_max
    if pu is None:
        pu = _as_int(base.get("pushups_max"))
    return SkillSignals(
        want_knee=prefer_knee_pushups(
            location=location,
            no_equipment=no_equipment,
            pushups_max=pu,
            fitness_baseline=base,
        ),
        want_ring_row_progress=want_ring_row_progress(base),
        can_pullup=can_do_pullups(base),
        fitness_baseline=base or None,
    )


def _item_names(item: Any) -> tuple[str | None, str | None]:
    if isinstance(item, dict):
        return (
            str(item.get("name_vi") or "") or None,
            str(item.get("name_en") or "") or None,
        )
    return (
        str(getattr(item, "name_vi", None) or "") or None,
        str(getattr(item, "name_en", None) or "") or None,
    )


def is_hard_pushup_item(item: Any) -> bool:
    nv, ne = _item_names(item)
    return is_standard_pushup_name(nv, ne)


def is_easy_pushup_item(item: Any) -> bool:
    nv, ne = _item_names(item)
    return is_knee_pushup_name(nv, ne)


def is_hard_pull_item(item: Any) -> bool:
    nv, ne = _item_names(item)
    return _is_unassisted_pullup_family(nv, ne)


def is_easy_pull_item(item: Any) -> bool:
    nv, ne = _item_names(item)
    blob = f"{nv or ''} {ne or ''}".strip().lower()
    return any(
        k in blob
        for k in (
            "inverted",
            "australian",
            "ring row",
            "chèo vòng",
            "cheo vong",
            "scapular",
            "assisted",
            "trợ lực",
            "tro luc",
            "1/3",
        )
    )


def item_allowed_for_phase(item: Any, phase_i: int, signals: SkillSignals) -> bool:
    """Phase 0 drops the hard skill; later phases keep both variants."""
    if phase_i <= 0:
        if signals.want_knee and is_hard_pushup_item(item):
            return False
        if signals.want_ring_row_progress and is_hard_pull_item(item):
            return False
    return True


def _rank_item(item: Any, phase_i: int, signals: SkillSignals) -> int:
    """Lower sorts first in the prompt pool."""
    score = 1
    if phase_i <= 0:
        if signals.want_knee and is_easy_pushup_item(item):
            score = 0
        if signals.want_ring_row_progress and is_easy_pull_item(item):
            score = 0
    elif phase_i == 1:
        if signals.want_knee and is_hard_pushup_item(item):
            score = 0
        if signals.want_ring_row_progress and (
            is_easy_pull_item(item) or is_hard_pull_item(item)
        ):
            score = 0 if is_easy_pull_item(item) else 1
    else:
        if signals.want_knee and is_hard_pushup_item(item):
            score = 0
        elif signals.want_knee and is_easy_pushup_item(item):
            score = 2
        if signals.want_ring_row_progress and is_hard_pull_item(item):
            score = 0
        elif signals.want_ring_row_progress and is_easy_pull_item(item):
            score = 2
    return score


def gate_pool(items: list[Any], phase_i: int, signals: SkillSignals) -> list[Any]:
    from app.services.workout_generation.skill_ladder import filter_pool_by_ladder

    kept = [x for x in items if item_allowed_for_phase(x, phase_i, signals)]
    if not kept:
        kept = list(items)
    kept = filter_pool_by_ladder(kept, signals.fitness_baseline, phase_i=phase_i)
    return sorted(kept, key=lambda it: (_rank_item(it, phase_i, signals), _item_eid(it)))


def _item_eid(item: Any) -> int:
    try:
        if isinstance(item, dict):
            return int(item.get("id") or 0)
        return int(getattr(item, "id", 0) or 0)
    except (TypeError, ValueError):
        return 0


def apply_skill_gate_to_week(
    week_payload: list[dict[str, Any]],
    phase_i: int,
    signals: SkillSignals,
) -> list[dict[str, Any]]:
    out = copy.deepcopy(week_payload)
    for day in out:
        for spec in day.get("slots") or []:
            spec["pool"] = gate_pool(list(spec.get("pool") or []), phase_i, signals)
        for block in day.get("blocks") or []:
            block["shortlist"] = gate_pool(
                list(block.get("shortlist") or []), phase_i, signals
            )
    return out


def first_allowed_id(pool: list[Any], phase_i: int, signals: SkillSignals) -> int | None:
    for item in gate_pool(pool, phase_i, signals):
        eid = _item_eid(item)
        if eid:
            return eid
    return None


def replace_gated_ids(
    ids: list[int],
    pool: list[Any],
    phase_i: int,
    signals: SkillSignals,
) -> list[int]:
    allowed = {_item_eid(x) for x in gate_pool(pool, phase_i, signals)}
    fallback = first_allowed_id(pool, phase_i, signals)
    out: list[int] = []
    for eid in ids:
        if eid in allowed:
            if eid not in out:
                out.append(eid)
        elif fallback and fallback not in out:
            out.append(fallback)
    return out


def exempt_stems(phase_i: int, signals: SkillSignals) -> set[str]:
    if phase_i > 0:
        return set()
    out: set[str] = set()
    if signals.want_knee:
        out.add("pushup")
    if signals.want_ring_row_progress:
        out.add("pullup")
    return out


def stem_of_item(item: Any) -> str | None:
    nv, ne = _item_names(item)
    return lift_stem(nv, ne)


def skill_prompt_vi(phase_i: int, signals: SkillSignals) -> str:
    from app.services.workout_generation.skill_ladder import ladder_prompt_vi

    month = phase_i + 1
    bits: list[str] = []
    ladder = ladder_prompt_vi(signals.fitness_baseline, phase_i=phase_i)
    if ladder:
        bits.append(ladder)
    if signals.want_knee:
        if phase_i <= 0:
            bits.append(
                "Pha 1: chỉ chống đẩy quỳ — không pick chống đẩy sàn."
            )
        elif phase_i == 1:
            bits.append(
                "Pha 2: được 1 slot chống đẩy sàn nếu pool còn; giữ quỳ làm volume."
            )
        else:
            bits.append(
                "Pha 3: ưu tiên chống đẩy sàn làm compound; quỳ là phụ."
            )
    if signals.want_ring_row_progress:
        if phase_i <= 0:
            bits.append(
                "Pha 1: không pick kéo xà/chin trần. Ưu tiên ring row, australian, scapular, assisted."
            )
        elif phase_i == 1:
            bits.append(
                "Pha 2: được 1 slot kéo xà hoặc 1/3 / scapular / assisted nếu pool còn; giữ ring row."
            )
        else:
            bits.append(
                "Pha 3: ưu tiên kéo xà; ring row là phụ."
            )
    elif signals.can_pullup:
        bits.append("User đã test kéo xà — được pick kéo xà trần từ pha này.")
    if not bits:
        return f"Pha {month}: pick trong pool đã lọc, tôn trọng test thể lực."
    return " ".join(bits)


# Re-export for shortlist L1 deny.
def allow_unassisted_pull_progress(fitness_baseline: dict[str, Any] | None) -> bool:
    return can_do_pullups(fitness_baseline) or want_ring_row_progress(fitness_baseline)


def is_l1_forever_bar_skill(name_vi: str | None, name_en: str | None) -> bool:
    """Dips / muscle-up stay L1-denied even when pull-up progress is allowed."""
    if not is_unassisted_bar_skill(name_vi, name_en):
        return False
    if _is_unassisted_pullup_family(name_vi, name_en):
        blob = f"{name_vi or ''} {name_en or ''}".strip().lower()
        return "muscle-up" in blob or "muscle up" in blob
    return True
