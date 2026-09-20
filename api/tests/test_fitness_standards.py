from app.services.workout_generation.fitness_standards import (
    evaluate_fitness_baseline,
    familiarization_catalog,
    familiarization_overview_copy,
    normalize_familiarization_path,
)


def _male_basic(**overrides):
    data = {
        "pushup_variant": "standard",
        "pushups_max": 10,
        "pull_test_variant": "strict",
        "pullups_max": 4,
        "squats_max": 36,
        "plank_seconds": 76,
        "run_10min_meters": 1500,
    }
    data.update(overrides)
    return data


def test_male_strict_greater_than_boundaries():
    below = evaluate_fitness_baseline(
        "male", _male_basic(squats_max=19, plank_seconds=44)
    )
    assert below["level"] == "below_basic"
    assert {"squat", "plank"}.issubset(below["basic_not_met"])

    passed = evaluate_fitness_baseline("male", _male_basic())
    assert passed["level"] == "basic"
    assert passed["recommended_path"] == "advanced_foundation"


def test_male_basic_uses_range_floors():
    result = evaluate_fitness_baseline(
        "male",
        {
            "pushup_variant": "standard",
            "pushups_max": 8,
            "pull_test_variant": "strict",
            "pullups_max": 2,
            "squats_max": 20,
            "plank_seconds": 45,
            "run_10min_meters": 1100,
        },
    )
    assert result["level"] == "basic"


def test_female_basic_alternative_tests():
    result = evaluate_fitness_baseline(
        "female",
        {
            "pushup_variant": "incline_low",
            "pushups_max": 8,
            "pull_test_variant": "inverted_row",
            "inverted_rows_max": 5,
            "squats_max": 26,
            "plank_seconds": 51,
            "run_10min_meters": 1300,
        },
    )
    assert result["level"] == "basic"


def test_female_advanced_requires_low_row_or_strict_pull():
    common = {
        "pushup_variant": "standard",
        "pushups_max": 5,
        "squats_max": 36,
        "plank_seconds": 76,
        "run_10min_meters": 1500,
    }
    high_row = evaluate_fitness_baseline(
        "female",
        {**common, "pull_test_variant": "inverted_row", "inverted_rows_max": 10},
    )
    assert high_row["advanced"]["pull"] is False

    low_row = evaluate_fitness_baseline(
        "female",
        {**common, "pull_test_variant": "inverted_row_low", "inverted_rows_max": 6},
    )
    assert low_row["level"] == "advanced"

    hang = evaluate_fitness_baseline(
        "female",
        {**common, "pull_test_variant": "hang", "pull_hold_seconds": 45},
    )
    assert hang["advanced"]["pull"] is False


def test_zero_push_or_pull_recommends_first_rep_path():
    result = evaluate_fitness_baseline(
        "male", _male_basic(pushups_max=0, pullups_max=0)
    )
    assert result["recommended_path"] == "first_push_pull"


def test_catalog_and_path_normalization_are_stable():
    catalog = familiarization_catalog()
    assert catalog["duration_weeks"] == 9
    assert catalog["duration_days"] == 60
    assert [path["key"] for path in catalog["paths"]] == [
        "first_push_pull",
        "basic_foundation",
        "advanced_foundation",
    ]
    assert [path["label_vi"] for path in catalog["paths"]] == [
        "Nhập môn & gia cố khớp",
        "Xây sức mạnh nền",
        "Nền tảng nâng cao",
    ]
    first_path = catalog["paths"][0]
    assert first_path["duration_days"] == 60
    assert first_path["duration_weeks"] == 9
    assert catalog["paths"][1]["duration_days"] == 60
    assert catalog["paths"][1]["duration_weeks"] == 9
    assert catalog["paths"][2]["duration_days"] == 60
    assert catalog["paths"][2]["duration_weeks"] == 9
    assert catalog["exit_goals"]["male"][0]["display_vi"] == "3–8 lần sàn (hoặc kê ghế)"
    assert catalog["exit_goals"]["male"][1]["display_vi"] == "1–2 kéo xà hoặc 6–10 kéo người nằm (bàn/xà)"
    assert catalog["exit_goals"]["female"][0]["display_vi"] == "4–10 lần"
    assert catalog["exit_goals"]["female"][1]["display_vi"] == "20–45 giây"
    assert catalog["standards"]["male"]["basic"][0]["display_vi"] == "8–15 lần sàn"
    assert catalog["standards"]["female"]["basic"][0]["display_vi"] == (
        "1–6 lần sàn hoặc 6–12 kê bục 20 cm"
    )
    assert normalize_familiarization_path("advanced_foundation") == "advanced_foundation"
    assert normalize_familiarization_path("unknown") == "basic_foundation"


def test_overview_copy_has_mission_and_outcome():
    male = familiarization_overview_copy("first_push_pull", "male")
    female = familiarization_overview_copy("basic_foundation", "female")
    assert "nhập môn" in male["mission_vi"].lower()
    assert "3–8 chống đẩy" in male["outcome_vi"]
    assert male["nutrition_vi"].startswith("Đạm 1,6–2,0")
    assert "1–6 chống đẩy sàn" in female["outcome_vi"]
    assert "xây sức mạnh nền" in female["mission_vi"].lower()
    assert "mission_vi" in male and "outcome_vi" in male


def test_bmi_bands_match_asia_pacific_cutoffs():
    from app.services.workout_generation.bmi import bmi_band, compute_bmi, goal_from_bmi_band

    assert compute_bmi(90, 170) == 31.1
    assert bmi_band(18.4) == "underweight"
    assert bmi_band(22.9) == "normal"
    assert bmi_band(24.0) == "overweight"
    assert bmi_band(29.9) == "obese_1"
    assert bmi_band(31.1) == "obese_2"
    assert goal_from_bmi_band("underweight") == "gain_weight"
    assert goal_from_bmi_band("normal") == "maintain"
    assert goal_from_bmi_band("obese_1") == "lose_weight"


def test_weight_goal_obese_loses_about_five_kg_in_two_months():
    from app.services.workout_generation.bmi import build_familiarization_weight_goal

    card = build_familiarization_weight_goal(
        {
            "gender": "male",
            "age": 30,
            "height_cm": 170,
            "weight_kg": 90,
            "activity": "light",
        }
    )
    assert card is not None
    assert card["goal"] == "lose_weight"
    assert card["band"] == "obese_2"
    assert card["current_kg"] == 90
    assert 84.0 <= card["target_kg"] <= 87.0
    assert card["daily_kcal"] >= 1500
    assert "90 kg" in card["copy_vi"]
    assert "kcal/ngày" in card["copy_vi"]
    assert "2 tháng" in card["copy_vi"]


def test_weight_goal_underweight_gains_and_normal_maintains():
    from app.services.workout_generation.bmi import build_familiarization_weight_goal

    gain = build_familiarization_weight_goal(
        {
            "gender": "female",
            "age": 25,
            "height_cm": 160,
            "weight_kg": 42,
            "activity": "light",
        }
    )
    assert gain is not None
    assert gain["goal"] == "gain_weight"
    assert gain["target_kg"] > 42
    assert "tăng" in gain["copy_vi"]

    keep = build_familiarization_weight_goal(
        {
            "gender": "male",
            "age": 25,
            "height_cm": 170,
            "weight_kg": 65,
            "activity": "light",
        }
    )
    assert keep is not None
    assert keep["goal"] == "maintain"
    assert keep["target_kg"] == 65
    assert "duy trì" in keep["copy_vi"]
