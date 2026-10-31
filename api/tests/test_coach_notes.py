"""Coach notes: load-selection cues for gym / band / bodyweight."""

from app.services.workout_generation.effort_mode import exercise_effort_mode
from app.services.workout_generation.coach_notes import (
    LOAD_CUE_BAND_VI,
    LOAD_CUE_BW_VI,
    LOAD_CUE_GYM_VI,
    align_rep_cues,
    hold_note_vi,
    load_kind_for_item,
    looks_band,
    looks_loaded,
    working_note_vi,
)


def test_loaded_working_note_asks_to_pick_weight_for_target_reps():
    note = working_note_vi("10–14", kind="loaded", include_progress=True, rpe=7)
    assert "Chọn mức tạ" in note
    assert "10–14" in note
    assert "còn dư khoảng 1–2 cái" in note
    assert LOAD_CUE_GYM_VI in note


def test_band_working_note_asks_to_pick_tension():
    note = working_note_vi("12–15", kind="band", include_progress=True)
    assert "Chọn độ căng dây" in note
    assert "12–15" in note
    assert LOAD_CUE_BAND_VI in note
    assert "tạ" not in note.lower() or "mức tạ" not in note


def test_bodyweight_working_note_has_no_barbell_language():
    note = working_note_vi("8–12", kind="bw", include_progress=True)
    assert "làm 8–12 cái rồi dừng" in note.lower() or "Làm 8–12 cái rồi dừng" in note
    assert "đừng làm đến lúc hết sức" in note
    assert LOAD_CUE_BW_VI in note
    assert "2.5 kg" not in note


def test_progress_only_when_requested():
    gym = working_note_vi("10", kind="loaded", include_progress=False)
    bw = working_note_vi("10", kind="bw", include_progress=False)
    band = working_note_vi("10", kind="band", include_progress=False)
    assert LOAD_CUE_GYM_VI not in gym
    assert LOAD_CUE_BW_VI not in bw
    assert LOAD_CUE_BAND_VI not in band
    assert "Chọn mức tạ" in gym
    assert "10 cái rồi dừng" in bw
    assert "Chọn độ căng dây" in band


def test_vietnamese_elbow_plank_is_hold():
    assert (
        exercise_effort_mode(
            {"name_vi": "Chống người chống khuỷu", "movement_role": "isolation"}
        )
        == "hold"
    )
    assert (
        exercise_effort_mode(
            {"name_vi": "Chống người nghiêng chống khuỷu", "movement_role": "isolation"}
        )
        == "hold"
    )


def test_hold_note():
    note = hold_note_vi("20 giây")
    assert note == "Giữ 20 giây, dừng trước khi lưng võng hoặc vai rũ."
    assert "tạ" not in note


def test_khong_ta_plus_english_name_is_not_loaded():
    twist = {
        "name_vi": "Xoay người không tạ",
        "name_en": "Bodyweight Russian Twist",
    }
    squat = {
        "name_vi": "Ngồi xổm không tạ",
        "name_en": "Bodyweight Squat",
    }
    press = {
        "name_vi": "Đẩy ngực tạ đơn",
        "name_en": "Dumbbell Bench Press",
    }
    assert looks_loaded(twist) is False
    assert load_kind_for_item(twist) == "bw"
    assert looks_loaded(squat) is False
    assert load_kind_for_item(squat) == "bw"
    assert looks_loaded(press) is True
    assert load_kind_for_item(press) == "loaded"


def test_no_equipment_never_looks_loaded():
    assert looks_loaded({"name_en": "Dumbbell bench"}, no_equipment=True) is False
    assert looks_loaded({"name_en": "Dumbbell bench"}, no_equipment=False) is True
    assert looks_loaded({"name_vi": "Chống đẩy"}, no_equipment=False) is False


def test_band_not_classified_as_loaded():
    item = {"name_vi": "Đẩy ngực với dây kháng lực", "name_en": "Band Chest Press"}
    assert looks_band(item) is True
    assert looks_loaded(item, no_equipment=False) is False
    assert load_kind_for_item(item, no_equipment=False) == "band"


def test_align_rep_cues_rewrites_effort_span_only():
    loaded = align_rep_cues(
        "Chọn mức tạ để làm đúng 2–6 cái mỗi hiệp (còn dư khoảng 1–2 cái).",
        "8-12",
    )
    assert loaded is not None
    assert "làm đúng 8–12 cái" in loaded
    assert "còn dư khoảng 1–2 cái" in loaded
    assert "2–6" not in loaded

    unilateral = align_rep_cues("Làm 18–22 cái mỗi chân, xong đổi chân còn lại.", "8-12")
    assert unilateral == "Làm 8–12 cái mỗi chân, xong đổi chân còn lại."

    bodyweight = align_rep_cues("Làm 10–14 cái rồi dừng, đừng làm đến lúc hết sức.", "8")
    assert bodyweight is not None
    assert bodyweight.startswith("Làm 8 cái rồi dừng")

    hold = align_rep_cues("Giữ 20 giây, dừng trước khi lưng võng.", "8-12")
    assert hold == "Giữ 20 giây, dừng trước khi lưng võng."


def test_legacy_loaded_kwarg_still_maps_to_weight_cue():
    note = working_note_vi("8–12", loaded=True, include_progress=False)
    assert "Chọn mức tạ" in note
