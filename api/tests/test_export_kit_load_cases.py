"""Case grid for the 100-day Excel. Does not generate the full grid."""

from __future__ import annotations

from scripts.export_kit_load_cases_xlsx import (
    BAND_CASE_HEADERS,
    BAR_EQUIPMENT,
    CORE_CASE_COUNT,
    FOCUS_COMBOS,
    FULL_CASE_COUNT,
    GOALS,
    KITS,
    MINUTES,
    TIERS,
    baseline_for,
    equipment_for,
    is_core,
    iter_band_specs,
    iter_boundary_specs,
    iter_core_specs,
    iter_specs,
    payload_for,
    run_case,
    fitness_test_inputs,
    with_suggestion,
)


def test_suggestion_sits_on_the_exercise_and_in_the_note():
    row = with_suggestion(
        {
            "ten": "Đẩy ngực với dây kháng lực",
            "load_note_vi": "Gợi ý: Dây vàng · 10 lbs",
            "notes_vi": "Chọn độ căng dây để làm đúng 8–12 cái.",
        }
    )
    assert row["goi_y"] == "Gợi ý: Dây vàng · 10 lbs"
    assert row["notes_vi"].startswith("Gợi ý: Dây vàng · 10 lbs. ")
    plain = with_suggestion({"ten": "Chống người", "notes_vi": "Giữ 20 giây."})
    assert plain["goi_y"] == ""
    assert plain["notes_vi"] == "Giữ 20 giây."


def test_iter_specs_is_full_grid():
    specs = iter_specs()
    assert len(specs) == FULL_CASE_COUNT == 138_240
    assert len({s["case_id"] for s in specs}) == 138_240
    assert {s["kit"] for s in specs} == set(KITS)
    assert {s["gender"] for s in specs} == {"male", "female"}
    assert {s["level"] for s in specs} == {1, 2, 3}
    assert {s["sessions"] for s in specs} == {2, 3, 4, 5, 6}
    assert {s["minutes"] for s in specs} == set(MINUTES) == {45, 60}
    assert {s["goal"] for s in specs} == set(GOALS)
    assert {s["tier"] for s in specs} == set(TIERS) == {"weak", "ok", "strong"}
    assert {tuple(s["focus"]) for s in specs} == set(FOCUS_COMBOS)
    assert len(FOCUS_COMBOS) == 64
    core = iter_core_specs()
    assert len(core) == CORE_CASE_COUNT == 1_440
    assert len({s["case_id"] for s in core}) == 1_440
    assert all(is_core(s) for s in core)
    assert {s["goal"] for s in core} == {"maintain"}
    assert {s["tier"] for s in core} == {"ok"}
    assert all(len(s["focus"]) <= 1 for s in core)


def test_tier_baselines_classify():
    from app.services.workout_generation.capacity import resolve_capacity

    for kit in KITS:
        for gender in ("male", "female"):
            weight = 68.0 if gender == "female" else 75.0
            for tier in TIERS:
                base = baseline_for(kit, gender, 2, tier)
                got = resolve_capacity(2, base, gender=gender, weight_kg=weight)
                assert got.strength_tier == tier, (kit, gender, tier, got.strength_tier)


def test_payload_carries_kit_focus_and_challenge():
    band = next(
        s
        for s in iter_specs()
        if s["kit"] == "resistance-band"
        and s["focus"] == ["nguc"]
        and s["tier"] == "ok"
        and s["goal"] == "maintain"
    )
    band_payload = payload_for(band)
    assert band_payload["focus_areas"] == ["nguc"]
    assert band_payload["equipment_list"] == ["resistance-band"]
    assert band_payload["challenge_100_days"] is True
    assert band_payload["fitness_baseline"]["pushups_max"] == 15
    assert band_payload["fitness_baseline"]["test_kit"] == "band"
    assert "persist" not in band_payload
    assert fitness_test_inputs(band)["test_day"].endswith("15 cái")
    assert fitness_test_inputs(band)["test_day"].startswith("Dây ")

    bar = next(
        s
        for s in iter_specs()
        if s["kit"] == "bar-and-rings" and s["tier"] == "ok" and s["goal"] == "maintain"
    )
    bar_payload = payload_for(bar)
    assert bar_payload["equipment_list"] == list(BAR_EQUIPMENT)
    assert equipment_for("bar-and-rings") == ["pull-up-bar", "gymnastic-rings"]
    assert bar_payload["fitness_baseline"]["test_kit"] == "bar_rings"
    assert "db_press_kg" not in bar_payload["fitness_baseline"]
    assert bar_payload["fitness_baseline"]["pushups_max"] > 0
    assert bar_payload["fitness_baseline"]["squats_max"] > 0
    tests = fitness_test_inputs(bar)
    assert tests["test_day"].startswith("Chống đẩy")
    assert tests["test_keo"].startswith("Kéo xà")
    assert "kg" not in tests["test_chan"]

    db = next(
        s
        for s in iter_specs()
        if s["kit"] == "dumbbell"
        and s["focus"] == ["chan"]
        and s["tier"] == "ok"
        and s["goal"] == "maintain"
    )
    db_payload = payload_for(db)
    assert db_payload["focus_areas"] == ["chan"]
    assert db_payload["equipment_list"] == ["dumbbell"]
    assert db_payload["challenge_100_days"] is True
    assert db_payload["fitness_baseline"]["test_kit"] == "dumbbell"
    assert db_payload["fitness_baseline"]["db_press_reps"] == 15
    assert db_payload["fitness_baseline"]["goblet_reps"] == 15
    assert "kg" in fitness_test_inputs(db)["test_chan"]


def test_run_case_does_not_persist(monkeypatch):
    spec = next(s for s in iter_specs() if s["case_id"] == "band_M_L1_none_s2_m60_keep_ok")
    seen: dict[str, object] = {}

    def fake_generate(db, user_id, payload, *, persist=True, commit=True):
        seen["persist"] = persist
        seen["commit"] = commit
        seen["user_id"] = user_id
        return {
            "days": [],
            "insights": {},
            "week_code": "UL",
            "sessions_actual": 2,
        }

    monkeypatch.setattr("scripts.export_kit_load_cases_xlsx.generate_workout", fake_generate)
    monkeypatch.setattr(
        "scripts.export_kit_load_cases_xlsx.expand_plan_days_for_weeks",
        lambda *args, **kwargs: [],
    )
    rec = run_case(None, spec, {})
    assert seen["persist"] is False
    assert seen["commit"] is False
    assert seen["user_id"] is None
    assert rec["error"] is None
    assert rec["case"]["week_code"] == "UL"
    assert rec["case"]["buoi_thuc"] == 2
    assert rec["exercises"] == []


def test_band_specs_are_the_resistance_grid():
    specs = iter_band_specs()
    assert len(specs) == 46_080
    assert len({s["case_id"] for s in specs}) == 46_080
    assert {s["kit"] for s in specs} == {"resistance-band"}
    assert all(s["case_id"].startswith("band_") for s in specs)


def test_boundary_specs_stay_outside_the_grid():
    from app.services.workout_generation.focus import normalize_focus_areas

    rows = iter_boundary_specs()
    assert len(rows) == 14
    assert len({s["case_id"] for s in rows}) == 14
    assert all(s["case_id"].startswith("bien_") for s in rows)
    focus4 = next(s for s in rows if s["case_id"] == "bien_focus_4")
    assert normalize_focus_areas(focus4["focus"]) == ["nguc", "lung", "mong"]
    assert {s["case_id"] for s in rows}.isdisjoint({s["case_id"] for s in iter_specs()})


def test_band_run_keeps_every_week_and_tdee(monkeypatch):
    spec = next(s for s in iter_band_specs() if s["case_id"] == "band_F_L2_none_s3_m60_keep_ok")
    seen: dict[str, object] = {}

    def fake_generate(db, user_id, payload, *, persist=True, commit=True):
        seen["persist"] = persist
        seen["commit"] = commit
        seen["user_id"] = user_id
        return {
            "days": [
                {
                    "day_number": 1,
                    "split_role": "full",
                    "exercises": [
                        {
                            "exercise_id": 1,
                            "section": "main",
                            "sets": 3,
                            "reps": "8-12",
                            "rest_seconds": 60,
                            "notes_vi": "Siết vai sau.",
                            "set_prescriptions": [{"load_note_vi": "Gợi ý: Dây đỏ · 20 lbs"}],
                        }
                    ],
                }
            ],
            "insights": {
                "nutrition": {
                    "tdee": 1800,
                    "target_calories": 1800,
                    "protein_g": 110,
                    "carbs_g": 180,
                    "fat_g": 55,
                }
            },
            "week_code": "FBW",
            "sessions_actual": 3,
        }

    monkeypatch.setattr("scripts.export_kit_load_cases_xlsx.generate_workout", fake_generate)
    monkeypatch.setattr(
        "scripts.export_kit_load_cases_xlsx.expand_plan_days_for_weeks",
        lambda seed, *args, **kwargs: seed,
    )
    rec = run_case(None, spec, {1: {"name_vi": "Bay vai sau với dây"}}, weeks=None)
    assert seen["persist"] is False
    assert seen["commit"] is False
    assert seen["user_id"] is None
    assert rec["error"] is None
    assert rec["case"]["tuoi"] == 28
    assert rec["case"]["chieu_cao_cm"] == 160.0
    assert rec["case"]["can_nang_kg"] == 68.0
    assert rec["case"]["tdee"] == 1800
    assert rec["case"]["kcal_muc_tieu"] == 1800
    assert set(BAND_CASE_HEADERS).issuperset(
        {"tuoi", "chieu_cao_cm", "can_nang_kg", "tdee", "protein_g"}
    )
    assert rec["exercises"][0]["tuan"] == 1
    assert rec["exercises"][0]["ten"] == "Bay vai sau với dây"
    assert rec["exercises"][0]["goi_y"] == "Gợi ý: Dây đỏ · 20 lbs"
    assert rec["exercises"][0]["sets"] == 3
    assert rec["exercises"][0]["reps"] == "8-12"
