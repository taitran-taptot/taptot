"""Overview knowledge matrix mirrored for 100-day prompts + engine flags."""

from app.services.periodization import expand_plan_days_for_weeks, periodization_advice_vi, NOVICE
from app.services.workout_generation.phase_knowledge import (
    flags_for_phase,
    refs_for_phase,
)
from app.services.workout_generation.wizard_inputs import _nutrition_insight_vi
from app.services.workout_generation.nutrition_targets import NutritionTargets


def _slugs(level, month, **opts):
    return [r["slug"] for r in refs_for_phase(level, month, **opts)]


def test_phase_slugs_match_frontend_matrix():
    # Missing activity is the walking job; missing goal is maintain.
    assert _slugs(1, 1) == [
        "cach-doc-lich-tap-quy-uoc-buoi-tap",
        "ky-thuat-tap-chuan-form-an-toan-co-xuong-khop",
        "tap-tai-nha-chon-va-su-dung-dung-cu-an-toan",
        "cach-tinh-tdee-theo-muc-van-dong-thuc-te",
    ]
    assert _slugs(1, 2) == [
        "mau-van-dong-va-cach-tang-giam-do-kho-bai-tap",
        "dau-moi-co-doms-va-chan-thuong-cach-phan-biet-va-xu-ly",
        "tu-dien-thuat-ngu-tap-luyen-cho-nguoi-moi",
        "uoc-luong-khau-phan-va-an-uong-thuc-te",
    ]
    assert _slugs(1, 3, goal="lose_weight")[1] == "tuan-xa-tai-nhe-deload-cho-nguoi-moi"
    assert _slugs(2, 2) == [
        "nguyen-tac-qua-tai-luy-tien-progressive-overload-co-ban",
        "rpe-va-rir-trong-tung-set",
        "dau-moi-co-doms-va-chan-thuong-cach-phan-biet-va-xu-ly",
        "uoc-luong-khau-phan-va-an-uong-thuc-te",
    ]
    assert refs_for_phase(3, 1)[1]["slug"] == "periodization-co-ban"
    assert "refeed-va-diet-break" in _slugs(3, 3, goal="lose_weight")
    assert refs_for_phase(2, 0) == []


def test_job_goal_matrix_keeps_twelve_unique_articles():
    sit_lose = [
        _slugs(1, month, goal="lose_weight", activity="sedentary") for month in (1, 2, 3)
    ]
    assert sit_lose[0][3] == "nang-luong-va-can-nang-tham-hut-thang-du-va-can-bang-calo"
    assert sit_lose[2] == [
        "nguyen-tac-qua-tai-luy-tien-progressive-overload-co-ban",
        "tuan-xa-tai-nhe-deload-cho-nguoi-moi",
        "theo-doi-tien-bo-va-nhat-ky-tap-luyen",
        "cardio-cho-suc-khoe-va-giam-mo",
    ]
    heavy_gain = [
        _slugs(1, month, goal="gain_weight", activity="very_active") for month in (1, 2, 3)
    ]
    assert heavy_gain[0][:3] == [
        "cach-doc-lich-tap-quy-uoc-buoi-tap",
        "theo-doi-dau-va-dau-hieu-can-kham",
        "hit-tho-bracing-va-kiem-soat-ap-luc-khi-tap",
    ]
    assert heavy_gain[0][3] == (
        "dinh-duong-da-luong-chat-dam-protein-tinh-bot-carb-va-chat-beo-fat"
    )
    walk_lose = [
        _slugs(2, month, goal="lose_weight", activity="moderate") for month in (1, 2, 3)
    ]
    assert walk_lose[2][3] == "cardio-cho-suc-khoe-va-giam-mo"
    assert "carb-cycling-co-ban" not in walk_lose[2]
    assert flags_for_phase(2, 3, goal="lose_weight", activity="moderate").want_carb_cycle
    heavy_cut = [
        _slugs(3, month, goal="lose_weight", activity="active") for month in (1, 2, 3)
    ]
    assert heavy_cut[2] == [
        "deload-dung-thoi-diem",
        "phuc-hoi-co-bap-giac-ngu-va-toi-uu-phat-trien",
        "nuoc-dien-giai-va-ruou-bia-khi-tap-luyen",
        "refeed-va-diet-break",
    ]
    maintain = [
        _slugs(1, month, goal="maintain", activity="sedentary") for month in (1, 2, 3)
    ]
    assert maintain[0][3] == "cach-tinh-tdee-theo-muc-van-dong-thuc-te"
    assert maintain[1][3] == "uoc-luong-khau-phan-va-an-uong-thuc-te"
    walk_gain = [
        _slugs(2, month, goal="gain_weight", activity="light") for month in (1, 2, 3)
    ]
    assert walk_gain[0][3] == "cach-tinh-tdee-theo-muc-van-dong-thuc-te"
    assert walk_gain[2][3] == (
        "dinh-duong-da-luong-chat-dam-protein-tinh-bot-carb-va-chat-beo-fat"
    )
    home = _slugs(1, 1, goal="lose_weight", activity="sedentary", location="home")
    assert home == _slugs(1, 1, goal="lose_weight", activity="sedentary")
    assert _slugs(2, 1, goal="gain_muscle", activity="very_active") == _slugs(
        2, 1, goal="gain_weight", activity="active"
    )

    for level in (1, 2, 3):
        for goal in ("lose_weight", "gain_weight", "maintain"):
            for activity in ("sedentary", "light", "moderate", "active", "very_active"):
                slugs = [
                    slug
                    for month in (1, 2, 3)
                    for slug in _slugs(level, month, goal=goal, activity=activity)
                ]
                assert len(slugs) == 12
                assert len(set(slugs)) == 12, (level, goal, activity, slugs)


def test_flags_l1_no_carb_cycle_l2_p3_yes():
    l1p1 = flags_for_phase(1, 1)
    l1p3 = flags_for_phase(1, 3)
    l2p3 = flags_for_phase(2, 3)
    l3p2 = flags_for_phase(3, 2)
    l3p3 = flags_for_phase(3, 3)
    assert not l1p1.want_carb_cycle
    assert l1p1.want_rep_ramp
    assert l1p3.want_rep_ramp
    assert l1p3.want_beginner_deload
    assert not l1p3.want_carb_cycle
    assert not l2p3.want_carb_cycle
    assert flags_for_phase(2, 3, goal="lose_weight").want_carb_cycle
    assert l2p3.want_set_ramp
    assert not l3p2.want_carb_cycle
    assert flags_for_phase(3, 2, goal="lose_weight").want_carb_cycle
    assert l3p2.want_intensity_tech
    assert not l3p3.want_refeed
    assert flags_for_phase(3, 3, goal="lose_weight").want_refeed
    assert not l3p3.want_carb_cycle


def test_l1_curriculum_ramps_integer_reps_each_non_deload_week():
    day = {
        "day_number": 1,
        "title_vi": "Ngày 1",
        "main": [{"sets": 3, "reps": "8-12", "rest_seconds": 90}],
        "warmup": [{"sets": 2, "reps": "30 giây", "rest_seconds": 30}],
    }
    expanded = expand_plan_days_for_weeks(
        [day], 14, is_dict=True, experience_level=1, curriculum=True, goal="gain_weight"
    )
    # Global non-deload weeks 1–3, 5–7, 9–13. Band 8–12.
    assert expanded[0]["main"][0]["reps"] == "8"  # week 1
    assert expanded[1]["main"][0]["reps"] == "9"  # week 2
    assert expanded[2]["main"][0]["reps"] == "10"  # week 3
    assert expanded[3]["main"][0]["reps"] == "8"  # week 4 deload — no +rep
    assert expanded[4]["main"][0]["reps"] == "11"  # week 5
    assert expanded[5]["main"][0]["reps"] == "12"  # week 6 cap
    assert expanded[12]["main"][0]["reps"] == "12"  # week 13 still capped
    assert expanded[13]["main"][0]["reps"] == "8"  # week 14 deload
    assert expanded[0]["warmup"][0]["reps"] == "30 giây"
    assert expanded[5]["warmup"][0]["reps"] == "30 giây"
    assert expanded[0]["main"][0]["sets"] == 3
    assert expanded[10]["main"][0]["sets"] == 3  # L1 no set ramp


def test_curriculum_single_integer_does_not_invent_plus_four_hi():
    day = {
        "day_number": 1,
        "title_vi": "Push",
        "main": [{"sets": 4, "reps": "14", "rest_seconds": 90}],
    }
    expanded = expand_plan_days_for_weeks(
        [day], 14, is_dict=True, experience_level=2, curriculum=True
    )
    assert expanded[0]["main"][0]["reps"] == "14"
    assert expanded[6]["main"][0]["reps"] == "14"  # week 7 — not 18
    assert expanded[7]["main"][0]["reps"] == "14"  # week 8 deload


def test_curriculum_4_5_range_caps_at_hi():
    day = {
        "day_number": 1,
        "title_vi": "Push",
        "main": [{"sets": 3, "reps": "4-5", "rest_seconds": 90}],
    }
    expanded = expand_plan_days_for_weeks(
        [day], 14, is_dict=True, experience_level=1, curriculum=True, goal="gain_weight"
    )
    assert expanded[0]["main"][0]["reps"] == "4"
    assert expanded[1]["main"][0]["reps"] == "5"
    assert expanded[6]["main"][0]["reps"] == "5"
    assert expanded[3]["main"][0]["reps"] == "4"


def test_l2_phase3_adds_a_compound_set_late_in_phase():
    day = {
        "day_number": 1,
        "title_vi": "Ngày 1",
        "main": [{"sets": 3, "reps": 10, "rest_seconds": 90}],
    }
    expanded = expand_plan_days_for_weeks(
        [day], 14, is_dict=True, experience_level=2, curriculum=True
    )
    assert expanded[8]["main"][0]["sets"] == 3  # week 9 local 1
    assert expanded[10]["main"][0]["sets"] == 4  # week 11 local 3


def test_periodization_advice_l1_does_not_claim_carb_cycling():
    text = periodization_advice_vi(NOVICE, 14, curriculum=True, experience_level=1)
    assert "không carb cycling" in text
    assert "carb cycling ngày tập" not in text
    text_l2 = periodization_advice_vi(NOVICE, 14, curriculum=True, experience_level=2)
    assert "không carb cycling" in text_l2
    text_l2_cut = periodization_advice_vi(
        NOVICE, 14, curriculum=True, experience_level=2, goal="lose_weight"
    )
    assert "carb cycling ngày tập/nghỉ" in text_l2_cut


def test_nutrition_insight_l1_says_stable_macros():
    nt = NutritionTargets(
        bmr=1500,
        tdee=2000,
        target_calories=1800,
        protein_g=120,
        carbs_g=180,
        fat_g=60,
        meals_per_day=3,
        kg_per_week=0.4,
        delta_kcal=-200,
        clamped=False,
        notes_vi=(),
    )
    text = _nutrition_insight_vi(nt, goal="lose_weight", experience_level=1)
    assert "không carb cycling" in text
    text_l2 = _nutrition_insight_vi(nt, goal="lose_weight", experience_level=2)
    assert "Carb cycling" in text_l2
    assert "không carb cycling" not in text_l2
