"""Tests for default rest constants."""

from app.services.workout_rest import (
    REST_COMPOUND_L1_SEC,
    REST_COMPOUND_SEC,
    REST_CONDITIONING_SEC,
    REST_ISOLATION_SEC,
    REST_LADDER_SEC,
    REST_WARMUP_BETWEEN_SEC,
    default_rest_for_section,
    default_rest_seconds,
    rest_for_plan_exercise,
    snap_rest_seconds,
    timed_block_prescription,
)


def test_default_rest_seconds_by_role():
    assert default_rest_seconds("compound") == REST_COMPOUND_SEC == 180
    assert default_rest_seconds("resistance") == 180
    assert default_rest_seconds("isolation") == REST_ISOLATION_SEC == 90
    assert default_rest_seconds("conditioning") == REST_CONDITIONING_SEC == 90
    assert default_rest_seconds("cardio") == 0
    assert default_rest_seconds("mobility") == 60
    assert default_rest_seconds("compound", experience_level=1) == REST_COMPOUND_L1_SEC == 120
    assert default_rest_seconds("compound", experience_level=2) == 180


def test_default_rest_for_section():
    assert default_rest_for_section("cardio") == 0
    assert default_rest_for_section("warmup") == REST_WARMUP_BETWEEN_SEC == 30
    assert default_rest_for_section("main", movement_role="compound") == 180
    assert default_rest_for_section("main", movement_role="isolation") == 90


def test_rest_for_plan_exercise_warmup_and_cardio():
    assert rest_for_plan_exercise(
        block_key="general_warmup", plan_section="warmup", movement_role="mobility"
    ) == 30
    assert rest_for_plan_exercise(
        block_key="conditioning", plan_section="cardio", movement_role="conditioning"
    ) == 0
    sets, reps, rest, notes = timed_block_prescription(
        block_key="conditioning",
        plan_section="main",
        movement_role="conditioning",
        duration_min=8,
    )
    assert sets == 1
    assert reps == "8 phút"
    assert rest == 0
    assert notes
    assert "Mệt" in notes
    assert "nghỉ" in notes.lower() or "Nghỉ" in notes

    sets, reps, rest, notes = timed_block_prescription(
        block_key="general_warmup",
        plan_section="warmup",
        movement_role="mobility",
        duration_min=5,
    )
    assert (sets, reps, rest) == (2, "30 giây", 30)
    assert notes and "RPE" not in notes

    sets, reps, rest, _ = timed_block_prescription(
        block_key="cooldown",
        plan_section="cooldown",
        movement_role="mobility",
        duration_min=5,
    )
    assert (sets, reps, rest) == (2, "30 giây", 20)


def test_home_interval_cardio_splits_budget_into_short_bouts():
    from app.services.workout_rest import home_interval_cardio_prescription

    sets, reps, rest, notes = timed_block_prescription(
        block_key="conditioning",
        plan_section="cardio",
        movement_role="conditioning",
        duration_min=8,
        interval_cardio=True,
        experience_level=1,
    )
    assert reps == "30 giây"
    assert sets == 5
    assert rest in {60, 90, 120}
    wall = sets * 30 + max(0, sets - 1) * rest
    assert abs(wall - 8 * 60) <= 90
    assert notes and "liền mạch" in notes

    sets, reps, rest, _ = home_interval_cardio_prescription(13, experience_level=1)
    assert reps == "30 giây"
    assert sets >= 5
    assert rest in {60, 90, 120}
    wall = sets * 30 + max(0, sets - 1) * rest
    # Beginner stays at 30s work; wall may undershoot long budgets after rest cap.
    assert wall <= 13 * 60 + 30
    assert "phút" not in reps
    fat_sets, fat_reps, fat_rest, _ = home_interval_cardio_prescription(
        23, experience_level=1
    )
    assert fat_reps == "30 giây"
    assert fat_sets <= 8
    assert 60 <= fat_rest <= 120
    # L1/yếu: always 30s work, never 45–60.
    for mins in (5, 8, 10, 15, 20, 25):
        _, rlabel, r, _ = home_interval_cardio_prescription(mins, experience_level=1)
        assert rlabel == "30 giây"
        assert r >= 60
        assert r <= 120
    # Stronger athlete may use longer work bouts.
    _, mid_reps, mid_rest, _ = home_interval_cardio_prescription(10, experience_level=2)
    assert mid_reps in {"30 giây", "45 giây", "60 giây"}
    assert mid_rest in {60, 90, 120}

    gym_sets, gym_reps, gym_rest, _ = timed_block_prescription(
        block_key="conditioning",
        plan_section="cardio",
        movement_role="conditioning",
        duration_min=8,
        interval_cardio=False,
    )
    assert (gym_sets, gym_reps, gym_rest) == (1, "8 phút", 0)


def test_named_challenge_cardio_splits_interval_vs_leftover_minutes():
    hike_sets, hike_reps, hike_rest, _ = timed_block_prescription(
        block_key="conditioning",
        plan_section="cardio",
        movement_role="conditioning",
        duration_min=10,
        interval_cardio=True,
        name_en="Hiking",
        name_vi="Đi bộ đường dài",
    )
    assert (hike_sets, hike_reps, hike_rest) == (1, "10 phút", 0)

    jack_sets, jack_reps, _, _ = timed_block_prescription(
        block_key="conditioning",
        plan_section="cardio",
        movement_role="conditioning",
        duration_min=10,
        interval_cardio=True,
        experience_level=1,
        name_en="Jumping Jack",
        name_vi="Nhảy dang chân",
    )
    assert jack_sets > 1
    assert "giây" in jack_reps


def test_snap_rest_seconds_to_gym_clock():
    assert snap_rest_seconds(0) == 0
    assert snap_rest_seconds(25) == 30
    assert snap_rest_seconds(45) == 45
    assert snap_rest_seconds(85) == 90
    assert snap_rest_seconds(114) == 120
    assert snap_rest_seconds(138) == 150
    assert snap_rest_seconds(171) == 180
    assert snap_rest_seconds(200) == 180
    assert set(REST_LADDER_SEC) == {0, 30, 45, 60, 90, 120, 150, 180}
