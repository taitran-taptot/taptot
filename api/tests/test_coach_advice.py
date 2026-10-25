"""Tests for local coach advice helpers."""

from app.services.workout_generation.coach_advice import (
    FALLBACK_ADVICE,
    build_schedule_summary,
    generate_coach_advice,
)


def test_build_schedule_summary():
    class Frame:
        code = "master_test"
        name_vi = "Test"
        week_code = "PPL"

    class Ex:
        exercise_id = 1
        sets = 3
        reps = "10"
        section = "main"

    class Day:
        day_number = 1
        title_vi = "Buổi 1"
        split_role = "push"
        exercises = [Ex()]

    summary = build_schedule_summary(Frame(), [Day()], session_minutes=60, location="gym")
    assert summary["week_code"] == "PPL"
    assert summary["days"][0]["split_role"] == "push"


def test_coach_advice_is_local_fallback():
    out = generate_coach_advice(
        {"goal": "lose_weight", "health_note": "Đau vai"},
        {"week_code": "PPL", "days": []},
    )
    assert out["advice_vi"] == list(FALLBACK_ADVICE)
    assert out["swaps"] == []
    assert "used_openai" not in out
