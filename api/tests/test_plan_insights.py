"""Tests for AI plan insights builder."""

from app.services.plan_insights_service import build_plan_insights


def _base_params(**overrides):
    params = {
        "sessions_per_week": 5,
        "goal": "lose_weight",
        "experience_level": 2,
        "duration_weeks": 1,
        "nutrition": {
            "tdee": 2400,
            "target_calories": 2000,
            "goal_vi": "Giảm cân",
            "protein_g": 130,
        },
        "exercises_catalog": [
            {"exercise_id": "1", "name_vi": "Chống đẩy", "body_part": "chest"},
        ],
    }
    params.update(overrides)
    return params


def _base_output(**overrides):
    output = {
        "summary_vi": "Lịch Push/Pull/Legs phù hợp giảm cân.",
        "advice_vi": ["Uống đủ nước.", "Ngủ 7–8 tiếng."],
        "split_name_vi": "Push / Pull / Legs",
        "days": [
            {
                "day_index": 0,
                "label_vi": "Ngày 1 — Push",
                "split_role": "push",
                "warmup": [],
                "main": [
                    {
                        "exercise_id": "1",
                        "name_vi": "Chống đẩy",
                        "sets": 3,
                        "reps": 12,
                        "why_vi": "Bài cơ bản cho ngực, phù hợp người mới.",
                    }
                ],
                "cooldown": [],
                "section_notes": {"main": "Giữ form, không bỏ hơi."},
                "meal_notes": {"lunch": "Ăn sau tập 30–60 phút."},
            }
        ],
        "meals": [
            {
                "meal_type": "lunch",
                "food_id": 10,
                "name_vi": "Cơm gà",
                "calories": 450,
                "why_vi": "Đủ protein và carb sau buổi tập.",
            }
        ],
    }
    output.update(overrides)
    return output


def test_nutrition_insight_mentions_tdee_and_deficit():
    insights = build_plan_insights(_base_output(), _base_params())
    nut = insights["overview"]["nutrition_vi"] or ""
    assert "TDEE" in nut or "2400" in nut or "2.400" in nut
    assert "2000" in nut or "2.000" in nut
    assert "thiếu" in nut.lower() or "giảm" in nut.lower()


def test_schedule_insight_mentions_recovery():
    insights = build_plan_insights(_base_output(), _base_params(sessions_per_week=5))
    sched = insights["overview"]["schedule_vi"] or ""
    assert "5 buổi" in sched
    assert "phục hồi" in sched.lower()


def test_exercise_and_meal_why_from_ai():
    insights = build_plan_insights(_base_output(), _base_params())
    day = insights["days"][0]
    assert day["exercises"][0]["why_vi"] == "Bài cơ bản cho ngực, phù hợp người mới."
    assert day["meals"][0]["why_vi"] == "Đủ protein và carb sau buổi tập."


def test_exercise_why_fallback_without_ai_field():
    output = _base_output()
    output["days"][0]["main"][0].pop("why_vi")
    insights = build_plan_insights(output, _base_params())
    why = insights["days"][0]["exercises"][0]["why_vi"]
    assert "Chống đẩy" in why
    assert "push" in why.lower() or "Đẩy" in why
