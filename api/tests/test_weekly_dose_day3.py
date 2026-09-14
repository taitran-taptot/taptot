"""Weekly dose must not gut day 3; reduce isolation sets before dropping lifts."""

from types import SimpleNamespace

from app.services.workout_generation.weekly_volume import (
    apply_weekly_dose,
    apply_weekly_dose_expanded,
    count_weekly_sets,
    main_exercise_count,
    weekly_budget,
)


def _ex(eid: int, sets: int = 3, section: str = "main") -> SimpleNamespace:
    return SimpleNamespace(exercise_id=eid, section=section, sets=sets)


def _day(role: str, eids: list[int], sets: int = 3) -> SimpleNamespace:
    return SimpleNamespace(
        split_role=role,
        exercises=[_ex(eid, sets=sets) for eid in eids],
    )


def _mains(day) -> list[int]:
    return [ex.exercise_id for ex in day.exercises if (ex.section or "main") == "main"]


def test_lul_day3_keeps_main_count_near_day1():
    meta = {
        1: {"movement_role": "compound", "movement_pattern": "squat", "muscle_slug": "quads"},
        2: {"movement_role": "compound", "movement_pattern": "hinge", "muscle_slug": "hamstrings"},
        3: {"movement_role": "isolation", "movement_pattern": "hinge", "muscle_slug": "hamstrings"},
        4: {"movement_role": "isolation", "movement_pattern": "hinge", "muscle_slug": "glutes"},
        5: {"movement_role": "isolation", "movement_pattern": "hinge", "muscle_slug": "hamstrings"},
        10: {"movement_role": "compound", "movement_pattern": "h_push", "muscle_slug": "chest"},
        11: {"movement_role": "compound", "movement_pattern": "h_pull", "muscle_slug": "back"},
        12: {"movement_role": "isolation", "movement_pattern": "h_push", "muscle_slug": "chest"},
        13: {"movement_role": "isolation", "movement_pattern": "h_pull", "muscle_slug": "back"},
    }
    days = [
        _day("lower", [1, 2, 3, 4, 5]),
        _day("upper", [10, 11, 12, 13]),
        _day("lower", [1, 2, 3, 4, 5]),
    ]
    out, _note = apply_weekly_dose(
        days,
        meta_by_id=meta,
        effective_level=1,
        strength_tier="ok",
        focus_slugs=frozenset(),
        session_minutes=60,
    )
    d1, d3 = out[0], out[2]
    assert main_exercise_count(d3) >= 3
    assert abs(main_exercise_count(d3) - main_exercise_count(d1)) <= 1
    assert 1 in _mains(d3) and 2 in _mains(d3)
    hinge_iso = [eid for eid in _mains(d3) if eid in {3, 4, 5}]
    assert len(hinge_iso) >= 1
    counts = count_weekly_sets(out, meta)
    assert counts.get("hinge", 0) <= weekly_budget(1)["hinge"].max_sets


def test_fb_day3_not_stripped_to_one_compound():
    meta = {
        1: {"movement_role": "compound", "movement_pattern": "squat", "muscle_slug": "quads"},
        2: {"movement_role": "compound", "movement_pattern": "hinge", "muscle_slug": "hamstrings"},
        3: {"movement_role": "compound", "movement_pattern": "h_push", "muscle_slug": "chest"},
        4: {"movement_role": "compound", "movement_pattern": "h_pull", "muscle_slug": "back"},
        5: {"movement_role": "isolation", "movement_pattern": "h_push", "muscle_slug": "chest"},
        6: {"movement_role": "isolation", "movement_pattern": "h_pull", "muscle_slug": "back"},
        7: {"movement_role": "isolation", "movement_pattern": "hinge", "muscle_slug": "glutes"},
    }
    days = [_day("fb", [1, 2, 3, 4, 5, 6, 7]) for _ in range(3)]
    out, _note = apply_weekly_dose(
        days,
        meta_by_id=meta,
        effective_level=1,
        strength_tier="ok",
        focus_slugs=frozenset(),
        session_minutes=60,
    )
    d1, d3 = out[0], out[2]
    assert main_exercise_count(d3) >= 3
    assert abs(main_exercise_count(d3) - main_exercise_count(d1)) <= 1
    assert {1, 2, 3, 4} & set(_mains(d3))
    counts = count_weekly_sets(out, meta)
    budget = weekly_budget(1)
    for fam in ("chest", "back", "hinge"):
        assert counts.get(fam, 0) <= budget[fam].max_sets


def test_ppl_legs_keeps_hinge_and_isolation():
    meta = {
        1: {"movement_role": "compound", "movement_pattern": "h_push", "muscle_slug": "chest"},
        2: {"movement_role": "isolation", "movement_pattern": "h_push", "muscle_slug": "triceps"},
        10: {"movement_role": "compound", "movement_pattern": "h_pull", "muscle_slug": "back"},
        11: {"movement_role": "isolation", "movement_pattern": "h_pull", "muscle_slug": "biceps"},
        20: {"movement_role": "compound", "movement_pattern": "squat", "muscle_slug": "quads"},
        21: {"movement_role": "compound", "movement_pattern": "hinge", "muscle_slug": "hamstrings"},
        22: {"movement_role": "isolation", "movement_pattern": "hinge", "muscle_slug": "hamstrings"},
        23: {"movement_role": "isolation", "movement_pattern": "hinge", "muscle_slug": "glutes"},
        24: {"movement_role": "isolation", "movement_pattern": "hinge", "muscle_slug": "hamstrings"},
    }
    days = [
        _day("push", [1, 2]),
        _day("pull", [10, 11]),
        _day("legs", [20, 21, 22, 23, 24]),
    ]
    out, _note = apply_weekly_dose(
        days,
        meta_by_id=meta,
        effective_level=1,
        strength_tier="ok",
        focus_slugs=frozenset(),
        session_minutes=60,
    )
    legs = out[2]
    ids = set(_mains(legs))
    assert 21 in ids
    assert ids & {22, 23, 24}
    counts = count_weekly_sets(out, meta)
    assert counts.get("hinge", 0) <= weekly_budget(1)["hinge"].max_sets


def test_over_budget_reduces_sets_before_dropping_exercise():
    meta = {
        1: {"movement_role": "compound", "movement_pattern": "h_push", "muscle_slug": "chest"},
        2: {"movement_role": "isolation", "movement_pattern": "h_push", "muscle_slug": "triceps"},
        3: {"movement_role": "isolation", "movement_pattern": "v_push", "muscle_slug": "triceps"},
        4: {"movement_role": "isolation", "movement_pattern": "isolation", "muscle_slug": "triceps"},
    }
    days = [_day("push", [1, 2, 3, 4], sets=3)]
    out, _note = apply_weekly_dose(
        days,
        meta_by_id=meta,
        effective_level=1,
        strength_tier="ok",
        focus_slugs=frozenset(),
        session_minutes=75,
    )
    iso = [ex for ex in out[0].exercises if ex.exercise_id in {2, 3, 4}]
    assert 1 <= len(iso) <= 3
    if len(iso) == 3:
        assert all(ex.sets == 2 for ex in iso)
    counts = count_weekly_sets(out, meta)
    assert counts.get("triceps", 0) <= weekly_budget(1)["triceps"].max_sets
    assert any(ex.exercise_id == 1 for ex in out[0].exercises)


def test_expanded_week4_does_not_drop_extra_exercises():
    meta = {
        1: {"movement_role": "compound", "movement_pattern": "h_push", "muscle_slug": "chest"},
        2: {"movement_role": "isolation", "movement_pattern": "h_push", "muscle_slug": "triceps"},
        3: {"movement_role": "isolation", "movement_pattern": "h_push", "muscle_slug": "triceps"},
    }
    expanded = []
    for week_n in range(1, 5):
        bonus = 1 if week_n >= 4 else 0
        expanded.append(
            SimpleNamespace(
                split_role="push",
                exercises=[
                    SimpleNamespace(exercise_id=1, section="main", sets=3 + bonus),
                    SimpleNamespace(exercise_id=2, section="main", sets=4 + bonus),
                    SimpleNamespace(exercise_id=3, section="main", sets=4 + bonus),
                ],
            )
        )
    before_ids = [tuple(ex.exercise_id for ex in expanded[3].exercises)]
    out, _note = apply_weekly_dose_expanded(
        expanded,
        sessions_per_week=1,
        meta_by_id=meta,
        effective_level=3,
        strength_tier="ok",
        focus_slugs=frozenset(),
        session_minutes=45,
    )
    after_ids = tuple(ex.exercise_id for ex in out[3].exercises)
    assert after_ids == before_ids[0]
    w4 = count_weekly_sets([out[3]], meta)
    assert w4.get("triceps", 0) <= weekly_budget(3)["triceps"].max_sets
    iso = [ex for ex in out[3].exercises if ex.exercise_id in {2, 3}]
    assert len(iso) == 2
    assert any(ex.exercise_id == 1 for ex in out[3].exercises)
