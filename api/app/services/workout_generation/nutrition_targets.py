"""BMR / TDEE / macro targets with safety clamps for AI plans."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

KCAL_PER_KG = 7700.0
GAIN_MUSCLE_SURPLUS = 300

SessionKind = Literal["strength", "fullbody", "cardio", "rest"]

_CALORIE_MULTIPLIERS: dict[str, dict[str, float]] = {
    "lose_weight": {"strength": 1.05, "fullbody": 1.00, "cardio": 0.92, "rest": 0.82},
    "gain_weight": {"strength": 1.12, "fullbody": 1.08, "cardio": 0.98, "rest": 0.90},
    "gain_muscle": {"strength": 1.12, "fullbody": 1.08, "cardio": 0.98, "rest": 0.90},
    "maintain": {"strength": 1.03, "fullbody": 1.00, "cardio": 0.97, "rest": 0.95},
}

_STRENGTH_ROLES = frozenset(
    {
        "upper",
        "lower",
        "push",
        "pull",
        "legs",
        "chest",
        "back",
        "shoulders",
        "arms",
        "glutes",
        "core",
    }
)
_FULLBODY_ROLES = frozenset({"fb", "fb_a", "fb_b", "fullbody", "full_body", "full body"})
_CARDIO_ROLES = frozenset({"cardio", "conditioning", "recovery"})

MAX_BLOCK_CALORIE_DELTA = 150
MAX_BLOCK_CALORIE_DELTA_MONTHLY = 250
BLOCK_SIZE_WEEKS = 2
CURRICULUM_BLOCK_SIZE_WEEKS = 4

ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}


@dataclass(frozen=True)
class NutritionTargets:
    bmr: int
    tdee: int
    target_calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    meals_per_day: int
    kg_per_week: float | None
    delta_kcal: int
    clamped: bool
    notes_vi: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DayCalorieTarget:
    split_role: str | None
    session_kind: SessionKind
    targets: NutritionTargets


@dataclass(frozen=True)
class WeeklyCalorieSchedule:
    avg_target: int
    training: tuple[DayCalorieTarget, ...]
    rest: NutritionTargets
    rest_days_per_week: int


@dataclass(frozen=True)
class NutritionBlock:
    block_index: int
    week_from: int
    week_to: int
    projected_weight_kg: float
    targets: NutritionTargets
    schedule: WeeklyCalorieSchedule


def projected_weight_kg(
    initial_weight: float,
    *,
    goal: str,
    kg_per_week: float,
    block_index: int,
    block_size: int = BLOCK_SIZE_WEEKS,
) -> float:
    delta = kg_per_week * block_size * block_index
    goal_n = (goal or "maintain").lower()
    if goal_n == "lose_weight":
        return max(30.0, initial_weight - delta)
    if goal_n == "gain_weight":
        return initial_weight + delta
    return initial_weight


def clamp_block_avg_target(
    new_avg: int,
    prev_avg: int | None,
    goal: str,
    *,
    max_delta: int | None = None,
) -> int:
    """Limit step change between nutrition blocks (monotonic for lose/gain)."""
    if prev_avg is None:
        return int(new_avg)
    goal_n = (goal or "maintain").lower()
    d = int(max_delta if max_delta is not None else MAX_BLOCK_CALORIE_DELTA)
    if goal_n == "lose_weight":
        return min(prev_avg, max(int(new_avg), prev_avg - d))
    if goal_n in {"gain_weight", "gain_muscle"}:
        return max(prev_avg, min(int(new_avg), prev_avg + d))
    return int(new_avg)


def build_nutrition_blocks(
    payload: dict[str, Any],
    *,
    goal: str,
    duration_weeks: int,
    split_roles: list[str | None],
    block_size: int = BLOCK_SIZE_WEEKS,
    max_block_calorie_delta: int | None = None,
    week_ranges: list[tuple[int, int]] | tuple[tuple[int, int], ...] | None = None,
) -> list[NutritionBlock]:
    """Project nutrition targets per block from initial weight + kg/week goal.

    Pass ``week_ranges`` (inclusive) for challenge phases, e.g. ((1,4),(5,8),(9,14)).
    """
    goal_n = (goal or "maintain").lower()
    if payload.get("weight_kg") in (None, ""):
        return []
    initial_weight = float(payload.get("weight_kg") or 65)
    kg_rate = (
        parse_kg_per_week(payload, goal=goal_n)
        if goal_n in {"lose_weight", "gain_weight"}
        else 0.0
    )
    weeks = max(1, int(duration_weeks or 1))
    gender = (payload.get("gender") or "male").lower()
    if gender not in {"male", "female"}:
        gender = "male"

    ranges: list[tuple[int, int]]
    if week_ranges:
        ranges = [(int(a), int(b)) for a, b in week_ranges if int(b) >= int(a)]
        ranges = [(a, min(b, weeks)) for a, b in ranges if a <= weeks]
    else:
        num_blocks = max(1, (weeks + block_size - 1) // block_size)
        ranges = [
            (bi * block_size + 1, min(weeks, (bi + 1) * block_size)) for bi in range(num_blocks)
        ]

    use_monthly_delta = bool(week_ranges) or block_size >= CURRICULUM_BLOCK_SIZE_WEEKS
    delta_cap = (
        max_block_calorie_delta
        if max_block_calorie_delta is not None
        else (MAX_BLOCK_CALORIE_DELTA_MONTHLY if use_monthly_delta else MAX_BLOCK_CALORIE_DELTA)
    )

    blocks: list[NutritionBlock] = []
    prev_avg: int | None = None

    for bi, (week_from, week_to) in enumerate(ranges):
        # Project weight using weeks elapsed before this block (not fixed block_size).
        weeks_before = max(0, week_from - 1)
        if goal_n == "lose_weight":
            pw = max(30.0, initial_weight - kg_rate * weeks_before)
        elif goal_n == "gain_weight":
            pw = initial_weight + kg_rate * weeks_before
        else:
            pw = initial_weight
        block_payload = {**payload, "weight_kg": pw}
        nt = estimate_targets(block_payload)
        if nt is None:
            break
        avg = clamp_block_avg_target(nt.target_calories, prev_avg, goal_n, max_delta=delta_cap)
        prev_avg = avg
        schedule = build_weekly_calorie_schedule(
            goal=goal_n,
            avg_target=avg,
            split_roles=split_roles,
            gender=gender,
            weight_kg=pw,
            bmr=float(nt.bmr),
            base=nt,
        )
        blocks.append(
            NutritionBlock(
                block_index=bi,
                week_from=week_from,
                week_to=week_to,
                projected_weight_kg=round(pw, 1),
                targets=nt,
                schedule=schedule,
            )
        )
    return blocks


def deload_week_avg_target(*, goal: str, block_avg: int, tdee: int) -> int:
    """Cut: nudge deload week toward maintenance; bulk/maintain: keep block avg."""
    goal_n = (goal or "maintain").lower()
    if goal_n != "lose_weight":
        return int(block_avg)
    # Blend 70% TDEE + 30% deficit avg — soft recovery without undoing the cut.
    blended = int(round(0.7 * int(tdee) + 0.3 * int(block_avg)))
    return max(int(block_avg), min(int(tdee), blended))


def split_role_category(split_role: str | None) -> SessionKind:
    role = (split_role or "").lower().strip().replace("-", "_").replace(" ", "_")
    if role in _CARDIO_ROLES:
        return "cardio"
    if role in _FULLBODY_ROLES:
        return "fullbody"
    if role in _STRENGTH_ROLES or role:
        return "strength"
    return "strength"


def _multiplier(goal: str, kind: SessionKind) -> float:
    table = _CALORIE_MULTIPLIERS.get(goal.lower(), _CALORIE_MULTIPLIERS["maintain"])
    return table.get(kind, 1.0)


def targets_for_calories(
    base: NutritionTargets,
    *,
    goal: str,
    weight_kg: float,
    target_calories: int,
) -> NutritionTargets:
    protein, carbs, fat = _macros_for(goal, weight_kg, int(target_calories))
    meals = 4 if target_calories >= 1800 else 3
    return NutritionTargets(
        bmr=base.bmr,
        tdee=base.tdee,
        target_calories=int(target_calories),
        protein_g=protein,
        carbs_g=carbs,
        fat_g=fat,
        meals_per_day=meals,
        kg_per_week=base.kg_per_week,
        delta_kcal=int(target_calories) - base.tdee,
        clamped=base.clamped,
        notes_vi=base.notes_vi,
    )


def build_weekly_calorie_schedule(
    *,
    goal: str,
    avg_target: int,
    split_roles: list[str | None],
    gender: str,  # noqa: ARG001 — kept for callers
    weight_kg: float,  # noqa: ARG001
    bmr: float,  # noqa: ARG001
    base: NutritionTargets,
) -> WeeklyCalorieSchedule:
    """Balance training vs rest calories so 7-day sum equals 7 * avg_target."""
    goal_n = (goal or "maintain").lower()
    sessions = len(split_roles)
    rest_days = max(0, 7 - sessions)

    kinds: list[SessionKind] = [split_role_category(r) for r in split_roles]
    train_raw = [avg_target * _multiplier(goal_n, k) for k in kinds]
    if rest_days > 0:
        rest_raw = (7 * avg_target - sum(train_raw)) / rest_days
    else:
        rest_raw = avg_target * _multiplier(goal_n, "rest")

    train_kcals = [max(1, int(round(v))) for v in train_raw]
    rest_kcal = max(1, int(round(rest_raw))) if rest_days > 0 else int(round(rest_raw))

    target_total = 7 * avg_target
    total = sum(train_kcals) + rest_days * rest_kcal
    if total != target_total and train_kcals:
        remainder = target_total - total
        train_kcals[-1] = max(1, train_kcals[-1] + remainder)
        total = sum(train_kcals) + rest_days * rest_kcal
        if total != target_total and rest_days > 0:
            rest_kcal = max(1, rest_kcal + (target_total - total) // rest_days)

    training: list[DayCalorieTarget] = []
    for role, kind, kcal in zip(split_roles, kinds, train_kcals):
        training.append(
            DayCalorieTarget(
                split_role=role,
                session_kind=kind,
                targets=targets_for_calories(
                    base, goal=goal_n, weight_kg=weight_kg, target_calories=kcal
                ),
            )
        )

    rest_targets = targets_for_calories(
        base, goal=goal_n, weight_kg=weight_kg, target_calories=rest_kcal
    )
    return WeeklyCalorieSchedule(
        avg_target=int(avg_target),
        training=tuple(training),
        rest=rest_targets,
        rest_days_per_week=rest_days,
    )


def activity_factor(activity: str) -> float:
    return ACTIVITY_FACTORS.get((activity or "").lower(), 1.375)


LOSS_WEEKLY_PCT_MIN = 0.005
LOSS_WEEKLY_PCT_MAX = 0.01
LOSS_WEEKLY_KG_ABS_MIN = 0.2
LOSS_WEEKLY_KG_ABS_MAX = 1.5
GAIN_WEEKLY_PCT_MIN = 0.0025
GAIN_WEEKLY_PCT_DEFAULT = 0.005
GAIN_WEEKLY_PCT_MAX = 0.0075
GAIN_WEEKLY_KG_ABS_MIN = 0.1
GAIN_WEEKLY_KG_ABS_MAX = 1.5


def _payload_weight_kg(payload: dict[str, Any]) -> float | None:
    raw = payload.get("weight_kg")
    if raw in (None, ""):
        return None
    try:
        weight = float(raw)
    except (TypeError, ValueError):
        return None
    if weight <= 0:
        return None
    return weight


def _round_weekly_kg(kg: float) -> float:
    return round(kg * 20) / 20


def parse_kg_per_week(payload: dict[str, Any], *, goal: str) -> float:
    raw = payload.get("kg_per_week")
    if goal == "lose_weight":
        weight = _payload_weight_kg(payload)
        if weight is not None:
            lo = max(LOSS_WEEKLY_KG_ABS_MIN, _round_weekly_kg(weight * LOSS_WEEKLY_PCT_MIN))
            hi = min(LOSS_WEEKLY_KG_ABS_MAX, _round_weekly_kg(weight * LOSS_WEEKLY_PCT_MAX))
            if hi < lo:
                hi = lo
            default = max(lo, min(hi, _round_weekly_kg(weight * 0.0075)))
        else:
            # Không có cân nặng: giữ khung kg cũ để tương thích test / payload thiếu.
            default, lo, hi = 0.5, 0.5, 1.0
    elif goal == "gain_weight":
        weight = _payload_weight_kg(payload)
        if weight is not None:
            lo = max(GAIN_WEEKLY_KG_ABS_MIN, _round_weekly_kg(weight * GAIN_WEEKLY_PCT_MIN))
            hi = min(GAIN_WEEKLY_KG_ABS_MAX, _round_weekly_kg(weight * GAIN_WEEKLY_PCT_MAX))
            if hi < lo:
                hi = lo
            default = max(lo, min(hi, _round_weekly_kg(weight * GAIN_WEEKLY_PCT_DEFAULT)))
        else:
            default, lo, hi = 0.5, 0.25, 0.75
    else:
        return 0.0
    try:
        rate = float(raw) if raw not in (None, "") else default
    except (TypeError, ValueError):
        rate = default
    return max(lo, min(hi, rate))


def desired_calorie_adjustment(goal: str, payload: dict[str, Any]) -> int:
    if goal == "lose_weight":
        return -int(round(parse_kg_per_week(payload, goal=goal) * KCAL_PER_KG / 7))
    if goal == "gain_weight":
        return int(round(parse_kg_per_week(payload, goal=goal) * KCAL_PER_KG / 7))
    return {"maintain": 0, "gain_muscle": GAIN_MUSCLE_SURPLUS}.get(goal, 0)


def _macros_for(goal: str, weight: float, target: int) -> tuple[float, float, float]:
    """Protein/fat by goal; always leave a carb floor so cuts do not go to ~0g carbs."""
    goal_n = (goal or "maintain").lower()
    if goal_n == "lose_weight":
        protein = weight * 1.8
        fat = max(weight * 0.7, 0.20 * target / 9, 35.0)
    elif goal_n in {"gain_weight", "gain_muscle"}:
        protein = weight * 2.0
        fat = max(weight * 0.9, 0.22 * target / 9, 40.0)
    else:
        protein = weight * 1.8
        fat = max(weight * 0.8, 0.20 * target / 9, 35.0)

    protein = max(weight * 1.6, min(weight * 2.0, protein))
    fat = min(fat, 0.30 * max(target, 1) / 9)

    # Smaller of 1.5 g/kg vs 20% kcal — still at least ~15% kcal or 40g.
    carb_floor = min(weight * 1.5, 0.20 * max(target, 1) / 4)
    carb_floor = max(carb_floor, min(40.0, 0.15 * max(target, 1) / 4))
    pf_budget = max(1.0, float(target) - carb_floor * 4)

    protein_cal = protein * 4
    fat_cal = fat * 9
    if protein_cal + fat_cal > pf_budget:
        fat_floor = max(weight * 0.6, 0.18 * target / 9, 35.0)
        fat = min(fat, max(fat_floor, (pf_budget - protein_cal) / 9))
        fat = max(weight * 0.5, fat)
        fat_cal = fat * 9
        if protein_cal + fat_cal > pf_budget:
            protein = max(weight * 1.6, (pf_budget - fat_cal) / 4)

    carbs = max(carb_floor, (target - protein * 4 - fat * 9) / 4)
    # If rounding pushed P+F over target, shave fat again.
    overflow = protein * 4 + fat * 9 + carbs * 4 - target
    if overflow > 4:
        fat = max(weight * 0.5, fat - overflow / 9)
        carbs = max(carb_floor, (target - protein * 4 - fat * 9) / 4)
    return round(protein, 1), round(carbs, 1), round(fat, 1)


def estimate_targets(payload: dict[str, Any]) -> NutritionTargets | None:
    if payload.get("weight_kg") in (None, "") or payload.get("height_cm") in (None, ""):
        return None
    gender = (payload.get("gender") or "male").lower()
    if gender not in {"male", "female"}:
        gender = "male"
    weight = float(payload.get("weight_kg") or 65)
    height = float(payload.get("height_cm") or 170)
    age = int(payload.get("age") or 25)
    if gender == "female":
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    tdee = int(bmr * activity_factor(str(payload.get("activity") or "moderate")))
    goal = (payload.get("goal") or "maintain").lower()
    desired = desired_calorie_adjustment(goal, payload)
    target = max(1, tdee + desired)

    protein, carbs, fat = _macros_for(goal, weight, target)
    meals = 4 if target >= 1800 else 3
    kg = parse_kg_per_week(payload, goal=goal) if goal in {"lose_weight", "gain_weight"} else None

    return NutritionTargets(
        bmr=int(bmr),
        tdee=tdee,
        target_calories=int(target),
        protein_g=protein,
        carbs_g=carbs,
        fat_g=fat,
        meals_per_day=meals,
        kg_per_week=kg,
        delta_kcal=int(target) - tdee,
        clamped=False,
        notes_vi=(),
    )
