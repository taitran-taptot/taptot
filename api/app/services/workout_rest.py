"""Default rest between sets by movement role (seconds)."""

from __future__ import annotations

REST_COMPOUND_SEC = 180
REST_COMPOUND_L1_SEC = 120
REST_ISOLATION_SEC = 90
REST_CONDITIONING_SEC = 90
REST_MOBILITY_SEC = 60
REST_WARMUP_BETWEEN_SEC = 30
REST_COOLDOWN_BETWEEN_SEC = 20
REST_CARDIO_SEC = 0
REST_LADDER_SEC = (0, 30, 45, 60, 90, 120, 150, 180)
_TIMED_CARDIO_KEYS = frozenset({"cardio", "conditioning"})
_WARMUP_KEYS = frozenset({"general_warmup", "dynamic_mobility", "cooldown"})


def snap_rest_seconds(sec: int | None) -> int:
    """Snap rest to a gym-clock ladder. Cardio 0 stays 0; otherwise nearest of 30–180."""
    try:
        value = int(sec or 0)
    except (TypeError, ValueError):
        return REST_ISOLATION_SEC
    if value <= 0:
        return REST_CARDIO_SEC
    if value == REST_COOLDOWN_BETWEEN_SEC:
        return value
    value = min(REST_COMPOUND_SEC, value)
    ladder = REST_LADDER_SEC[1:]
    return min(ladder, key=lambda step: (abs(step - value), step))


def is_continuous_cardio(
    *,
    block_key: str | None = None,
    plan_section: str | None = None,
    movement_role: str | None = None,
) -> bool:
    key = (block_key or "").strip().lower()
    section = (plan_section or "").strip().lower()
    role = (movement_role or "").strip().lower()
    return section == "cardio" or key in _TIMED_CARDIO_KEYS or role in _TIMED_CARDIO_KEYS


def rest_for_plan_exercise(
    *,
    block_key: str | None,
    plan_section: str | None,
    movement_role: str | None,
) -> int:
    if is_continuous_cardio(
        block_key=block_key, plan_section=plan_section, movement_role=movement_role
    ):
        return REST_CARDIO_SEC
    section = (plan_section or "").strip().lower()
    key = (block_key or "").strip().lower()
    if section in {"warmup", "cooldown"} or key in _WARMUP_KEYS:
        return REST_WARMUP_BETWEEN_SEC
    return default_rest_seconds(movement_role)

# Schema / import fallback when role unknown
REST_MAIN_DEFAULT_SEC = REST_ISOLATION_SEC


def default_rest_seconds(
    movement_role: str | None,
    *,
    experience_level: int | None = None,
) -> int:
    role = (movement_role or "").strip().lower()
    if role in {"compound", "resistance"}:
        if experience_level is not None and int(experience_level) <= 1:
            return REST_COMPOUND_L1_SEC
        return REST_COMPOUND_SEC
    if role in {"isolation", "conditioning"}:
        return REST_ISOLATION_SEC if role == "isolation" else REST_CONDITIONING_SEC
    if role == "cardio":
        return REST_CARDIO_SEC
    if role == "mobility":
        return REST_MOBILITY_SEC
    return REST_MAIN_DEFAULT_SEC


def default_rest_for_section(
    section: str | None,
    *,
    movement_role: str | None = None,
    experience_level: int | None = None,
) -> int:
    sec = (section or "main").strip().lower()
    if sec == "cardio":
        return REST_CARDIO_SEC
    if sec in {"warmup", "cooldown"}:
        return REST_WARMUP_BETWEEN_SEC
    if movement_role:
        return default_rest_seconds(movement_role, experience_level=experience_level)
    return REST_MAIN_DEFAULT_SEC


WARMUP_NOTE_VI = "Thở đều, đừng gồng hết sức."
COOLDOWN_NOTE_VI = "Giãn nhẹ, không ép đau. Nghỉ ngắn giữa hiệp."
CARDIO_NOTE_VI = (
    "Nhịp vừa phải, vẫn nói chuyện được. "
    "Mệt thì chậm lại hoặc nghỉ 30–60 giây rồi tiếp; chóng mặt / đau ngực thì dừng."
)
INTERVAL_CARDIO_NOTE_VI = (
    "Mỗi nhịp 30–60 giây rồi nghỉ, không chạy liền mạch. "
    "Nhịp vừa phải, vẫn nói chuyện được. "
    "Mệt thì chậm lại hoặc nghỉ thêm; chóng mặt / đau ngực thì dừng."
)
# Fixed-set interval: scale rest (then work/sets) to match leftover minutes.
INTERVAL_CARDIO_SETS = 5
INTERVAL_CARDIO_MIN_BOUTS = 4
INTERVAL_CARDIO_MAX_BOUTS = 8
INTERVAL_CARDIO_REST_MIN = 60
INTERVAL_CARDIO_REST_MAX = 120
INTERVAL_CARDIO_WORK_MIN = 30
INTERVAL_CARDIO_WORK_MAX = 60
INTERVAL_CARDIO_WORK_DEFAULT = 45
INTERVAL_CARDIO_REST_DEFAULT = 60
INTERVAL_CARDIO_SPLIT_MINUTES = 10


def _interval_wall_seconds(sets: int, work_sec: int, rest_sec: int) -> int:
    return int(sets) * int(work_sec) + max(0, int(sets) - 1) * int(rest_sec)


def home_interval_cardio_prescription(
    duration_min: int | None,
    *,
    experience_level: int | None = None,
) -> tuple[int, str, int, str]:
    """Home cardio: ~5 bouts; L1/yếu khóa 30s/hiệp — scale rest/sets, không đẩy work lên 60."""
    target_sec = max(180, int(round(float(duration_min or 5) * 60)))
    beginner = experience_level is None or int(experience_level) <= 1
    work = INTERVAL_CARDIO_WORK_MIN if beginner else INTERVAL_CARDIO_WORK_DEFAULT
    sets = INTERVAL_CARDIO_SETS
    gaps = max(1, sets - 1)
    rest = int(round((target_sec - sets * work) / gaps))

    if rest < INTERVAL_CARDIO_REST_MIN:
        rest = INTERVAL_CARDIO_REST_MIN
        if not beginner:
            # Short budget: shrink work within 30–60 for stronger athletes only.
            work = int(round((target_sec - gaps * rest) / sets))
            work = max(INTERVAL_CARDIO_WORK_MIN, min(INTERVAL_CARDIO_WORK_MAX, work))
    elif rest > INTERVAL_CARDIO_REST_MAX:
        rest = INTERVAL_CARDIO_REST_MAX
        if not beginner:
            needed_work = int(round((target_sec - gaps * rest) / sets))
            if needed_work <= INTERVAL_CARDIO_WORK_MAX:
                work = max(work, min(INTERVAL_CARDIO_WORK_MAX, needed_work))
                rest = int(round((target_sec - sets * work) / gaps))
                rest = min(
                    INTERVAL_CARDIO_REST_MAX,
                    max(INTERVAL_CARDIO_REST_MIN, rest),
                )
            else:
                work = INTERVAL_CARDIO_WORK_MAX
        # Fill remaining time with more short bouts (beginner stays at 30s work).
        while (
            _interval_wall_seconds(sets, work, rest) + 45 < target_sec
            and sets < INTERVAL_CARDIO_MAX_BOUTS
        ):
            sets += 1
            rest = min(
                INTERVAL_CARDIO_REST_MAX,
                max(
                    INTERVAL_CARDIO_REST_DEFAULT,
                    int(round((target_sec - sets * work) / max(1, sets - 1))),
                ),
            )

    rest = snap_rest_seconds(rest)
    rest = max(INTERVAL_CARDIO_REST_MIN, min(INTERVAL_CARDIO_REST_MAX, rest))
    if beginner:
        work = INTERVAL_CARDIO_WORK_MIN
    return sets, f"{work} giây", rest, INTERVAL_CARDIO_NOTE_VI


def interval_cardio_prescription(
    target_minutes: float | int | None,
    *,
    experience_level: int | None = None,
) -> tuple[int, str, int, str]:
    """Alias used by duration fill — same fixed-set / scaled-rest math."""
    return home_interval_cardio_prescription(
        target_minutes, experience_level=experience_level
    )


def interval_cardio_piece_count(budget_minutes: float) -> int:
    """≤10p → 1 interval piece; >10p → 2 pieces sharing the budget."""
    budget = float(budget_minutes or 0)
    if budget <= 0:
        return 0
    if budget <= float(INTERVAL_CARDIO_SPLIT_MINUTES):
        return 1
    return 2


def timed_block_prescription(
    *,
    block_key: str | None,
    plan_section: str | None,
    movement_role: str | None,
    duration_min: int | None,
    duration_max: int | None = None,
    interval_cardio: bool = False,
    experience_level: int | None = None,
    mobility_sets: int | None = None,
) -> tuple[int, str, int, str | None] | None:
    """(sets, reps, rest_seconds, notes) for timed cardio / mobility; else None."""
    rest = rest_for_plan_exercise(
        block_key=block_key,
        plan_section=plan_section,
        movement_role=movement_role,
    )
    if is_continuous_cardio(
        block_key=block_key, plan_section=plan_section, movement_role=movement_role
    ):
        dur = duration_min or duration_max or 10
        if interval_cardio:
            return home_interval_cardio_prescription(
                dur, experience_level=experience_level
            )
        return 1, f"{int(dur)} phút", rest, CARDIO_NOTE_VI
    section = (plan_section or "").strip().lower()
    role = (movement_role or "").strip().lower()
    key = (block_key or "").strip().lower()
    if section in {"warmup", "cooldown"} or role == "mobility" or key in _WARMUP_KEYS:
        hold_sets = 2 if mobility_sets is None else max(1, min(3, int(mobility_sets)))
        if section == "cooldown" or key == "cooldown":
            return hold_sets, "30 giây", REST_COOLDOWN_BETWEEN_SEC, COOLDOWN_NOTE_VI
        return hold_sets, "30 giây", REST_WARMUP_BETWEEN_SEC, WARMUP_NOTE_VI
    return None
