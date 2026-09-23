"""Unit tests for GPT V1.5 capacity, split overlay, focus, weekly set budget."""

from types import SimpleNamespace

from app.services.exercise_prescription import reps_range_from_center, rpe_for
from app.services.schedule_spec_master import lookup_week_split
from app.services.workout_generation.capacity import resolve_capacity
from app.services.workout_generation.focus import focus_muscle_slugs, is_focus_muscle
from app.services.workout_generation.muscle_quotas import quotas_for_split
from app.services.workout_generation.split_score import pick_week_code, week_family
from app.services.workout_generation.weekly_volume import (
    apply_weekly_dose,
    count_weekly_sets,
    weekly_budget,
)


def test_capacity_missing_tests_ok_same_level():
    cap = resolve_capacity(2, None)
    assert cap.strength_tier == "ok"
    assert cap.effective_level == 2
    assert cap.tests_used == 0
    assert cap.reason_vi is None


def test_capacity_l3_without_two_tests_keeps_level_3_conservative():
    cap = resolve_capacity(3, None)
    assert cap.strength_tier == "ok"
    assert cap.effective_level == 3
    assert cap.tests_used == 0
    assert cap.conservative_volume is True
    assert cap.reason_vi

    one = resolve_capacity(3, {"pushups_max": 20})
    assert one.tests_used == 1
    assert one.effective_level == 3
    assert one.conservative_volume is True
    assert one.reason_vi


def test_capacity_weak_tests_downgrade_level():
    cap = resolve_capacity(
        3,
        {"pushups_max": 1, "pullups_max": 0, "plank_seconds": 10, "squats_max": 2},
    )
    assert cap.strength_tier == "weak"
    assert cap.effective_level == 2
    assert cap.reason_vi


def test_capacity_strong_does_not_promote():
    cap = resolve_capacity(
        1,
        {"pushups_max": 25, "pullups_max": 12, "plank_seconds": 90, "squats_max": 40},
    )
    assert cap.strength_tier == "strong"
    assert cap.effective_level == 1


def test_split_beginner_3_days_keeps_ppl():
    cap = resolve_capacity(1, None)
    choice = pick_week_code("PPL", sessions=3, capacity=cap)
    assert week_family(choice.week_code) == "ppl"
    assert not choice.overridden


def test_split_weak_tests_3_days_keeps_ppl():
    cap = resolve_capacity(
        1, {"pushups_max": 2, "pullups_max": 0, "plank_seconds": 10, "squats_max": 5}
    )
    assert cap.strength_tier == "weak"
    choice = pick_week_code("PPL", sessions=3, capacity=cap)
    assert week_family(choice.week_code) == "ppl"
    assert not choice.overridden
    assert choice.week_code == "PPL"


def test_split_no_equip_3_days_keeps_ppl():
    cap = resolve_capacity(2, None)
    choice = pick_week_code("PPL", sessions=3, capacity=cap, no_equipment=True)
    assert week_family(choice.week_code) == "ppl"
    assert not choice.overridden
    assert choice.week_code == "PPL"


def test_split_no_equip_3_days_keeps_ulu_master():
    cap = resolve_capacity(2, None)
    choice = pick_week_code("ULU", sessions=3, capacity=cap, no_equipment=True)
    assert week_family(choice.week_code) == "ul"
    assert not choice.overridden
    assert choice.week_code == "ULU"


def test_split_does_not_override_female_lul():
    cap = resolve_capacity(1, None)
    choice = pick_week_code("LUL", sessions=3, capacity=cap, no_equipment=True)
    assert choice.week_code == "LUL"
    assert week_family(choice.week_code) == "ul"
    assert not choice.overridden


def test_split_does_not_override_female_lppl():
    cap = resolve_capacity(1, None)
    choice = pick_week_code("LPPL", sessions=4, capacity=cap)
    assert choice.week_code == "LPPL"
    assert week_family(choice.week_code) == "ul"
    assert not choice.overridden


def test_split_intermediate_3_days_keeps_ppl():
    cap = resolve_capacity(3, {"pushups_max": 12, "squats_max": 20, "plank_seconds": 45})
    assert cap.strength_tier == "ok"
    choice = pick_week_code("PPL", sessions=3, capacity=cap)
    assert week_family(choice.week_code) == "ppl"
    assert not choice.overridden


def test_split_l1_six_days_keeps_ppl_x2():
    cap = resolve_capacity(1, None)
    choice = pick_week_code("PPLPPL", sessions=6, capacity=cap)
    assert week_family(choice.week_code) == "ppl_x2"
    assert choice.week_code == "PPLPPL"
    assert not choice.overridden


def test_split_l1_five_days_keeps_default_ppl_mix():
    cap = resolve_capacity(1, None)
    choice = pick_week_code("PPL, Cardio-Core, FullBody", sessions=5, capacity=cap)
    assert choice.week_code == "PPL, Cardio-Core, FullBody"
    assert not choice.overridden


def test_session_policy_clamps_beginner():
    from app.services.workout_generation.session_policy import resolve_session_policy

    cap = resolve_capacity(1, None)
    policy = resolve_session_policy(cap, goal="gain_weight", session_minutes=90)
    assert policy.clamp_sessions(6) == 5
    assert policy.clamp_sessions(5) == 5
    assert policy.clamp_minutes(90) == 90
    assert policy.clamp_minutes(120) == 90
    assert policy.clamp_weeks(15, challenge=False) == 8
    assert policy.clamp_weeks(15, challenge=True) == 14
    assert policy.clamp_weeks(2, challenge=False) == 4
    assert policy.allow_pplul is True
    assert policy.cardio_on_lift_days is True
    assert policy.easy_cardio is True
    short = resolve_session_policy(cap, goal="gain_weight", session_minutes=45)
    assert short.cardio_on_lift_days is False
    assert short.liss_finisher is False
    liss = resolve_session_policy(
        cap, goal="gain_muscle", session_minutes=45, extra_goals=["endurance"]
    )
    assert liss.liss_finisher is True
    loss = resolve_session_policy(cap, goal="lose_weight", session_minutes=45)
    assert loss.liss_finisher is True
    l2 = resolve_session_policy(resolve_capacity(2, None), goal="gain_weight", session_minutes=90)
    assert l2.clamp_sessions(6) == 6
    assert l2.allow_pplul is True


def test_focus_slugs_chest():
    slugs = focus_muscle_slugs(["nguc"])
    assert "chest" in slugs or "co-nguc" in slugs
    assert is_focus_muscle("chest", slugs)


def test_focus_new_body_goal_keys():
    from app.services.workout_generation.focus import focus_labels_vi

    back = focus_muscle_slugs(["mo_lung"])
    assert back == focus_muscle_slugs(["lung"])
    shoulders = focus_muscle_slugs(["vai_thon"])
    assert shoulders == focus_muscle_slugs(["vai"])
    arms = focus_muscle_slugs(["tay_to"])
    assert arms == focus_muscle_slugs(["tay"])
    labels = focus_labels_vi(["mo_lung", "vai_thon", "tay_to", "eo"])
    assert labels == ["giảm mỡ lưng", "vai thon gọn", "tay to", "giảm mỡ bụng"]


def test_quotas_focus_bumps_chest_min():
    base = quotas_for_split("push")
    bumped = quotas_for_split("push", focus_slugs=focus_muscle_slugs(["nguc"]))
    chest_base = next(b for b in base if b.key == "chest")
    chest_b = next(b for b in bumped if b.key == "chest")
    assert chest_b.min_n == min(chest_base.max_n, chest_base.min_n + 1)
    tri_base = next(b for b in base if b.key == "triceps")
    tri_b = next(b for b in bumped if b.key == "triceps")
    assert tri_b.min_n == tri_base.min_n


def test_split_lookup_uses_gender():
    male = lookup_week_split(
        experience="0-1", sessions=3, gender="male", location="gym", home_equip="with_equip"
    )
    female = lookup_week_split(
        experience="0-1", sessions=3, gender="female", location="gym", home_equip="with_equip"
    )
    assert male != female
    assert male == "PPL"
    assert female == "LUL"


def test_split_lookup_home_no_equip_differs_by_gender():
    male = lookup_week_split(
        experience="1-6", sessions=3, gender="male", location="home", home_equip="no_equip"
    )
    female = lookup_week_split(
        experience="1-6", sessions=3, gender="female", location="home", home_equip="no_equip"
    )
    assert male != female
    assert male == "ULU"
    assert female == "LUL"


def test_split_lookup_female_gym_4d_lppl():
    code = lookup_week_split(
        experience="1-6", sessions=4, gender="female", location="gym", home_equip="with_equip"
    )
    assert code == "LPPL"


def test_split_lookup_l3_gym_3d_ppl():
    code = lookup_week_split(
        experience="6-24", sessions=3, gender="male", location="gym", home_equip="with_equip"
    )
    assert code == "PPL"


def test_split_lookup_l2_gym_4d_ulul():
    code = lookup_week_split(
        experience="1-6", sessions=4, gender="male", location="gym", home_equip="with_equip"
    )
    assert code == "ULUL"


def test_weekly_budget_l2_mains_are_wider_than_l1():
    l1 = weekly_budget(1, strength_tier="ok")
    l2 = weekly_budget(2, strength_tier="ok")
    for fam in ("chest", "back", "quads", "hinge"):
        assert (l2[fam].recommended_min, l2[fam].target_sets, l2[fam].max_sets) == (6, 9, 14)
        assert l1[fam].max_sets == 12


def test_weekly_budget_focus_raises_chest_floor():
    base = weekly_budget(1, strength_tier="ok")
    focused = weekly_budget(1, strength_tier="ok", focus_slugs=frozenset({"chest"}))
    assert focused["chest"].max_sets >= base["chest"].max_sets + 2
    assert focused["chest"].recommended_min >= base["chest"].recommended_min + 1
    assert "biceps" in base and "triceps" in base
    assert "arms" not in base


def test_weekly_dose_drops_isolation_by_sets_not_exercise_count():
    meta = {
        1: {"movement_role": "compound", "movement_pattern": "h_push", "muscle_slug": "chest"},
        2: {"movement_role": "isolation", "movement_pattern": "h_push", "muscle_slug": "triceps"},
    }
    days = []
    for _ in range(7):
        days.append(
            SimpleNamespace(
                split_role="push",
                exercises=[
                    SimpleNamespace(exercise_id=1, section="main", sets=3),
                    SimpleNamespace(exercise_id=2, section="main", sets=3),
                ]
            )
        )
    focus = focus_muscle_slugs(["nguc"])
    out, _note = apply_weekly_dose(
        days,
        meta_by_id=meta,
        effective_level=1,
        strength_tier="ok",
        focus_slugs=focus,
        session_minutes=45,
    )
    counts = count_weekly_sets(out, meta)
    compounds = sum(1 for d in out for ex in d.exercises if ex.exercise_id == 1)
    assert compounds == 7
    assert counts.get("triceps", 0) <= weekly_budget(1)["triceps"].max_sets


def test_clamp_keeps_last_coverage_isolation():
    from app.services.workout_generation.coverage import coverage_ok

    meta = {
        1: {"movement_role": "compound", "movement_pattern": "squat", "muscle_slug": "quads"},
        2: {"movement_role": "compound", "movement_pattern": "hinge", "muscle_slug": "glutes"},
        3: {"movement_role": "compound", "movement_pattern": "h_push", "muscle_slug": "chest"},
        4: {"movement_role": "isolation", "movement_pattern": "h_pull", "muscle_slug": "back"},
    }
    isolations = [
        SimpleNamespace(exercise_id=4, section="main", sets=3) for _ in range(5)
    ]
    days = [
        SimpleNamespace(
            split_role="fb",
            exercises=[
                SimpleNamespace(exercise_id=1, section="main", sets=3),
                SimpleNamespace(exercise_id=2, section="main", sets=3),
                SimpleNamespace(exercise_id=3, section="main", sets=3),
                *isolations,
            ],
        )
    ]
    out, _note = apply_weekly_dose(
        days,
        meta_by_id=meta,
        effective_level=1,
        strength_tier="ok",
        focus_slugs=frozenset(),
        session_minutes=45,
    )
    assert coverage_ok(out, meta)
    pull_left = sum(1 for ex in out[0].exercises if ex.exercise_id == 4)
    assert pull_left >= 1
    counts = count_weekly_sets(out, meta)
    assert counts.get("back", 0) <= weekly_budget(1)["back"].max_sets or pull_left == 1


def test_dose_expanded_reclamps_week_after_set_ramp():
    from app.services.workout_generation.weekly_volume import apply_weekly_dose_expanded

    meta = {
        1: {"movement_role": "compound", "movement_pattern": "h_push", "muscle_slug": "chest"},
        2: {"movement_role": "isolation", "movement_pattern": "h_push", "muscle_slug": "triceps"},
    }
    # One-week template already at triceps max (L3 max 8).
    # Simulate periodization week 4: +1 set on isolations → 10 > max 8
    expanded = []
    for week_n in range(1, 5):
        bonus = 1 if week_n >= 4 else 0
        expanded.append(
            SimpleNamespace(
                split_role="push",
                exercises=[
                    SimpleNamespace(exercise_id=1, section="main", sets=3 + bonus),
                    SimpleNamespace(exercise_id=2, section="main", sets=4 + bonus),
                    SimpleNamespace(exercise_id=2, section="main", sets=4 + bonus),
                ],
            )
        )
    out, _note = apply_weekly_dose_expanded(
        expanded,
        sessions_per_week=1,
        meta_by_id=meta,
        effective_level=3,
        strength_tier="ok",
        focus_slugs=frozenset(),
        session_minutes=45,
    )
    w4 = count_weekly_sets([out[3]], meta)
    assert w4.get("triceps", 0) <= weekly_budget(3)["triceps"].max_sets
    assert any(ex.exercise_id == 1 for ex in out[3].exercises)


def test_weekly_dose_drops_focus_isolation_when_over():
    meta = {
        1: {"movement_role": "compound", "movement_pattern": "h_push", "muscle_slug": "chest"},
        2: {"movement_role": "isolation", "movement_pattern": "v_push", "muscle_slug": "shoulders"},
        3: {"movement_role": "compound", "movement_pattern": "squat", "muscle_slug": "quads"},
        4: {"movement_role": "compound", "movement_pattern": "hinge", "muscle_slug": "hamstrings"},
    }
    days = [
        SimpleNamespace(
            split_role="legs",
            exercises=[
                SimpleNamespace(exercise_id=3, section="main", sets=3),
                SimpleNamespace(exercise_id=4, section="main", sets=3),
                SimpleNamespace(exercise_id=2, section="main", sets=3),
                SimpleNamespace(exercise_id=2, section="main", sets=3),
            ],
        ),
        SimpleNamespace(
            split_role="push",
            exercises=[
                SimpleNamespace(exercise_id=1, section="main", sets=3),
                SimpleNamespace(exercise_id=2, section="main", sets=3),
            ],
        ),
    ]
    out, note = apply_weekly_dose(
        days,
        meta_by_id=meta,
        effective_level=1,
        strength_tier="ok",
        focus_slugs=focus_muscle_slugs(["vai"]),
        session_minutes=75,
    )
    counts = count_weekly_sets(out, meta)
    assert counts.get("shoulders", 0) <= weekly_budget(1, focus_slugs=focus_muscle_slugs(["vai"]))["shoulders"].max_sets
    legs_ids = [ex.exercise_id for ex in out[0].exercises]
    assert 2 not in legs_ids


def test_weekly_dose_drops_upper_tricep_spam_even_if_pull_missing():
    meta = {
        1: {"movement_role": "compound", "movement_pattern": "h_push", "muscle_slug": "chest"},
        2: {"movement_role": "compound", "movement_pattern": "h_push", "muscle_slug": "chest"},
        10: {"movement_role": "isolation", "movement_pattern": "h_push", "muscle_slug": "triceps"},
        11: {"movement_role": "isolation", "movement_pattern": "h_push", "muscle_slug": "triceps"},
        12: {"movement_role": "isolation", "movement_pattern": "h_push", "muscle_slug": "triceps"},
        13: {"movement_role": "isolation", "movement_pattern": "h_push", "muscle_slug": "triceps"},
    }
    days = [
        SimpleNamespace(
            split_role="upper",
            exercises=[
                SimpleNamespace(exercise_id=1, section="main", sets=3),
                SimpleNamespace(exercise_id=2, section="main", sets=3),
                SimpleNamespace(exercise_id=10, section="main", sets=3),
                SimpleNamespace(exercise_id=11, section="main", sets=3),
                SimpleNamespace(exercise_id=12, section="main", sets=3),
                SimpleNamespace(exercise_id=13, section="main", sets=3),
            ],
        )
    ]
    out, _note = apply_weekly_dose(
        days,
        meta_by_id=meta,
        effective_level=1,
        strength_tier="ok",
        focus_slugs=frozenset({"biceps", "triceps"}),
        session_minutes=75,
    )
    tri = sum(1 for ex in out[0].exercises if ex.exercise_id in {10, 11, 12, 13})
    assert tri < 4
    assert any(ex.exercise_id == 1 for ex in out[0].exercises)


def test_reps_range_helpers():
    assert reps_range_from_center(10, role="compound", goal=None) == "8-12"
    assert rpe_for(1, "compound") == 7


def test_estimate_targets_uses_weekly_loss_rate():
    from app.services.workout_generation.nutrition_targets import (
        desired_calorie_adjustment,
        estimate_targets,
        parse_kg_per_week,
    )

    assert desired_calorie_adjustment("lose_weight", {"kg_per_week": 0.5}) == -550
    assert desired_calorie_adjustment("lose_weight", {"kg_per_week": 1}) == -1100
    assert desired_calorie_adjustment("gain_weight", {"kg_per_week": 0.25}) == 275
    assert desired_calorie_adjustment("gain_weight", {"kg_per_week": 0.5}) == 550
    assert desired_calorie_adjustment("maintain", {"kg_per_week": 1}) == 0

    assert parse_kg_per_week({"kg_per_week": 1, "weight_kg": 60}, goal="lose_weight") == 0.6
    assert parse_kg_per_week({"kg_per_week": 0.2, "weight_kg": 100}, goal="lose_weight") == 0.5
    assert parse_kg_per_week({"kg_per_week": 1, "weight_kg": 100}, goal="lose_weight") == 1.0
    assert parse_kg_per_week({"kg_per_week": 1}, goal="lose_weight") == 1.0
    assert parse_kg_per_week({"weight_kg": 80}, goal="gain_weight") == 0.4
    assert parse_kg_per_week({"kg_per_week": 0.5, "weight_kg": 80}, goal="gain_weight") == 0.5
    assert parse_kg_per_week({"kg_per_week": 1, "weight_kg": 80}, goal="gain_weight") == 0.6
    assert parse_kg_per_week({"kg_per_week": 0.5, "weight_kg": 60}, goal="gain_weight") == 0.45
    assert parse_kg_per_week({"kg_per_week": 0.25}, goal="gain_weight") == 0.25

    base = {
        "gender": "male",
        "weight_kg": 80,
        "height_cm": 175,
        "age": 30,
        "activity": "moderate",
        "goal": "lose_weight",
    }
    slow = estimate_targets({**base, "kg_per_week": 0.5})
    fast = estimate_targets({**base, "kg_per_week": 1})
    assert slow is not None and fast is not None
    assert fast.target_calories < slow.target_calories
    assert slow.target_calories - fast.target_calories == 330  # 0,8 kg − 0,5 kg (1% cân 80 kg)
