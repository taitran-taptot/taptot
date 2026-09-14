"""Master schedule matrix: 90 split cells (no OpenAI)."""

import pytest

from app.services.session_blocks import get_master_session_recipe
from app.services.schedule_spec_master import (
    day_label_to_split_role,
    expand_week_days,
    experience_to_master_key,
    lookup_week_split,
)
from app.services.workout_generation.schedule_case_matrix import (
    HOME_COVERAGE_CELLS,
    HOME_COVERAGE_KITS,
    HOME_PUBLIC_KEYS,
    MINUTES,
    iter_schedule_cases,
    iter_split_cells,
)
from app.services.workout_generation.session_policy import resolve_session_policy
from app.services.workout_generation.capacity import resolve_capacity


def test_gym_catalog_is_150_cases():
    gym = [c for c in iter_schedule_cases() if c.venue_key == "gym"]
    assert len(gym) == 150
    assert all(c.location == "gym" and not c.no_equipment for c in gym)


def test_home_challenge_catalog_is_348_cases():
    home = [c for c in iter_schedule_cases() if c.location == "home"]
    body = [c for c in home if c.venue_key == "home_body"]
    full = [c for c in home if c.venue_key == "home_all"]
    kits = [c for c in home if c.venue_key not in {"home_body", "home_all"}]
    assert len(body) == 150
    assert all(c.no_equipment and c.equipment_list == () for c in body)
    assert len(full) == 150
    assert all(c.equipment_list == HOME_PUBLIC_KEYS and not c.no_equipment for c in full)
    assert "bench" not in HOME_PUBLIC_KEYS
    assert "resistance-band" in HOME_PUBLIC_KEYS
    assert "resistance-band-1" not in HOME_PUBLIC_KEYS
    assert len(kits) == len(HOME_COVERAGE_KITS) * len(HOME_COVERAGE_CELLS) == 48
    kit_ids = {c.venue_key for c in kits}
    assert kit_ids == {f"home_{kid}" for kid, _ in HOME_COVERAGE_KITS}
    assert len(home) == 348
    assert all("bench" not in c.equipment_list for c in home)
    ids = [c.case_id for c in iter_schedule_cases()]
    assert len(ids) == len(set(ids)) == 498


def test_split_cells_are_90():
    cells = iter_split_cells()
    assert len(cells) == 90
    assert all(c.session_minutes == 60 for c in cells)


@pytest.mark.parametrize("case", iter_split_cells(), ids=lambda c: c.case_id)
def test_split_cell_matches_master_and_clamp(case):
    capacity = resolve_capacity(case.experience_level, None)
    policy = resolve_session_policy(capacity, goal="maintain", session_minutes=60)
    assert case.sessions_actual == policy.clamp_sessions(case.sessions_requested)
    if case.experience_level <= 1:
        assert case.sessions_actual <= 5
        if case.sessions_requested == 6:
            assert case.sessions_actual == 5

    matrix = lookup_week_split(
        experience=experience_to_master_key(case.experience_level),
        sessions=case.sessions_actual,
        gender=case.gender,
        location=case.location,
        home_equip="no_equip" if case.no_equipment else "with_equip",
    )
    assert matrix == case.matrix_week_code
    labels = expand_week_days(case.expected_week_code)
    roles = [day_label_to_split_role(lbl) for lbl in labels[: case.sessions_actual]]
    assert tuple(roles) == case.expected_roles
    assert len(case.expected_roles) == case.sessions_actual
    if not case.overlay_expected:
        assert case.expected_week_code == case.matrix_week_code


@pytest.mark.parametrize("case", iter_split_cells(), ids=lambda c: f"{c.case_id}_recipe")
def test_session_recipe_one_stretch_warmup(case):
    role = case.expected_roles[0] if case.expected_roles else "upper"
    blocks = get_master_session_recipe(
        location=case.location,
        session_minutes=case.session_minutes,
        split_role=role,
        experience_level=case.experience_level,
    )
    by_key = {b.block_key: b for b in blocks}
    wu = by_key.get("general_warmup")
    assert wu is not None
    assert wu.count_max == 1
    assert "dynamic_mobility" not in by_key
    assert (wu.duration_min_minutes or 0) <= 5


@pytest.mark.parametrize("minutes", MINUTES)
@pytest.mark.parametrize("location", ["gym", "home"])
def test_recipe_minutes_buckets_keep_single_warmup(minutes, location):
    blocks = get_master_session_recipe(
        location=location,
        session_minutes=minutes,
        split_role="upper",
        experience_level=2,
    )
    wu = next(b for b in blocks if b.block_key == "general_warmup")
    assert wu.count_max == 1
    assert not any(b.block_key == "dynamic_mobility" for b in blocks)


def test_generate_workout_accepts_persist_flag():
    import inspect

    from app.services.workout_generation.service import generate_workout

    params = inspect.signature(generate_workout).parameters
    assert "persist" in params
    assert params["persist"].default is True
    assert params["persist"].kind is inspect.Parameter.KEYWORD_ONLY
