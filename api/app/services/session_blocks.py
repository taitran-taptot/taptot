"""Resolve session structure from DB templates for AI / deterministic gen.

OpenAI must not invent block counts: inject the recipe from get_session_recipe()
and only allow picking exercise_ids within each block's shortlist.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.entities import SessionBlockTemplate
from app.services.exercise_prescription import clamp_experience_level

REFERENCE_SESSION_MINUTES = 50.0


@dataclass(frozen=True)
class BlockSpec:
    block_key: str
    label_vi: str
    plan_section: str
    movement_role: str | None
    count_min: int
    count_max: int
    duration_min_minutes: int | None
    duration_max_minutes: int | None
    is_optional: bool
    sort_order: int


def _clamp(n: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, n))


def _scale_minutes(value: int | None, factor: float) -> int | None:
    if value is None:
        return None
    return max(1, int(round(value * factor)))


def get_session_recipe(
    db: Session,
    experience_level: int | None,
    session_minutes: int | None = 45,
    *,
    include_cardio: bool | None = None,
) -> list[BlockSpec]:
    """Return ordered blocks for a level, with durations scaled by session length.

    Cardio: omitted when session_minutes < 60 unless include_cardio=True.
    When include_cardio=False, always omit. When True, always keep.
    """
    level = clamp_experience_level(experience_level)
    try:
        minutes = int(session_minutes if session_minutes is not None else 45)
    except (TypeError, ValueError):
        minutes = 45
    minutes = max(1, minutes)

    factor = _clamp(minutes / REFERENCE_SESSION_MINUTES, 0.75, 1.4)

    if include_cardio is None:
        keep_cardio = minutes >= 60
    else:
        keep_cardio = bool(include_cardio)

    rows = (
        db.query(SessionBlockTemplate)
        .filter(SessionBlockTemplate.experience_level == level)
        .order_by(SessionBlockTemplate.sort_order.asc())
        .all()
    )

    out: list[BlockSpec] = []
    for row in rows:
        if row.block_key == "cardio" and not keep_cardio:
            continue
        out.append(
            BlockSpec(
                block_key=row.block_key,
                label_vi=row.label_vi,
                plan_section=row.plan_section,
                movement_role=row.movement_role,
                count_min=int(row.count_min),
                count_max=int(row.count_max),
                duration_min_minutes=_scale_minutes(
                    row.duration_min_minutes if row.duration_min_minutes is not None else None,
                    factor,
                ),
                duration_max_minutes=_scale_minutes(
                    row.duration_max_minutes if row.duration_max_minutes is not None else None,
                    factor,
                ),
                is_optional=bool(row.is_optional),
                sort_order=int(row.sort_order),
            )
        )
    return out


def _spec_block(
    *,
    sort_order: int,
    block_key: str,
    label_vi: str,
    plan_section: str,
    movement_role: str | None,
    count: int,
    duration_min: int | None = None,
    duration_max: int | None = None,
    is_optional: bool = False,
) -> BlockSpec:
    c = max(0, int(count))
    return BlockSpec(
        block_key=block_key,
        label_vi=label_vi,
        plan_section=plan_section,
        movement_role=movement_role,
        count_min=c,
        count_max=c,
        duration_min_minutes=duration_min,
        duration_max_minutes=duration_max or duration_min,
        is_optional=is_optional,
        sort_order=sort_order,
    )


def _gym_warmup_spec(warm: int) -> tuple[int, int, int, int]:
    """1 stretch only; primer of the first main lift is injected later."""
    warm = max(0, int(warm or 0))
    gen_d = max(2, min(5, warm if warm else 4))
    if warm >= 8:
        gen_d = max(3, min(5, warm // 2))
    return 1, gen_d, 0, 0


def _home_warmup_spec(warm: int) -> tuple[int, int]:
    """1 stretch only; primer of the first main lift is injected later."""
    warm = max(0, int(warm or 0))
    each = max(2, min(5, warm if warm else 3))
    if warm >= 8:
        each = max(3, min(5, warm // 2))
    return 1, each


def _cooldown_spec(cool: int, session_minutes: int) -> tuple[int, int]:
    cool = max(0, int(cool or 0))
    n = 2 if int(session_minutes or 0) >= 45 and cool >= 4 else 1
    each = max(2, cool // n) if cool else 3
    return n, each


def _core_cardio_minutes(session_minutes: int) -> int:
    """One continuous cardio bout on Cardio-Core days (not several short pieces)."""
    m = max(30, int(session_minutes or 45))
    leftover = m - 26  # ~5 warmup + ~16 core work + ~5 cooldown
    # Long Cardio-Core sessions use Zone 2 time, not extra abdominal hard sets.
    return max(12, min(60, leftover))


def _home_conditioning_minutes(
    session_minutes: int,
    count: int,
    spec: dict | None = None,
) -> int:
    """One Zone 2 bout on home lift days. Spec minutes win; no 10p cap."""
    n = max(1, int(count or 1))
    raw = None if spec is None else spec.get("conditioningMinutes")
    if raw is not None:
        budget = int(raw)
    else:
        m = int(session_minutes or 45)
        if m <= 30:
            budget = 5
        elif m <= 45:
            budget = 8
        elif m <= 60:
            budget = 10
        elif m <= 75:
            budget = 15
        else:
            budget = 20
    return max(5, max(1, budget // n))


def _inject_liss_finisher(blocks: list[BlockSpec], *, enabled: bool) -> list[BlockSpec]:
    """Add 8–10 min easy cardio before cooldown without dropping lift slots."""
    if not enabled or any(b.block_key in {"cardio", "conditioning"} for b in blocks):
        return blocks
    insert_at = next((i for i, b in enumerate(blocks) if b.block_key == "cooldown"), len(blocks))
    prev_order = blocks[insert_at - 1].sort_order if insert_at > 0 else 45
    next_order = blocks[insert_at].sort_order if insert_at < len(blocks) else prev_order + 20
    if next_order > prev_order + 1:
        order = prev_order + max(1, (next_order - prev_order) // 2)
    else:
        order = prev_order + 5
    liss = _spec_block(
        sort_order=order,
        block_key="cardio",
        label_vi="Cardio nhẹ cuối buổi",
        plan_section="cardio",
        movement_role="cardio",
        count=1,
        duration_min=8,
        duration_max=10,
    )
    return blocks[:insert_at] + [liss] + blocks[insert_at:]


def _with_core_finisher(blocks: list[BlockSpec], *, enabled: bool) -> list[BlockSpec]:
    """L3 lift days: one short core after accessories, before cardio/cooldown."""
    if not enabled or any(b.block_key == "core" for b in blocks):
        return blocks
    insert_at = next(
        (i for i, b in enumerate(blocks) if b.block_key in {"cardio", "cooldown"}),
        len(blocks),
    )
    prev_order = blocks[insert_at - 1].sort_order if insert_at > 0 else 40
    next_order = blocks[insert_at].sort_order if insert_at < len(blocks) else prev_order + 20
    if next_order > prev_order + 1:
        order = prev_order + max(1, (next_order - prev_order) // 2)
    else:
        order = prev_order + 5
    core = _spec_block(
        sort_order=order,
        block_key="core",
        label_vi="Core",
        plan_section="main",
        movement_role="isolation",
        count=1,
        is_optional=True,
    )
    return blocks[:insert_at] + [core] + blocks[insert_at:]


def get_master_session_recipe(
    *,
    location: str,
    session_minutes: int | None = 45,
    split_role: str | None = None,
    experience_level: int | None = None,
    cardio_on_lift_days: bool = True,
    liss_finisher: bool = False,
    no_equipment: bool = False,
) -> list[BlockSpec]:
    """Session blocks from Master gym/home minute tables."""
    from app.services.schedule_spec_master import (
        gym_session_spec,
        home_session_spec,
        parse_duration_minutes,
        snap_session_minutes,
    )

    loc = (location or "gym").strip().lower()
    minutes = snap_session_minutes(int(session_minutes or 45))
    role = (split_role or "").strip().lower()
    level = int(experience_level or 2)
    lift_cardio = bool(cardio_on_lift_days) and role not in {"core"}
    from app.services.workout_generation.split_map import normalize_split_role

    core_finisher = level >= 3 and normalize_split_role(role) not in {"core"}

    if role == "core":
        cardio_m = _core_cardio_minutes(minutes)
        cardio_key = "conditioning" if loc == "home" else "cardio"
        cardio_role = "conditioning" if loc == "home" else "cardio"
        cardio_label = "Thể lực / cardio" if loc == "home" else "Cardio"
        if loc == "home":
            spec = home_session_spec(minutes)
            warm = parse_duration_minutes(spec.get("warmup"))
            cool = parse_duration_minutes(spec.get("cooldown"))
            wu_n, wu_d = _home_warmup_spec(warm)
        else:
            spec = gym_session_spec(minutes)
            warm = parse_duration_minutes(spec.get("warmup"))
            cool = parse_duration_minutes(spec.get("cooldown"))
            wu_n, wu_d = _home_warmup_spec(warm)
        cool_n, cool_d = _cooldown_spec(cool, minutes)
        core_blocks = [
            _spec_block(
                sort_order=10,
                block_key="general_warmup",
                label_vi="Khởi động",
                plan_section="warmup",
                movement_role="mobility",
                count=wu_n,
                duration_min=wu_d,
            ),
            _spec_block(
                sort_order=20,
                block_key=cardio_key,
                label_vi=cardio_label,
                plan_section="cardio",
                movement_role=cardio_role,
                count=1,
                duration_min=cardio_m,
            ),
            _spec_block(
                sort_order=30,
                block_key="core",
                label_vi="Core",
                plan_section="main",
                movement_role="isolation",
                count=2,
            ),
            _spec_block(
                sort_order=50,
                block_key="cooldown",
                label_vi="Cool-down",
                plan_section="cooldown",
                movement_role="mobility",
                count=cool_n,
                duration_min=cool_d,
            ),
        ]
        return core_blocks

    if loc == "home":
        spec = home_session_spec(minutes)
        warm = parse_duration_minutes(spec.get("warmup"))
        cool = parse_duration_minutes(spec.get("cooldown"))
        resistance_n = int(spec.get("resistanceCount") or 2)
        conditioning_n = int(spec.get("conditioningCount") or 1)
        if no_equipment:
            if minutes <= 30:
                resistance_n = 2
            # Allow up to 2 interval pieces; final pass may keep 1 when budget ≤10.
            conditioning_n = max(2, conditioning_n)
        elif not lift_cardio:
            conditioning_n = 0
        wu_n, wu_d = _home_warmup_spec(warm)
        cool_n, cool_d = _cooldown_spec(cool, minutes)
        blocks = [
            _spec_block(
                sort_order=10,
                block_key="general_warmup",
                label_vi="Khởi động",
                plan_section="warmup",
                movement_role="mobility",
                count=wu_n,
                duration_min=wu_d,
            ),
            _spec_block(
                sort_order=20,
                block_key="resistance",
                label_vi="Kháng lực",
                plan_section="main",
                movement_role="resistance",
                count=resistance_n,
            ),
        ]
        if conditioning_n > 0:
            blocks.append(
                _spec_block(
                    sort_order=30,
                    block_key="conditioning",
                    label_vi="Cardio nhẹ cuối buổi",
                    plan_section="cardio",
                    movement_role="conditioning",
                    count=conditioning_n,
                    duration_min=_home_conditioning_minutes(
                        minutes, conditioning_n, spec
                    ),
                )
            )
        blocks.append(
            _spec_block(
                sort_order=40,
                block_key="cooldown",
                label_vi="Cool-down",
                plan_section="cooldown",
                movement_role="mobility",
                count=cool_n,
                duration_min=cool_d,
            )
        )
        return _inject_liss_finisher(
            _with_core_finisher(blocks, enabled=core_finisher),
            enabled=liss_finisher,
        )

    spec = gym_session_spec(minutes)
    warm = parse_duration_minutes(spec.get("warmup"))
    cardio_m = parse_duration_minutes(spec.get("cardio"))
    cool = parse_duration_minutes(spec.get("cooldown"))
    compounds = int(spec.get("compounds") or 1)
    isolates = int(spec.get("isolates") or 2)

    fb_role = normalize_split_role(role) in {"fb", "fb_a", "fb_b"}
    if fb_role and level <= 2 and isolates > 2:
        extra = isolates - 2
        compounds = min(4, compounds + extra // 2)
        isolates = 2
    if normalize_split_role(role) == "upper" and level <= 2:
        if isolates > 2:
            extra = isolates - 2
            compounds = min(3, compounds + extra // 2)
            isolates = 2
        compounds = min(max(compounds, 2), 3)
    gen_n, gen_d, dyn_n, dyn_d = _gym_warmup_spec(warm)
    cool_n, cool_d = _cooldown_spec(cool, minutes)
    blocks = [
        _spec_block(
            sort_order=10,
            block_key="general_warmup",
            label_vi="Khởi động chung",
            plan_section="warmup",
            movement_role="mobility",
            count=gen_n,
            duration_min=gen_d,
        ),
    ]
    if dyn_n > 0:
        blocks.append(
            _spec_block(
                sort_order=20,
                block_key="dynamic_mobility",
                label_vi="Mobility động",
                plan_section="warmup",
                movement_role="mobility",
                count=dyn_n,
                duration_min=dyn_d,
            )
        )
    blocks.extend(
        [
            _spec_block(
                sort_order=30,
                block_key="compound",
                label_vi="Compound",
                plan_section="main",
                movement_role="compound",
                count=compounds,
            ),
            _spec_block(
                sort_order=40,
                block_key="accessory",
                label_vi="Isolation",
                plan_section="main",
                movement_role="isolation",
                count=isolates,
            ),
        ]
    )
    if cardio_m > 0 and lift_cardio:
        blocks.append(
            _spec_block(
                sort_order=50,
                block_key="cardio",
                label_vi="Cardio nhẹ cuối buổi",
                plan_section="cardio",
                movement_role="cardio",
                count=1,
                duration_min=cardio_m,
                is_optional=False,
            )
        )
    blocks.append(
        _spec_block(
            sort_order=60,
            block_key="cooldown",
            label_vi="Cool-down",
            plan_section="cooldown",
            movement_role="mobility",
            count=cool_n,
            duration_min=cool_d,
        )
    )
    return _inject_liss_finisher(
        _with_core_finisher(blocks, enabled=core_finisher),
        enabled=liss_finisher,
    )
