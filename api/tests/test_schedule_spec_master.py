"""Tests for Master schedule spec module."""

from app.services.schedule_spec_master import (
    expand_week_days,
    gym_session_spec,
    home_session_spec,
    resolve_master_frame,
    snap_session_minutes,
)


def test_female_gym_3_sessions_l1():
    frame = resolve_master_frame(
        experience_level=1,
        sessions_per_week=3,
        gender="female",
        location="gym",
        no_equipment=False,
    )
    assert frame.week_code == "LUL"
    assert [d.split_role for d in frame.days] == ["legs", "upper", "legs"]


def test_female_gym_3_sessions_all_levels_lul():
    for level in (1, 2, 3):
        frame = resolve_master_frame(
            experience_level=level,
            sessions_per_week=3,
            gender="female",
            location="gym",
            no_equipment=False,
        )
        assert frame.week_code == "LUL"
        assert [d.split_role for d in frame.days] == ["legs", "upper", "legs"]


def test_female_gym_4_lppl():
    frame = resolve_master_frame(
        experience_level=1,
        sessions_per_week=4,
        gender="female",
        location="gym",
        no_equipment=False,
    )
    assert frame.week_code == "LPPL"
    assert [d.split_role for d in frame.days] == ["legs", "push", "pull", "legs"]


def test_male_gym_3_ppl():
    frame = resolve_master_frame(
        experience_level=1,
        sessions_per_week=3,
        gender="male",
        location="gym",
        no_equipment=False,
    )
    assert frame.week_code == "PPL"
    assert [d.split_role for d in frame.days] == ["push", "pull", "legs"]


def test_male_home_no_equip_l2_3d_ulu():
    frame = resolve_master_frame(
        experience_level=2,
        sessions_per_week=3,
        gender="male",
        location="home",
        no_equipment=True,
    )
    assert frame.week_code == "ULU"
    assert [d.split_role for d in frame.days] == ["upper", "legs", "upper"]


def test_male_3d_loaded_venues_ppl():
    for location, no_equip in (("gym", False), ("home", False)):
        for level in (1, 2, 3):
            frame = resolve_master_frame(
                experience_level=level,
                sessions_per_week=3,
                gender="male",
                location=location,
                no_equipment=no_equip,
            )
            assert frame.week_code == "PPL", (location, no_equip, level)
            assert [d.split_role for d in frame.days] == ["push", "pull", "legs"]


def test_expand_lul_lulu_lppl():
    assert expand_week_days("LUL") == ["Lower", "Upper", "Lower"]
    assert expand_week_days("LULU") == ["Lower", "Upper", "Lower", "Upper"]
    assert expand_week_days("LPPL") == ["Lower", "Push", "Pull", "Legs"]
    assert expand_week_days("ULU") == ["Upper", "Lower", "Upper"]


def test_expand_pplul():
    assert expand_week_days("PPLUL") == ["Push", "Pull", "Legs", "Upper", "Lower"]


def test_expand_ululul():
    assert expand_week_days("ULULUL") == [
        "Upper",
        "Lower",
        "Upper",
        "Lower",
        "Upper",
        "Lower",
    ]


def test_l3_gym_3_ppl():
    frame = resolve_master_frame(
        experience_level=3,
        sessions_per_week=3,
        gender="male",
        location="gym",
        no_equipment=False,
    )
    assert frame.week_code == "PPL"
    assert [d.split_role for d in frame.days] == ["push", "pull", "legs"]


def test_l2_gym_4_ulul():
    frame = resolve_master_frame(
        experience_level=2,
        sessions_per_week=4,
        gender="male",
        location="gym",
        no_equipment=False,
    )
    assert frame.week_code == "ULUL"
    assert [d.split_role for d in frame.days] == ["upper", "legs", "upper", "legs"]


def test_l1_gym_4_ulul():
    frame = resolve_master_frame(
        experience_level=1,
        sessions_per_week=4,
        gender="male",
        location="gym",
        no_equipment=False,
    )
    assert frame.week_code == "ULUL"


def test_snap_minutes():
    assert snap_session_minutes(58) == 60
    assert snap_session_minutes(32) == 30
    assert snap_session_minutes(120) == 90


def test_gym_60_compound_isolate_counts():
    spec = gym_session_spec(60)
    assert spec["compounds"] == 2
    assert spec["isolates"] == 3


def test_home_60_resistance_conditioning():
    spec = home_session_spec(60)
    assert spec["resistanceCount"] == 4
    assert spec["conditioningCount"] == 1


def test_home_75_90_cooldown_aligned_and_conditioning_minutes():
    s75 = home_session_spec(75)
    s90 = home_session_spec(90)
    assert s75["cooldown"] == "10p"
    assert s90["cooldown"] == "10p"
    assert s75["main"] == "55p"
    assert s75["conditioningMinutes"] == 15
    assert s90["conditioningMinutes"] == 20
    assert s75["resistanceCount"] == 5
    assert s90["resistanceCount"] == 6


def test_home_no_equip_pull_upper_titles():
    from app.services.schedule_spec_master import home_bw_focus_label

    assert home_bw_focus_label("pull") == "Lưng · core (BW)"
    assert home_bw_focus_label("upper") == "Thân trên (BW)"
    frame = resolve_master_frame(
        experience_level=1,
        sessions_per_week=3,
        gender="male",
        location="home",
        no_equipment=True,
    )
    assert frame.week_code == "ULU"
    uppers = [d.label_vi for d in frame.days if d.split_role == "upper"]
    assert uppers
    assert all("Thân trên" in t and "BW" in t for t in uppers)
    loaded = resolve_master_frame(
        experience_level=1,
        sessions_per_week=3,
        gender="male",
        location="home",
        no_equipment=False,
    )
    assert loaded.week_code == "PPL"
    assert any("Pull" in d.label_vi for d in loaded.days)
    assert all("Lưng · core" not in d.label_vi for d in loaded.days)
