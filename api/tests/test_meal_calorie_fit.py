"""Credibility of generated meal calories across the case grid."""

from scripts.export_meal_calorie_cases import (
    WEEKLY_KG,
    build_case_rows,
    build_plate_row,
    plate_sources,
)
from tests.test_meal_engine import _realistic_pool

from app.services.workout_generation.nutrition_targets import (
    KCAL_PER_KG,
    exercise_kcal_per_day,
)


def _match(rows, **want):
    found = [row for row in rows if all(row[key] == value for key, value in want.items())]
    assert found, want
    return found


def test_grid_covers_six_people_and_schedule_axes():
    rows = build_case_rows()
    assert len(rows) == 6 * 3 * 2 * 3 * 5 * 3
    assert {row["person_id"] for row in rows} == {
        "nu_moc",
        "nam_cung_so_do",
        "nu_60_tuoi",
        "nu_nhe",
        "nam_nhe",
        "nam_nang",
    }


def test_anchor_female_targets_about_1580_not_1800():
    rows = build_case_rows()
    row = _match(
        rows,
        person_id="nu_moc",
        activity="moderate",
        goal="lose_weight",
        level=2,
        sessions=4,
        minutes=45,
    )[0]
    bmr = 10 * 60 + 6.25 * 152 - 5 * 24 - 161
    tdee = int(bmr * 1.55) + exercise_kcal_per_day(60, 4, 45)
    expected = tdee - int(round(WEEKLY_KG * KCAL_PER_KG / 7))
    assert abs(row["clamped"] - expected) <= 15
    assert row["clamped"] != 1800
    assert row["floor"] < 1800 < row["tdee"]
    assert "1800" in row["compare_1800"]


def test_sessions_and_minutes_change_tdee_level_does_not():
    rows = build_case_rows()
    bmr = 10 * 60 + 6.25 * 152 - 5 * 24 - 161
    short = _match(
        rows,
        person_id="nu_moc",
        activity="moderate",
        goal="lose_weight",
        level=1,
        sessions=2,
        minutes=45,
    )[0]
    long = _match(
        rows,
        person_id="nu_moc",
        activity="moderate",
        goal="lose_weight",
        level=1,
        sessions=6,
        minutes=60,
    )[0]
    level3 = _match(
        rows,
        person_id="nu_moc",
        activity="moderate",
        goal="lose_weight",
        level=3,
        sessions=2,
        minutes=45,
    )[0]
    assert short["tdee"] == int(bmr * 1.55) + exercise_kcal_per_day(60, 2, 45)
    assert long["tdee"] == int(bmr * 1.55) + exercise_kcal_per_day(60, 6, 60)
    assert short["tdee"] != long["tdee"]
    assert level3["tdee"] == short["tdee"]


def test_light_people_hit_calorie_floor_when_sedentary_and_cutting():
    rows = build_case_rows()
    female = _match(
        rows,
        person_id="nu_nhe",
        activity="sedentary",
        goal="lose_weight",
        level=1,
        sessions=2,
        minutes=45,
    )[0]
    male = _match(
        rows,
        person_id="nam_nhe",
        activity="sedentary",
        goal="lose_weight",
        level=1,
        sessions=2,
        minutes=45,
    )[0]
    assert female["hit_floor"]
    assert female["clamped"] == female["floor"]
    assert male["hit_floor"]
    assert male["clamped"] == 1500


def test_six_plates_stay_within_10pct():
    rows = build_case_rows()
    pool = _realistic_pool()
    wanted = {
        ("nu_moc", "moderate", "lose_weight"),
        ("nu_moc", "moderate", "maintain"),
        ("nu_moc", "moderate", "gain_weight"),
        ("nu_nhe", "sedentary", "lose_weight"),
        ("nam_nang", "moderate", "lose_weight"),
        ("nu_moc", "sedentary", "lose_weight"),
    }
    sources = {
        (row["person_id"], row["activity"], row["goal"]): row for row in plate_sources(rows)
    }
    assert wanted <= set(sources)
    for key in wanted:
        plate = build_plate_row(sources[key], pool)
        assert plate["kcal_pct"] <= 10, plate


def test_extreme_weight_plates_stay_within_protein_and_calories():
    rows = build_case_rows()
    pool = _realistic_pool()
    light = _match(
        rows,
        person_id="nu_nhe",
        activity="sedentary",
        goal="lose_weight",
        level=2,
        sessions=4,
        minutes=45,
    )[0]
    heavy = _match(
        rows,
        person_id="nam_nang",
        activity="moderate",
        goal="lose_weight",
        level=2,
        sessions=4,
        minutes=45,
    )[0]
    for case in (light, heavy):
        plate = build_plate_row(case, pool)
        assert plate["kcal_pct"] <= 10, plate
        assert plate["prot_pct"] <= 5, plate


def test_heavy_labor_protein_above_1_8_stays_within_ceiling():
    rows = build_case_rows()
    pool = _realistic_pool()
    plate = build_plate_row(
        _match(
            rows,
            person_id="nam_nhe",
            activity="very_active",
            goal="maintain",
            level=2,
            sessions=6,
            minutes=60,
        )[0],
        pool,
    )
    assert plate["kcal_pct"] <= 10
    assert plate["protein_g_per_kg"] <= 2.3
    assert plate["plate_result"] == "khớp"


def test_gain_plate_short_on_protein_stays_off():
    rows = build_case_rows()
    pool = _realistic_pool()
    plate = build_plate_row(
        _match(
            rows,
            person_id="nu_moc",
            activity="sedentary",
            goal="gain_weight",
            level=2,
            sessions=6,
            minutes=45,
        )[0],
        pool,
    )
    assert plate["plate_protein"] < plate["protein_target"] * 0.88
    assert plate["plate_result"] == "lệch"


def test_heavy_sedentary_cut_note_states_pace_after_floor():
    rows = build_case_rows()
    row = _match(
        rows,
        person_id="nam_nang",
        activity="sedentary",
        goal="lose_weight",
        level=1,
        sessions=2,
        minutes=45,
    )[0]
    note = row["note"]
    realized = (row["tdee"] - row["clamped"]) * 7 / KCAL_PER_KG
    realized_text = f"{realized:.2f}".replace(".", ",")
    assert "kẹp còn" not in note
    assert "được nâng lên" in note
    assert "Sàn kéo calo ăn lên" in note
    assert realized_text in note
    assert realized < row["kg_week"] - 0.01
    assert not note.rstrip(".").endswith("0,50 kg/tuần")
