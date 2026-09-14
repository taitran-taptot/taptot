"""Tests for session duration estimation and fill."""

from app.schemas.plans import PlanDayIn, PlanExerciseIn
from app.services.workout_rest import (
    interval_cardio_piece_count,
    interval_cardio_prescription,
)
from app.services.workout_generation.session_duration import (
    HOME_CARDIO_SURPLUS_CAP_MINUTES,
    _FILL_BLOCK_ORDER,
    _home_cardio_budget_minutes,
    _rescale_interval_cardios_on_day,
    absorb_home_cardio_surplus_into_main_sets,
    clamp_session_to_target,
    estimate_day_minutes,
    estimate_exercise_minutes,
    estimate_transition_minutes,
    interval_cardio_wall_minutes,
    top_up_session_minutes,
)


def test_estimate_exercise_minutes_compound_3p_rest():
    assert estimate_exercise_minutes(
        PlanExerciseIn(exercise_id=1, sets=3, reps="12", rest_seconds=180, section="main")
    ) == 9.0


def test_estimate_exercise_minutes_isolation_90s_rest():
    assert estimate_exercise_minutes(
        PlanExerciseIn(exercise_id=1, sets=3, reps="12", rest_seconds=90, section="main")
    ) == 6.0


def test_estimate_exercise_minutes_cardio_minutes():
    assert estimate_exercise_minutes(
        PlanExerciseIn(exercise_id=1, sets=1, reps="10 phút", rest_seconds=0, section="cardio")
    ) == 10.0


def test_estimate_timed_hold_uses_seconds_not_one_minute_per_set():
    assert estimate_exercise_minutes(
        PlanExerciseIn(
            exercise_id=1,
            sets=3,
            reps="30 giây",
            rest_seconds=45,
            section="main",
        )
    ) == 3.0


def test_top_up_bumps_sets_to_reach_target():
    day = PlanDayIn(
        day_number=1,
        exercises=[
            PlanExerciseIn(
                exercise_id=1,
                sets=3,
                reps="10",
                rest_seconds=180,
                section="main",
            ),
            PlanExerciseIn(
                exercise_id=2,
                sets=3,
                reps="12",
                rest_seconds=90,
                section="main",
            ),
        ],
    )
    meta = {
        1: {"movement_role": "compound", "muscle_slug": "nguc", "difficulty": 2},
        2: {"movement_role": "isolation", "muscle_slug": "tay", "difficulty": 2},
    }
    before = estimate_day_minutes(day)
    topped = top_up_session_minutes([day], session_minutes=22, meta_by_id=meta)[0]
    after = estimate_day_minutes(topped)
    assert after > before
    iso = next(e for e in topped.exercises if e.exercise_id == 2)
    assert iso.sets > 3


def test_warmup_and_cardio_duration_count_toward_total():
    day = PlanDayIn(
        day_number=1,
        exercises=[
            PlanExerciseIn(exercise_id=1, sets=1, reps="5 phút", rest_seconds=0, section="warmup"),
            PlanExerciseIn(exercise_id=2, sets=3, reps="8", rest_seconds=180, section="main"),
            PlanExerciseIn(exercise_id=3, sets=1, reps="10 phút", rest_seconds=0, section="cardio"),
            PlanExerciseIn(exercise_id=4, sets=1, reps="5 phút", rest_seconds=0, section="cooldown"),
        ],
    )
    total = estimate_day_minutes(day)
    assert total >= 25


def test_fill_block_order_lifts_before_conditioning():
    assert _FILL_BLOCK_ORDER.index("accessory") < _FILL_BLOCK_ORDER.index("conditioning")
    assert _FILL_BLOCK_ORDER.index("resistance") < _FILL_BLOCK_ORDER.index("conditioning")
    assert _FILL_BLOCK_ORDER.index("compound") < _FILL_BLOCK_ORDER.index("conditioning")


def test_top_up_bumps_isolation_before_extending_cardio():
    day = PlanDayIn(
        day_number=1,
        split_role="upper",
        exercises=[
            PlanExerciseIn(
                exercise_id=1,
                sets=3,
                reps="10",
                rest_seconds=180,
                section="main",
            ),
            PlanExerciseIn(
                exercise_id=2,
                sets=3,
                reps="12",
                rest_seconds=90,
                section="main",
            ),
            PlanExerciseIn(
                exercise_id=3,
                sets=1,
                reps="8 phút",
                rest_seconds=0,
                section="cardio",
            ),
        ],
    )
    meta = {
        1: {"movement_role": "compound", "muscle_slug": "chest", "difficulty": 2},
        2: {"movement_role": "isolation", "muscle_slug": "shoulders", "difficulty": 2},
        3: {"movement_role": "cardio", "muscle_slug": "core", "difficulty": 1},
    }
    topped = top_up_session_minutes([day], session_minutes=45, meta_by_id=meta)[0]
    iso = next(e for e in topped.exercises if e.exercise_id == 2)
    cardio = next(e for e in topped.exercises if e.exercise_id == 3)
    compound = next(e for e in topped.exercises if e.exercise_id == 1)
    assert iso.sets > 3
    assert compound.sets == 3
    assert "8 phút" in str(cardio.reps) or iso.sets >= 4


def test_estimate_rounds_primer_like_frontend():
    primer = PlanExerciseIn(
        exercise_id=1, sets=2, reps="8", rest_seconds=45, section="warmup"
    )
    # 2×1′ + 0.75′ rest = 2.75 → 3
    assert estimate_exercise_minutes(primer) == 3.0


def test_estimate_adds_one_minute_between_different_exercises():
    primer = PlanExerciseIn(
        exercise_id=10, sets=2, reps="8", rest_seconds=45, section="warmup"
    )
    main = PlanExerciseIn(
        exercise_id=10, sets=3, reps="10", rest_seconds=120, section="main"
    )
    other = PlanExerciseIn(
        exercise_id=11, sets=3, reps="12", rest_seconds=90, section="main"
    )
    # Primer → same station: no walk. Then 1′ to the next machine.
    assert estimate_transition_minutes([primer, main, other]) == 1.0
    day = PlanDayIn(day_number=1, exercises=[primer, main, other])
    # 2.75 + 7 + 6 + 1 trans → 16.75 → 17
    assert estimate_day_minutes(day) == 17.0


def test_estimate_no_trailing_transition_after_last_exercise():
    a = PlanExerciseIn(exercise_id=1, sets=3, reps="10", rest_seconds=90, section="main")
    b = PlanExerciseIn(exercise_id=2, sets=3, reps="10", rest_seconds=90, section="main")
    assert estimate_transition_minutes([a, b]) == 1.0
    assert estimate_transition_minutes([a]) == 0.0


def test_estimate_skips_transition_onto_cooldown():
    main = PlanExerciseIn(
        exercise_id=1, sets=3, reps="10", rest_seconds=90, section="main"
    )
    cardio = PlanExerciseIn(
        exercise_id=2, sets=1, reps="10 phút", rest_seconds=0, section="cardio"
    )
    stretch = PlanExerciseIn(
        exercise_id=3, sets=1, reps="2 phút", rest_seconds=0, section="cooldown"
    )
    assert estimate_transition_minutes([main, cardio, stretch]) == 1.0


def test_estimate_day_rounds_once_not_each_isolation():
    a = PlanExerciseIn(
        exercise_id=1, sets=2, reps="12", rest_seconds=90, section="main"
    )
    b = PlanExerciseIn(
        exercise_id=2, sets=2, reps="12", rest_seconds=90, section="main"
    )
    # 3.5 + 3.5 + 1 trans = 8, not per-row 4+4+1 = 9
    assert estimate_day_minutes(PlanDayIn(day_number=1, exercises=[a, b])) == 8.0


def test_estimate_lower_day_does_not_inflate_two_set_isolations():
    """Gym lower: 2-set 90s isolations must not round 3.5→4 three times + stretch walk."""
    day = PlanDayIn(
        day_number=1,
        split_role="legs",
        exercises=[
            PlanExerciseIn(
                exercise_id=1, sets=1, reps="5 phút", rest_seconds=30, section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=2, sets=2, reps="8", rest_seconds=45, section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=2, sets=3, reps="8-12", rest_seconds=120, section="main"
            ),
            PlanExerciseIn(
                exercise_id=3, sets=3, reps="8-12", rest_seconds=120, section="main"
            ),
            PlanExerciseIn(
                exercise_id=4, sets=2, reps="12-20", rest_seconds=90, section="main"
            ),
            PlanExerciseIn(
                exercise_id=5, sets=1, reps="10 phút", rest_seconds=0, section="cardio"
            ),
            PlanExerciseIn(
                exercise_id=6, sets=1, reps="2 phút", rest_seconds=30, section="cooldown"
            ),
            PlanExerciseIn(
                exercise_id=7, sets=2, reps="12-20", rest_seconds=90, section="main"
            ),
            PlanExerciseIn(
                exercise_id=8, sets=2, reps="12-20", rest_seconds=90, section="main"
            ),
        ],
    )
    # Raw 44.25 + 6 station changes (no stretch walk) → 50
    assert estimate_day_minutes(day) == 50.0
    from app.services.workout_generation.session_duration import clamp_session_to_target

    day = PlanDayIn(
        day_number=1,
        split_role="push",
        exercises=[
            PlanExerciseIn(
                exercise_id=1, sets=1, reps="5 phút", rest_seconds=30, section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=2, sets=3, reps="10", rest_seconds=180, section="main"
            ),
            PlanExerciseIn(
                exercise_id=3, sets=3, reps="10", rest_seconds=180, section="main"
            ),
            PlanExerciseIn(
                exercise_id=4, sets=3, reps="12", rest_seconds=90, section="main"
            ),
            PlanExerciseIn(
                exercise_id=5, sets=3, reps="12", rest_seconds=90, section="main"
            ),
            PlanExerciseIn(
                exercise_id=6, sets=3, reps="12", rest_seconds=90, section="main"
            ),
            PlanExerciseIn(
                exercise_id=7, sets=1, reps="15 phút", rest_seconds=0, section="cardio"
            ),
            PlanExerciseIn(
                exercise_id=8, sets=1, reps="5 phút", rest_seconds=30, section="cooldown"
            ),
        ],
    )
    meta = {
        2: {"movement_role": "compound", "muscle_slug": "chest"},
        3: {"movement_role": "compound", "muscle_slug": "shoulders"},
        4: {"movement_role": "isolation", "muscle_slug": "chest"},
        5: {"movement_role": "isolation", "muscle_slug": "shoulders"},
        6: {"movement_role": "isolation", "muscle_slug": "triceps"},
        7: {"movement_role": "cardio", "muscle_slug": "core"},
    }
    before = estimate_day_minutes(day)
    assert before > 60
    out = clamp_session_to_target(
        [day], session_minutes=60, meta_by_id=meta, location="gym"
    )[0]
    used = estimate_day_minutes(out)
    assert used <= 60
    mains = [e for e in out.exercises if (e.section or "main") == "main"]
    assert len(mains) == 5


def test_clamp_keeps_two_set_primer_and_hits_target():
    from app.services.workout_generation.assemble import inject_main_primer_warmup

    day = PlanDayIn(
        day_number=1,
        split_role="push",
        exercises=[
            PlanExerciseIn(
                exercise_id=1, sets=1, reps="5 phút", rest_seconds=30, section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=2, sets=3, reps="10", rest_seconds=180, section="main"
            ),
            PlanExerciseIn(
                exercise_id=3, sets=3, reps="10", rest_seconds=180, section="main"
            ),
            PlanExerciseIn(
                exercise_id=4, sets=4, reps="12", rest_seconds=90, section="main"
            ),
            PlanExerciseIn(
                exercise_id=5, sets=4, reps="12", rest_seconds=90, section="main"
            ),
            PlanExerciseIn(
                exercise_id=6, sets=1, reps="12 phút", rest_seconds=0, section="cardio"
            ),
            PlanExerciseIn(
                exercise_id=7, sets=1, reps="5 phút", rest_seconds=30, section="cooldown"
            ),
        ],
    )
    inject_main_primer_warmup(day)
    primer = [e for e in day.exercises if e.section == "warmup"][-1]
    assert primer.exercise_id == 2
    assert primer.sets == 2
    meta = {
        2: {"movement_role": "compound", "muscle_slug": "chest"},
        3: {"movement_role": "compound", "muscle_slug": "shoulders"},
        4: {"movement_role": "isolation", "muscle_slug": "chest"},
        5: {"movement_role": "isolation", "muscle_slug": "triceps"},
        6: {"movement_role": "cardio", "muscle_slug": "core"},
    }
    out = clamp_session_to_target(
        [day], session_minutes=45, meta_by_id=meta, location="gym"
    )[0]
    wu = [e for e in out.exercises if e.section == "warmup"]
    assert len(wu) == 2
    assert wu[1].sets == 2
    assert wu[1].reps == "4"
    assert estimate_day_minutes(out) <= 45


def test_top_up_does_not_exceed_target():
    day = PlanDayIn(
        day_number=1,
        split_role="push",
        exercises=[
            PlanExerciseIn(
                exercise_id=1, sets=3, reps="10", rest_seconds=180, section="main"
            ),
            PlanExerciseIn(
                exercise_id=2, sets=3, reps="12", rest_seconds=90, section="main"
            ),
            PlanExerciseIn(
                exercise_id=3, sets=1, reps="23 phút", rest_seconds=0, section="cardio"
            ),
        ],
    )
    meta = {
        1: {"movement_role": "compound", "muscle_slug": "chest"},
        2: {"movement_role": "isolation", "muscle_slug": "shoulders"},
        3: {"movement_role": "cardio", "muscle_slug": "core"},
    }
    topped = top_up_session_minutes([day], session_minutes=40, meta_by_id=meta)[0]
    assert estimate_day_minutes(topped) <= 40


def test_top_up_long_core_extends_cardio_without_adding_hard_sets():
    day = PlanDayIn(
        day_number=1,
        split_role="core",
        exercises=[
            PlanExerciseIn(
                exercise_id=1, sets=1, reps="5 phút", rest_seconds=30, section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=2, sets=2, reps="4", rest_seconds=45, section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=2, sets=4, reps="12", rest_seconds=90, section="main"
            ),
            PlanExerciseIn(
                exercise_id=3, sets=4, reps="12", rest_seconds=90, section="main"
            ),
            PlanExerciseIn(
                exercise_id=4, sets=1, reps="30 phút", rest_seconds=0, section="cardio"
            ),
            PlanExerciseIn(
                exercise_id=5, sets=1, reps="4 phút", rest_seconds=30, section="cooldown"
            ),
        ],
    )
    meta = {
        2: {"movement_role": "isolation", "muscle_slug": "core-upper"},
        3: {"movement_role": "isolation", "muscle_slug": "core-obliques"},
        4: {"movement_role": "cardio", "muscle_slug": "cardio"},
    }
    hard_sets = sum(e.sets for e in day.exercises if e.section == "main")
    topped = top_up_session_minutes(
        [day], session_minutes=75, meta_by_id=meta, experience_level=1
    )[0]
    assert estimate_day_minutes(topped) >= 75 * 0.90
    assert estimate_day_minutes(topped) <= 75
    assert sum(e.sets for e in topped.exercises if e.section == "main") == hard_sets
    assert len([e for e in topped.exercises if e.section == "cardio"]) == 1


def test_interval_cardio_prescription_ten_minutes():
    sets, reps, rest, notes = interval_cardio_prescription(10, experience_level=1)
    assert sets == 5
    assert reps == "30 giây"
    assert rest in {60, 90, 120}
    wall = (sets * 30 + (sets - 1) * rest) / 60.0
    assert abs(wall - 10) <= 1.5
    assert "liền mạch" in notes.lower() or "giây" in notes.lower()


def test_beginner_home_interval_never_uses_long_work_bouts():
    for mins in (12, 15, 20, 25):
        sets, reps, rest, _ = interval_cardio_prescription(mins, experience_level=1)
        assert reps == "30 giây"
        assert 60 <= rest <= 120
        assert sets <= 8
    # Level 2 may lengthen work when budget needs it.
    _, reps2, rest2, _ = interval_cardio_prescription(15, experience_level=2)
    assert reps2 in {"30 giây", "45 giây", "60 giây"}
    assert 60 <= rest2 <= 120


def test_interval_cardio_piece_count_threshold():
    assert interval_cardio_piece_count(10) == 1
    assert interval_cardio_piece_count(8) == 1
    assert interval_cardio_piece_count(10.1) == 2
    assert interval_cardio_piece_count(25) == 2
    assert interval_cardio_piece_count(0) == 0


def test_rescale_budget_ten_keeps_one_interval_piece():
    day = PlanDayIn(
        day_number=1,
        split_role="upper",
        exercises=[
            PlanExerciseIn(
                exercise_id=1, sets=2, reps="30 giây", rest_seconds=30, section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=2, sets=3, reps="10", rest_seconds=90, section="main"
            ),
            PlanExerciseIn(
                exercise_id=3, sets=3, reps="10", rest_seconds=90, section="main"
            ),
            PlanExerciseIn(
                exercise_id=4, sets=5, reps="45 giây", rest_seconds=60, section="cardio"
            ),
            PlanExerciseIn(
                exercise_id=5, sets=5, reps="45 giây", rest_seconds=60, section="cardio"
            ),
        ],
    )
    # Non-cardio ≈ warmup+mains ≈ ~1+~9 = ~10; target 20 → budget ≈10 → 1 piece.
    _rescale_interval_cardios_on_day(day, 20)
    cardios = [e for e in day.exercises if e.section == "cardio"]
    assert len(cardios) == 1
    assert "giây" in str(cardios[0].reps).lower()
    assert "phút" not in str(cardios[0].reps).lower()
    assert cardios[0].sets == 5


def test_rescale_budget_over_ten_keeps_two_interval_pieces():
    day = PlanDayIn(
        day_number=1,
        split_role="upper",
        exercises=[
            PlanExerciseIn(
                exercise_id=1, sets=1, reps="30 giây", rest_seconds=20, section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=2, sets=2, reps="10", rest_seconds=60, section="main"
            ),
            PlanExerciseIn(
                exercise_id=3, sets=5, reps="45 giây", rest_seconds=60, section="cardio"
            ),
            PlanExerciseIn(
                exercise_id=4, sets=5, reps="45 giây", rest_seconds=60, section="cardio"
            ),
        ],
    )
    _rescale_interval_cardios_on_day(day, 60)
    cardios = [e for e in day.exercises if e.section == "cardio"]
    assert len(cardios) == 2
    for c in cardios:
        assert "giây" in str(c.reps).lower()
        assert c.sets <= 8
        wall = interval_cardio_wall_minutes(c)
        assert wall is not None and wall >= 8
        assert c.sets == 5 or c.rest_seconds >= 60


def test_core_day_rescale_leaves_continuous_cardio():
    day = PlanDayIn(
        day_number=1,
        split_role="core",
        exercises=[
            PlanExerciseIn(
                exercise_id=1, sets=2, reps="12", rest_seconds=60, section="main"
            ),
            PlanExerciseIn(
                exercise_id=2, sets=1, reps="20 phút", rest_seconds=0, section="cardio"
            ),
        ],
    )
    _rescale_interval_cardios_on_day(day, 45)
    cardios = [e for e in day.exercises if e.section == "cardio"]
    assert len(cardios) == 1
    assert "20 phút" in str(cardios[0].reps)


def test_top_up_and_clamp_interval_cardio_uses_sets_not_minutes():
    day = PlanDayIn(
        day_number=1,
        split_role="push",
        exercises=[
            PlanExerciseIn(
                exercise_id=1, sets=1, reps="30 giây", rest_seconds=30, section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=2, sets=2, reps="10", rest_seconds=45, section="main"
            ),
            PlanExerciseIn(
                exercise_id=3, sets=4, reps="30 giây", rest_seconds=45, section="cardio"
            ),
        ],
    )
    meta = {
        2: {"movement_role": "resistance", "muscle_slug": "chest"},
        3: {"movement_role": "conditioning", "muscle_slug": "cardio"},
    }
    topped = top_up_session_minutes(
        [day], session_minutes=30, meta_by_id=meta, experience_level=1
    )[0]
    cardio = next(e for e in topped.exercises if e.section == "cardio")
    assert "phút" not in str(cardio.reps).lower()
    assert "giây" in str(cardio.reps).lower()
    assert cardio.sets >= 5
    assert cardio.sets <= 8
    assert estimate_day_minutes(topped) <= 30

    fat = PlanDayIn(
        day_number=1,
        split_role="push",
        exercises=[
            PlanExerciseIn(
                exercise_id=1, sets=2, reps="30 giây", rest_seconds=30, section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=2, sets=3, reps="10", rest_seconds=90, section="main"
            ),
            PlanExerciseIn(
                exercise_id=3, sets=3, reps="10", rest_seconds=90, section="main"
            ),
            PlanExerciseIn(
                exercise_id=4, sets=16, reps="30 giây", rest_seconds=45, section="cardio"
            ),
        ],
    )
    fat_meta = {
        2: {"movement_role": "resistance", "muscle_slug": "chest"},
        3: {"movement_role": "resistance", "muscle_slug": "back"},
        4: {"movement_role": "conditioning", "muscle_slug": "cardio"},
    }
    out = clamp_session_to_target(
        [fat], session_minutes=30, meta_by_id=fat_meta, location="home"
    )[0]
    clamped_cardio = next(e for e in out.exercises if e.section == "cardio")
    assert clamped_cardio.sets <= 8
    assert "giây" in str(clamped_cardio.reps).lower()
    assert estimate_day_minutes(out) <= 30


def test_absorb_then_interval_does_not_explode_sets():
    """Surplus absorb + interval Rx: cardio stays ~5 sets, not ~20 bouts."""
    day = PlanDayIn(
        day_number=1,
        split_role="upper",
        exercises=[
            PlanExerciseIn(
                exercise_id=1, sets=1, reps="30 giây", rest_seconds=30, section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=2, sets=2, reps="10", rest_seconds=60, section="main"
            ),
            PlanExerciseIn(
                exercise_id=3, sets=2, reps="10", rest_seconds=60, section="main"
            ),
            PlanExerciseIn(
                exercise_id=4, sets=1, reps="25 phút", rest_seconds=0, section="cardio"
            ),
            PlanExerciseIn(
                exercise_id=5, sets=5, reps="45 giây", rest_seconds=60, section="cardio"
            ),
        ],
    )
    meta = {
        2: {"movement_role": "resistance", "muscle_slug": "chest"},
        3: {"movement_role": "resistance", "muscle_slug": "back"},
        4: {"movement_role": "conditioning", "muscle_slug": "cardio"},
        5: {"movement_role": "conditioning", "muscle_slug": "cardio"},
    }
    absorb_home_cardio_surplus_into_main_sets(
        day, session_minutes=60, meta_by_id=meta
    )
    # Drop continuous leftover; rescale existing interval pieces to budget.
    day.exercises = [
        ex
        for ex in day.exercises
        if not (
            (ex.section or "") == "cardio" and "phút" in str(ex.reps or "").lower()
        )
    ]
    _rescale_interval_cardios_on_day(day, 60)
    cardios = [e for e in day.exercises if e.section == "cardio"]
    assert 1 <= len(cardios) <= 2
    assert all(int(c.sets or 0) <= 8 for c in cardios)
    assert all("giây" in str(c.reps).lower() for c in cardios)


def test_absorb_home_cardio_surplus_bumps_main_sets():
    day = PlanDayIn(
        day_number=1,
        split_role="upper",
        exercises=[
            PlanExerciseIn(
                exercise_id=1, sets=1, reps="30 giây", rest_seconds=30, section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=2, sets=2, reps="10", rest_seconds=60, section="main"
            ),
            PlanExerciseIn(
                exercise_id=3, sets=2, reps="10", rest_seconds=60, section="main"
            ),
            PlanExerciseIn(
                exercise_id=4, sets=1, reps="25 phút", rest_seconds=0, section="cardio"
            ),
        ],
    )
    meta = {
        2: {"movement_role": "resistance", "muscle_slug": "chest"},
        3: {"movement_role": "resistance", "muscle_slug": "back"},
        4: {"movement_role": "conditioning", "muscle_slug": "cardio"},
    }
    before = sum(e.sets for e in day.exercises if e.section == "main")
    assert _home_cardio_budget_minutes(day, 60) > HOME_CARDIO_SURPLUS_CAP_MINUTES
    absorb_home_cardio_surplus_into_main_sets(
        day, session_minutes=60, meta_by_id=meta
    )
    after = sum(e.sets for e in day.exercises if e.section == "main")
    assert after > before
    # Thin 2-lift days hit set caps before leftover drops fully under 15p.
    assert all(
        int(e.sets or 0) >= 5 for e in day.exercises if (e.section or "") == "main"
    )
