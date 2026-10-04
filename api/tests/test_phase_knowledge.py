"""Overview knowledge matrix mirrored for 100-day prompts + engine flags."""

from app.services.periodization import expand_plan_days_for_weeks, periodization_advice_vi, NOVICE
from app.services.workout_generation.phase_knowledge import (
    flags_for_phase,
    refs_for_phase,
)
from app.services.workout_generation.wizard_inputs import _nutrition_insight_vi
from app.services.workout_generation.nutrition_targets import NutritionTargets


def test_phase_slugs_match_frontend_matrix():
    assert [r["slug"] for r in refs_for_phase(1, 1)] == [
        "cach-doc-lich-tap-quy-uoc-buoi-tap",
        "tu-dien-thuat-ngu-tap-luyen-cho-nguoi-moi",
        "xac-dinh-muc-tieu-tap-luyen",
        "mau-van-dong-va-cach-tang-giam-do-kho-bai-tap",
        "ky-thuat-tap-chuan-form-an-toan-co-xuong-khop",
        "khoi-dong-warm-up-van-dong-khop-mobility",
        "dau-moi-co-doms-va-chan-thuong-cach-phan-biet-va-xu-ly",
        "theo-doi-dau-va-dau-hieu-can-kham",
    ]
    assert [r["slug"] for r in refs_for_phase(1, 2)] == [
        "nang-luong-va-can-nang-tham-hut-thang-du-va-can-bang-calo",
        "cach-tinh-tdee-theo-muc-van-dong-thuc-te",
        "dinh-duong-da-luong-chat-dam-protein-tinh-bot-carb-va-chat-beo-fat",
        "phuc-hoi-co-bap-giac-ngu-va-toi-uu-phat-trien",
        "nuoc-dien-giai-va-ruou-bia-khi-tap-luyen",
        "ban-do-cac-nhom-co-chinh-co-che-chuyen-dong",
        "cardio-cho-suc-khoe-va-giam-mo",
    ]
    slugs_l1_p3 = [r["slug"] for r in refs_for_phase(1, 3)]
    assert slugs_l1_p3[0] == "ba-nut-chinh-khoi-luong-volume-do-nang-intensity-tan-suat-frequency"
    assert "tuan-xa-tai-nhe-deload-cho-nguoi-moi" in slugs_l1_p3
    assert [r["slug"] for r in refs_for_phase(2, 2)] == [
        "nguyen-tac-qua-tai-luy-tien-progressive-overload-co-ban",
        "rpe-va-rir-trong-tung-set",
        "deload-dung-thoi-diem",
    ]
    assert refs_for_phase(3, 1)[0]["slug"] == "periodization-co-ban"
    assert "refeed-va-diet-break" in [r["slug"] for r in refs_for_phase(3, 3)]
    assert refs_for_phase(2, 0) == []


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
    assert l2p3.want_carb_cycle
    assert l2p3.want_set_ramp
    assert l3p2.want_carb_cycle
    assert l3p2.want_intensity_tech
    assert l3p3.want_refeed
    assert not l3p3.want_carb_cycle


def test_l1_curriculum_ramps_integer_reps_each_non_deload_week():
    day = {
        "day_number": 1,
        "title_vi": "Ngày 1",
        "main": [{"sets": 3, "reps": "8-12", "rest_seconds": 90}],
        "warmup": [{"sets": 2, "reps": "30 giây", "rest_seconds": 30}],
    }
    expanded = expand_plan_days_for_weeks(
        [day], 14, is_dict=True, experience_level=1, curriculum=True
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
        [day], 14, is_dict=True, experience_level=1, curriculum=True
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
    assert "carb cycling ngày tập/nghỉ" in text_l2


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
