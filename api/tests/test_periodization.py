"""Tests for tiered progressive overload in periodization."""

from app.services.periodization import (
    DEVELOPING,
    EXPERIENCED,
    NOVICE,
    expand_plan_days_for_weeks,
    resolve_overload_profile,
)


def _day_main(sets=3, reps=10, rest=90, warmup_sets=2):
    return {
        "day_number": 1,
        "title_vi": "Ngày 1",
        "main": [{"sets": sets, "reps": reps, "rest_seconds": rest}],
        "warmup": [{"sets": warmup_sets, "reps": 10, "rest_seconds": 60}],
    }


def _week_main(expanded, week: int, sessions_per_week: int = 1):
    idx = (week - 1) * sessions_per_week
    return expanded[idx]["main"][0]


def test_novice_level1_four_weeks():
    expanded = expand_plan_days_for_weeks([_day_main()], 4, is_dict=True, experience_level=1)
    assert len(expanded) == 4

    w1 = _week_main(expanded, 1)
    assert w1["sets"] == 3
    assert w1["reps"] == 10
    assert w1["rest_seconds"] == 90

    w3 = _week_main(expanded, 3)
    assert w3["sets"] == 3
    assert w3["reps"] == 10

    w4 = _week_main(expanded, 4)
    assert w4["sets"] == 3
    assert w4["reps"] == 10
    assert w4["rest_seconds"] == 90


def test_novice_level1_six_weeks_deloads_last():
    expanded = expand_plan_days_for_weeks([_day_main()], 6, is_dict=True, experience_level=1)
    assert len(expanded) == 6
    w5 = _week_main(expanded, 5)
    assert w5["sets"] == 3
    assert w5["rest_seconds"] == 90
    w6 = _week_main(expanded, 6)
    assert w6["sets"] == 2
    assert w6["reps"] == 10
    assert w6["rest_seconds"] == 90


def test_developing_level3_four_weeks():
    expanded = expand_plan_days_for_weeks([_day_main()], 4, is_dict=True, experience_level=3)

    w2 = _week_main(expanded, 2)
    assert w2["sets"] == 3
    assert w2["reps"] == 10

    w3 = _week_main(expanded, 3)
    assert w3["sets"] == 3
    assert w3["reps"] == 10

    w4 = _week_main(expanded, 4)
    assert w4["sets"] == 2
    assert w4["reps"] == 10
    assert w4["rest_seconds"] == 120


def test_experienced_level5_four_weeks():
    expanded = expand_plan_days_for_weeks([_day_main()], 4, is_dict=True, experience_level=5)

    w2 = _week_main(expanded, 2)
    assert w2["sets"] == 3
    assert w2["reps"] == 10

    w3 = _week_main(expanded, 3)
    assert w3["sets"] == 4
    assert w3["reps"] == 10
    assert w3["rest_seconds"] == 90

    w4 = _week_main(expanded, 4)
    assert w4["sets"] == 2
    assert w4["reps"] == 10
    assert w4["rest_seconds"] == 120


def test_warmup_unchanged_all_levels():
    for level in (1, 3, 5):
        expanded = expand_plan_days_for_weeks([_day_main()], 4, is_dict=True, experience_level=level)
        for week in range(1, 5):
            item = expanded[week - 1]["warmup"][0]
            assert item["sets"] == 2
            assert item["reps"] == 10
            assert item["rest_seconds"] == 60


def test_weak_tier_dampens_experienced_to_developing():
    assert resolve_overload_profile(5, strength_tier="weak") == DEVELOPING
    assert resolve_overload_profile(5) == EXPERIENCED

    exp = expand_plan_days_for_weeks([_day_main()], 4, is_dict=True, experience_level=5)
    weak = expand_plan_days_for_weeks(
        [_day_main()], 4, is_dict=True, experience_level=5, strength_tier="weak"
    )

    w3_exp = _week_main(exp, 3)
    w3_weak = _week_main(weak, 3)
    assert w3_exp["reps"] == 10
    assert w3_weak["reps"] == 10
    assert w3_weak["sets"] < w3_exp["sets"]


def test_timed_reps_not_bumped():
    day = {
        "day_number": 1,
        "main": [{"sets": 3, "reps": "30s", "rest_seconds": 90}],
    }
    expanded = expand_plan_days_for_weeks([day], 4, is_dict=True, experience_level=5)
    w3 = expanded[2]["main"][0]
    assert w3["reps"] == "30s"


def test_profile_resolution_tiers():
    assert resolve_overload_profile(1) == NOVICE
    assert resolve_overload_profile(2) == NOVICE
    assert resolve_overload_profile(3) == DEVELOPING
    assert resolve_overload_profile(4) == EXPERIENCED
    assert resolve_overload_profile(5) == EXPERIENCED


def test_novice_deload_clears_rpe_and_keeps_cardio_rest_zero():
    from app.services.periodization import DELOAD_NOTE_VI

    day = {
        "day_number": 1,
        "title_vi": "Ngày 1",
        "main": [
            {
                "sets": 3,
                "reps": "8-12",
                "rest_seconds": 120,
                "notes_vi": (
                    "RPE 7. 2–4 set khởi động tăng dần mức tạ trước khi vào working sets. "
                    "Khi làm được cận trên range với RPE mục tiêu, tăng tạ nhỏ (khoảng 2.5 kg) phiên sau."
                ),
            }
        ],
        "warmup": [{"sets": 2, "reps": 10, "rest_seconds": 60, "notes_vi": "RPE 6"}],
        "cardio": [{"sets": 1, "reps": "10-15 phút", "rest_seconds": 0, "notes_vi": "RPE 4–5"}],
    }
    expanded = expand_plan_days_for_weeks([day], 6, is_dict=True, experience_level=1)
    main = expanded[5]["main"][0]
    assert main["sets"] == 2
    assert main["rest_seconds"] == 150
    assert main["notes_vi"] == DELOAD_NOTE_VI
    assert "RPE 7" not in (main["notes_vi"] or "")
    assert expanded[5]["cardio"][0]["rest_seconds"] == 0
    assert "RPE 6" not in (expanded[5]["warmup"][0].get("notes_vi") or "")


def test_rep_range_stays_fixed():
    day = {
        "day_number": 1,
        "main": [{"sets": 3, "reps": "8-12", "rest_seconds": 90}],
    }
    expanded = expand_plan_days_for_weeks([day], 4, is_dict=True, experience_level=1)
    assert expanded[0]["main"][0]["reps"] == "8-12"
    assert expanded[2]["main"][0]["reps"] == "8-12"
    assert expanded[3]["main"][0]["reps"] == "8-12"


def test_curriculum_deload_weeks_4_8_14():
    t1 = [{"day_number": 1, "title_vi": "Push A", "main": [{"sets": 3, "reps": 10, "rest_seconds": 90}]}]
    t2 = [{"day_number": 1, "title_vi": "Push B", "main": [{"sets": 3, "reps": 10, "rest_seconds": 90}]}]
    t3 = [{"day_number": 1, "title_vi": "Push C", "main": [{"sets": 4, "reps": 10, "rest_seconds": 90}]}]
    expanded = expand_plan_days_for_weeks(
        t1,
        14,
        is_dict=True,
        experience_level=3,
        week_templates=[t1, t2, t3],
        curriculum=True,
    )
    assert len(expanded) == 14
    assert "Pha 1" in expanded[0]["title_vi"] and "Push A" in expanded[0]["title_vi"]
    assert "Pha 2" in expanded[4]["title_vi"] and "Push B" in expanded[4]["title_vi"]
    assert "Pha 3" in expanded[8]["title_vi"] and "Push C" in expanded[8]["title_vi"]
    assert "Pha 3" in expanded[13]["title_vi"] and "Push C" in expanded[13]["title_vi"]
    for w in (4, 8, 14):
        day = expanded[w - 1]
        assert "Deload" in day["title_vi"]
        assert day["main"][0]["sets"] == 2
    assert "Deload" not in expanded[1]["title_vi"]
    assert "Deload" not in expanded[5]["title_vi"]
    assert "Deload" not in expanded[10]["title_vi"]
    # Weeks 9–13 are phase 3, not deload
    for w in (9, 10, 11, 12, 13):
        assert "Pha 3" in expanded[w - 1]["title_vi"]
        assert "Deload" not in expanded[w - 1]["title_vi"]


def test_curriculum_week_a_b_odd_even_and_deload_uses_a():
    from app.services.periodization import expand_plan_days_for_weeks

    t1a = [{"day_number": 1, "title_vi": "A", "main": [{"sets": 3, "reps": 10, "rest_seconds": 90, "exercise_id": 10}]}]
    t1b = [{"day_number": 1, "title_vi": "B", "main": [{"sets": 3, "reps": 10, "rest_seconds": 90, "exercise_id": 11}]}]
    phase = {"a": t1a, "b": t1b}
    expanded = expand_plan_days_for_weeks(
        t1a,
        14,
        is_dict=True,
        experience_level=2,
        week_templates=[phase, phase, phase],
        curriculum=True,
    )
    assert "A" in expanded[0]["title_vi"]  # week 1 odd
    assert expanded[0]["main"][0]["exercise_id"] == 10
    assert "B" in expanded[1]["title_vi"]  # week 2 even
    assert expanded[1]["main"][0]["exercise_id"] == 11
    assert "A" in expanded[2]["title_vi"]  # week 3 odd
    assert "Deload" in expanded[3]["title_vi"]  # week 4
    assert expanded[3]["main"][0]["exercise_id"] == 10
    assert expanded[3]["main"][0]["sets"] == 2
    assert expanded[4]["main"][0]["exercise_id"] == 10  # phase 2 week 1 = A
    assert expanded[5]["main"][0]["exercise_id"] == 11  # phase 2 week 2 = B



def test_curriculum_ramp_resets_each_phase():
    """Developing set ramp resets at start of each challenge phase."""
    day = {"day_number": 1, "title_vi": "Legs", "main": [{"sets": 3, "reps": 10, "rest_seconds": 90}]}
    expanded = expand_plan_days_for_weeks(
        [day], 14, is_dict=True, experience_level=3, curriculum=True
    )
    w1 = expanded[0]["main"][0]["sets"]
    w5 = expanded[4]["main"][0]["sets"]  # phase 2 week 1
    w9 = expanded[8]["main"][0]["sets"]  # phase 3 week 1
    assert w1 == w5 == w9 == 3


def test_non_curriculum_eight_weeks_deloads_last_only():
    day = {"day_number": 1, "title_vi": "Push", "main": [{"sets": 3, "reps": 10, "rest_seconds": 90}]}
    expanded = expand_plan_days_for_weeks(
        [day], 8, is_dict=True, experience_level=3, curriculum=False
    )
    assert len(expanded) == 8
    for w in range(1, 8):
        assert "Deload" not in expanded[w - 1]["title_vi"]
    assert "Deload" in expanded[7]["title_vi"]
    assert expanded[7]["main"][0]["sets"] == 2
