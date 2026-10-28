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


REQUIRE_PULLUP_MIN = 5
_PULLUP_GEAR = frozenset({"pull-up-bar", "gymnastic-rings"})


def can_do_pullups(fitness_baseline: dict[str, Any] | None) -> bool:
    n = _as_int((fitness_baseline or {}).get("pullups_max"))
    return n is not None and n > 0


def pullups_max_unspecified(fitness_baseline: dict[str, Any] | None) -> bool:
    """True when the wizard never sent pullups_max (empty test), not hang/null."""
    return not isinstance(fitness_baseline, dict) or "pullups_max" not in fitness_baseline


def must_include_pullup(
    fitness_baseline: dict[str, Any] | None,
    equipment_slugs: Any = None,
) -> bool:
    """True when the Pull day must include a bar or ring pull-up."""
    from app.services.workout_generation.shortlist import expand_equipment_aliases

    user = expand_equipment_aliases(equipment_slugs)
    if not (user & _PULLUP_GEAR):
        return False
    if pullups_max_unspecified(fitness_baseline):
        return True
    n = _as_int((fitness_baseline or {}).get("pullups_max"))
    if n is None:
        return False
    return n >= REQUIRE_PULLUP_MIN


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


def is_strict_pullup_item(item: Any) -> bool:
    """Unassisted pull-up / chin-up / ring pull-up — not muscle-up, row, or dip."""
    nv, ne = _item_names(item)
    if not _is_unassisted_pullup_family(nv, ne):
        return False
    blob = f"{nv or ''} {ne or ''}".strip().lower()
    if "muscle-up" in blob or "muscle up" in blob:
        return False
    if "weighted" in blob or "đeo tạ" in blob:
        return False
    return True


def is_warmup_strength_leak(item: Any) -> bool:
    """True for pull-ups / compounds that must not occupy the stretch warmup slot."""
    if is_strict_pullup_item(item):
        return True
    if isinstance(item, dict):
        role = str(item.get("movement_role") or "").strip().lower()
    else:
        role = str(getattr(item, "movement_role", None) or "").strip().lower()
    nv, ne = _item_names(item)
    blob = f"{nv or ''} {ne or ''}".strip().lower()
    if any(k in blob for k in ("giãn", "gian ", "stretch", "xoay", "mobility")):
        return False
    if role in {"compound", "resistance"}:
        return True
    if "ring dip" in blob or "dip vòng" in blob or "dip vong" in blob:
        return True
    return False


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
    elif pullups_max_unspecified(signals.fitness_baseline):
        bits.append(
            "Pull/Upper: chưa gửi pullups_max — một compound BẮT BUỘC là hít xà hoặc chin-up "
            "nếu pool còn (user chọn xà/vòng). Cấm chèo ba lô; không lặp cùng bài trong một buổi."
        )
    elif signals.can_pullup:
        n = _as_int((signals.fitness_baseline or {}).get("pullups_max"))
        if n is not None and n >= 10:
            bits.append(
                "Pull/Upper: BẮT BUỘC hít xà hoặc chin-up, kèm Ring Pull-Up + ring row "
                f"+ Ring Rear Delt Fly + ring face pull (test {n}). "
                "Cấm chèo ba lô; cấm ngực/vai trước/tay sau trên ngày Pull; "
                "không lặp cùng bài trong một buổi."
            )
        elif n is not None and n >= REQUIRE_PULLUP_MIN:
            bits.append(
                "Pull/Upper: một compound BẮT BUỘC là hít xà (bar) hoặc chin-up "
                f"(test {n} cái). Không thay bằng ring row. "
                "Cấm chèo ba lô; cấm ngực/vai trước/tay sau trên ngày Pull; "
                "không lặp cùng bài trong một buổi."
            )
        else:
            bits.append(
                "Pull: pullups_max < 5 — compound chính là ring row, kèm Ring Rear Delt Fly "
                "và ring face pull; thiếu slot thì Toes-to-Bar / Hanging Knee Raises. "
                "Không pick hít xà trần. Cấm chèo ba lô nếu test ≥ 3. "
                "Không lặp cùng bài trong một buổi."
            )
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
