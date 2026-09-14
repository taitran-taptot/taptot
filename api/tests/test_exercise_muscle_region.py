"""Tests for granular muscle region classification."""

from app.services.exercise_muscle_region import classify_region_slug


def test_chest_incline_to_upper():
    r = classify_region_slug(name_vi="Đẩy ngực dốc lên", name_en="Incline Press", old_slug="chest")
    assert r.new_slug == "chest-upper"


def test_chest_flat_to_mid():
    r = classify_region_slug(name_vi="Bench press", old_slug="chest")
    assert r.new_slug == "chest-mid"


def test_chest_decline_to_lower():
    r = classify_region_slug(name_vi="Decline bench", old_slug="chest")
    assert r.new_slug == "chest-lower"


def test_pushup_feet_elevated_upper_even_if_en_decline():
    r = classify_region_slug(
        name_vi="Chống đẩy chân trên ghế",
        name_en="Decline Push Up",
        old_slug="chest",
    )
    assert r.new_slug == "chest-upper"


def test_pushup_hands_elevated_lower_even_if_en_incline():
    r = classify_region_slug(
        name_vi="Chống đẩy tay trên ghế",
        name_en="Incline Push Up",
        old_slug="chest",
    )
    assert r.new_slug == "chest-lower"


def test_back_pulldown_to_lats():
    r = classify_region_slug(name_vi="Kéo xô", old_slug="back")
    assert r.new_slug == "back-lats"


def test_back_row_to_middle():
    r = classify_region_slug(name_vi="Chèo tạ", old_slug="back")
    assert r.new_slug == "back-middle"


def test_lateral_raise_not_back_lats():
    r = classify_region_slug(name_vi="Dang tay máy", name_en="Lateral Raise Machine", old_slug="back")
    assert r.new_slug == "shoulders-lateral"


def test_shrug_to_traps():
    r = classify_region_slug(name_vi="Nhún vai tạ đòn sau lưng", old_slug="back")
    assert r.new_slug == "shoulders-traps"


def test_face_pull_not_back():
    r = classify_region_slug(name_vi="Kéo dây về mặt cáp", name_en="Cable Rope Face Pulls", old_slug="back-middle")
    assert r.new_slug == "shoulders-rear"


def test_shoulder_rear_face_pull():
    r = classify_region_slug(name_vi="Face pull", old_slug="shoulders")
    assert r.new_slug == "shoulders-rear"


def test_back_lower_hyperextension():
    r = classify_region_slug(name_vi="Duỗi lưng ghế 45 độ", old_slug="back-middle")
    assert r.new_slug == "back-lower"


def test_back_lower_superman():
    r = classify_region_slug(name_vi="Superman với Tạ Đơn", old_slug="core-upper", movement_pattern="core")
    assert r.new_slug == "back-lower"


def test_lunge_not_glutes():
    r = classify_region_slug(name_vi="Chùng chân bước đi", old_slug="glutes")
    assert r.new_slug == "quads"


def test_hamstring_curl_not_biceps():
    r = classify_region_slug(name_vi="Cuốn đùi sau nằm", old_slug="biceps")
    assert r.new_slug == "hamstrings"


def test_wrist_curl_forearms():
    r = classify_region_slug(name_vi="Cuốn cổ tay tạ đòn", old_slug="biceps")
    assert r.new_slug == "forearms"


def test_arnold_press_not_forearms():
    r = classify_region_slug(name_vi="Đẩy vai xoay cổ tay", name_en="Arnold Press", old_slug="forearms")
    assert r.new_slug == "shoulders-front"
    r2 = classify_region_slug(name_vi="Đẩy vai xoay cổ tay", name_en="Arnold Press", old_slug="biceps")
    assert r2.new_slug == "shoulders-front"


def test_tate_press_not_forearms():
    r = classify_region_slug(name_vi="Ép tay sau nằm xoay cổ tay", name_en="Tate Press", old_slug="forearms")
    assert r.new_slug == "triceps"


def test_rdl_hamstrings():
    r = classify_region_slug(name_vi="Nhấc tạ đòn gập hông", name_en="Barbell Romanian Deadlift", old_slug="back-lower")
    assert r.new_slug == "hamstrings"


def test_core_lower_knee_raise():
    r = classify_region_slug(name_vi="Nâng gối ghế treo", old_slug="core-upper", movement_pattern="core")
    assert r.new_slug == "core-lower"


def test_core_obliques():
    r = classify_region_slug(name_vi="Russian twist", old_slug="core")
    assert r.new_slug == "core-obliques"


def test_calf_raise():
    r = classify_region_slug(name_vi="Nhón bắp chân đứng máy", old_slug="quads")
    assert r.new_slug == "calves"


def test_glute_bridge():
    r = classify_region_slug(name_vi="Cầu mông", old_slug="glutes")
    assert r.new_slug == "glutes"


def test_external_rotation_shoulders():
    r = classify_region_slug(name_vi="Xoay ngoài vai với dây", old_slug="back-middle")
    assert r.new_slug == "shoulders-rear"
