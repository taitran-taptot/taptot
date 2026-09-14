"""Coach notes: load-selection cues for gym / band / bodyweight."""

from app.services.workout_generation.coach_notes import (
    LOAD_CUE_BAND_VI,
    LOAD_CUE_BW_VI,
    LOAD_CUE_GYM_VI,
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


def test_hold_note():
    note = hold_note_vi("20 giây")
    assert note == "Giữ 20 giây, dừng trước khi lưng võng hoặc vai rũ."
    assert "tạ" not in note


def test_no_equipment_never_looks_loaded():
    assert looks_loaded({"name_en": "Dumbbell bench"}, no_equipment=True) is False
    assert looks_loaded({"name_en": "Dumbbell bench"}, no_equipment=False) is True
    assert looks_loaded({"name_vi": "Chống đẩy"}, no_equipment=False) is False


def test_band_not_classified_as_loaded():
    item = {"name_vi": "Ép ngực dây kháng lực", "name_en": "Band Chest Press"}
    assert looks_band(item) is True
    assert looks_loaded(item, no_equipment=False) is False
    assert load_kind_for_item(item, no_equipment=False) == "band"


def test_legacy_loaded_kwarg_still_maps_to_weight_cue():
    note = working_note_vi("8–12", loaded=True, include_progress=False)
    assert "Chọn mức tạ" in note
