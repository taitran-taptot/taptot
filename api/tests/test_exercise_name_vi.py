from app.services.exercise_name_vi import (
    leftover_english_tokens,
    preferred_name_vi,
    translate_exercise_name_en,
)


def test_translate_bodyweight_deadlift():
    out = translate_exercise_name_en("Bodyweight Deadlift")
    assert "Bodyweight" not in out
    assert leftover_english_tokens(out) == []
    assert "nhấc tạ" in out.lower() or "Nhấc tạ" in out


def test_keep_existing_vietnamese():
    assert (
        preferred_name_vi(
            name_en="Frog Pump",
            name_vi="Bơm mông tư thế ếch",
            copy_vi=None,
        )
        == "Bơm mông tư thế ếch"
    )


def test_face_pull_titles_are_rear_delt_moves():
    assert translate_exercise_name_en("Band High Face Pull") == "Kéo dây về mặt"
    assert translate_exercise_name_en("Cable Rope Face Pulls") == "Kéo dây về mặt cáp"
    assert translate_exercise_name_en("Cable Seated Rope Face Pull") == "Kéo dây về mặt ngồi"


def test_copy_wins():
    assert (
        preferred_name_vi(
            name_en="Jumping Jack",
            name_vi="Jumping Jack",
            copy_vi="Nhảy dang chân",
        )
        == "Nhảy dang chân"
    )


def test_rewrite_mixed_vietnamese_title():
    out = preferred_name_vi(
        name_en="Barbell Thruster",
        name_vi="Tạ đòn thruster",
        copy_vi=None,
    )
    assert leftover_english_tokens(out) == []
    assert "thruster" not in out.lower()


def test_assault_bike_and_swim_are_vietnamese():
    assert leftover_english_tokens(translate_exercise_name_en("Assault Bike")) == []
    assert leftover_english_tokens(translate_exercise_name_en("Backstroke Swim")) == []
    assert leftover_english_tokens(translate_exercise_name_en("Skin the Cat")) == []
    assert leftover_english_tokens(translate_exercise_name_en("Pendulum Squat / V-Squat")) == []
