"""Case grid for the band and dumbbell load Excel. Does not generate plans."""

from __future__ import annotations

from scripts.export_kit_load_cases_xlsx import (
    FOCUS_VALUES,
    KITS,
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
    assert len(specs) == 480
    assert len({s["case_id"] for s in specs}) == 480
    assert {s["kit"] for s in specs} == set(KITS)
    assert {s["gender"] for s in specs} == {"male", "female"}
    assert {s["level"] for s in specs} == {1, 2, 3}
    assert {s["sessions"] for s in specs} == {2, 3, 4, 5, 6}
    assert {tuple(s["focus"]) for s in specs} == set(FOCUS_VALUES)
    assert all(s["goal"] == "maintain" and s["minutes"] == 60 for s in specs)


def test_payload_carries_kit_focus_and_challenge():
    band = next(s for s in iter_specs() if s["kit"] == "resistance-band" and s["focus"] == ["nguc"])
    band_payload = payload_for(band)
    assert band_payload["focus_areas"] == ["nguc"]
    assert band_payload["equipment_list"] == ["resistance-band"]
    assert band_payload["challenge_100_days"] is True
    assert band_payload["fitness_baseline"]["pushups_max"] == 15
    assert band_payload["fitness_baseline"]["test_kit"] == "band"
    assert "persist" not in band_payload
    assert fitness_test_inputs(band)["test_day"].endswith("15 cái")
    assert fitness_test_inputs(band)["test_day"].startswith("Dây ")

    db = next(s for s in iter_specs() if s["kit"] == "dumbbell" and s["focus"] == ["chan"])
    db_payload = payload_for(db)
    assert db_payload["focus_areas"] == ["chan"]
    assert db_payload["equipment_list"] == ["dumbbell"]
    assert db_payload["challenge_100_days"] is True
    assert db_payload["fitness_baseline"]["test_kit"] == "dumbbell"
    assert db_payload["fitness_baseline"]["db_press_reps"] == 15
    assert db_payload["fitness_baseline"]["goblet_reps"] == 15
    assert "kg" in fitness_test_inputs(db)["test_chan"]


def test_run_case_does_not_persist(monkeypatch):
    spec = next(s for s in iter_specs() if s["case_id"] == "band_M_L1_none_s2")
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
