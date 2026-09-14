"""Catalog of Master schedule cases: gym + home body + home kits.

Used by pytest (split / recipe, no OpenAI) and the Excel batch generator.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.schedule_spec_master import (
    day_label_to_split_role,
    expand_week_days,
    experience_to_master_key,
    lookup_week_split,
)
from app.services.workout_generation.capacity import resolve_capacity
from app.services.workout_generation.session_policy import resolve_session_policy
from app.services.workout_generation.split_score import pick_week_code

MINUTES: tuple[int, ...] = (30, 45, 60, 75, 90)
GENDERS: tuple[str, ...] = ("male", "female")
LEVELS: tuple[int, ...] = (1, 2, 3)
SESSIONS: tuple[int, ...] = (2, 3, 4, 5, 6)

# gym | home all public gear | home bodyweight — gym is always loaded.
VENUES: tuple[tuple[str, bool, str], ...] = (
    ("gym", False, "gym"),
    ("home", False, "home_all"),
    ("home", True, "home_body"),
)
CORE_VENUE_KEYS = frozenset({"gym", "home_body", "home_all"})

# Public home catalog (frontend/src/lib/equipmentCatalog.ts).
HOME_PUBLIC_KEYS: tuple[str, ...] = (
    "parallel-bars",
    "pull-up-bar",
    "dumbbell",
    "jump-rope",
    "resistance-band",
    "gymnastic-rings",
)

# kit_id, equipment_list — singletons plus engine-distinct family combos.
# Public "resistance-band" expands to both loop and tube catalogs at generate time.
HOME_COVERAGE_KITS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("parallel-bars", ("parallel-bars",)),
    ("pull-up-bar", ("pull-up-bar",)),
    ("dumbbell", ("dumbbell",)),
    ("jump-rope", ("jump-rope",)),
    ("resistance-band", ("resistance-band",)),
    ("gymnastic-rings", ("gymnastic-rings",)),
    ("bars", ("pull-up-bar", "parallel-bars")),
    ("db_bar", ("dumbbell", "pull-up-bar")),
)

# gender, level, sessions, minutes
HOME_COVERAGE_CELLS: tuple[tuple[str, int, int, int], ...] = (
    ("male", 1, 3, 30),
    ("female", 1, 4, 45),
    ("male", 2, 4, 60),
    ("female", 2, 5, 75),
    ("male", 3, 3, 90),
    ("female", 3, 6, 45),
)


@dataclass(frozen=True)
class ScheduleCase:
    case_id: str
    gender: str
    experience_level: int
    sessions_requested: int
    sessions_actual: int
    session_minutes: int
    location: str
    no_equipment: bool
    venue_key: str
    expected_week_code: str
    expected_roles: tuple[str, ...]
    overlay_expected: bool
    matrix_week_code: str
    equipment_list: tuple[str, ...] = field(default_factory=tuple)

    def to_payload(self) -> dict:
        female = self.gender == "female"
        return {
            "goal": "maintain",
            "gender": self.gender,
            "age": 28,
            "height_cm": 162.0 if female else 175.0,
            "weight_kg": 56.0 if female else 75.0,
            "activity": "moderate",
            "sessions_per_week": self.sessions_requested,
            "session_minutes": self.session_minutes,
            "location": self.location,
            "focus_areas": [],
            "extra_goals": [],
            "equipment_list": list(self.equipment_list),
            "food_ids": [],
            "experience_level": self.experience_level,
            "ai_suggest_equipment": False,
            "no_equipment": self.no_equipment,
            "ai_suggest_foods": False,
            "duration_weeks": 4,
        }


def _expected_split(
    *,
    gender: str,
    experience_level: int,
    sessions_requested: int,
    session_minutes: int,
    location: str,
    no_equipment: bool,
) -> tuple[int, str, str, bool, tuple[str, ...]]:
    capacity = resolve_capacity(experience_level, None, sessions_per_week=sessions_requested)
    policy = resolve_session_policy(
        capacity,
        goal="maintain",
        session_minutes=session_minutes,
    )
    sessions_actual = policy.clamp_sessions(sessions_requested)
    matrix_code = lookup_week_split(
        experience=experience_to_master_key(capacity.effective_level),
        sessions=sessions_actual,
        gender=gender,
        location=location,
        home_equip="no_equip" if no_equipment else "with_equip",
    ) or ""
    choice = pick_week_code(
        matrix_code,
        sessions=sessions_actual,
        capacity=capacity,
        goal="maintain",
        no_equipment=no_equipment,
    )
    labels = expand_week_days(choice.week_code)
    roles = tuple(day_label_to_split_role(lbl) for lbl in labels[:sessions_actual])
    return sessions_actual, matrix_code, choice.week_code, bool(choice.overridden), roles


def _build_case(
    *,
    gender: str,
    level: int,
    sessions: int,
    mins: int,
    location: str,
    no_equipment: bool,
    venue_key: str,
    equipment_list: tuple[str, ...] = (),
) -> ScheduleCase:
    sessions_actual, matrix_code, week_code, overlay, roles = _expected_split(
        gender=gender,
        experience_level=level,
        sessions_requested=sessions,
        session_minutes=mins,
        location=location,
        no_equipment=no_equipment,
    )
    g = "F" if gender == "female" else "M"
    return ScheduleCase(
        case_id=f"{g}_L{level}_{sessions}d_{mins}m_{venue_key}",
        gender=gender,
        experience_level=level,
        sessions_requested=sessions,
        sessions_actual=sessions_actual,
        session_minutes=mins,
        location=location,
        no_equipment=no_equipment,
        venue_key=venue_key,
        expected_week_code=week_code,
        expected_roles=roles,
        overlay_expected=overlay,
        matrix_week_code=matrix_code,
        equipment_list=equipment_list,
    )


def iter_schedule_cases(*, minutes: tuple[int, ...] | None = None) -> list[ScheduleCase]:
    """Gym + home_body + home_all (all minute buckets) and home coverage kits."""
    buckets = minutes if minutes is not None else MINUTES
    out: list[ScheduleCase] = []
    for gender in GENDERS:
        for level in LEVELS:
            for sessions in SESSIONS:
                for location, no_equipment, venue_key in VENUES:
                    for mins in buckets:
                        equip = HOME_PUBLIC_KEYS if venue_key == "home_all" else ()
                        out.append(
                            _build_case(
                                gender=gender,
                                level=level,
                                sessions=sessions,
                                mins=mins,
                                location=location,
                                no_equipment=no_equipment,
                                venue_key=venue_key,
                                equipment_list=equip,
                            )
                        )
    bucket_set = set(buckets)
    for gender, level, sessions, mins in HOME_COVERAGE_CELLS:
        if mins not in bucket_set:
            continue
        for kit_id, equip in HOME_COVERAGE_KITS:
            out.append(
                _build_case(
                    gender=gender,
                    level=level,
                    sessions=sessions,
                    mins=mins,
                    location="home",
                    no_equipment=False,
                    venue_key=f"home_{kit_id}",
                    equipment_list=equip,
                )
            )
    return out


def filter_schedule_cases(
    cases: list[ScheduleCase],
    venue: str | None,
) -> list[ScheduleCase]:
    """Filter catalog by --venue. `home` = every home case; `home_equip` aliases home_all."""
    key = str(venue or "").strip()
    if not key:
        return list(cases)
    if key == "home":
        return [c for c in cases if c.location == "home"]
    if key == "home_equip":
        key = "home_all"
    return [c for c in cases if c.venue_key == key]


def iter_split_cells() -> list[ScheduleCase]:
    """90 Master cells (minutes do not change split). Uses 60 min as representative."""
    return [
        c
        for c in iter_schedule_cases(minutes=(60,))
        if c.venue_key in CORE_VENUE_KEYS
    ]
