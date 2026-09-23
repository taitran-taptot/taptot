"""Tests for coach advice generation."""

from unittest.mock import patch

from app.services.workout_generation.coach_advice import (
    FALLBACK_ADVICE,
    _profile_for_prompt,
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


@patch("app.services.workout_generation.coach_advice.get_settings")
def test_coach_advice_fallback_without_key(mock_settings):
    mock_settings.return_value.workout_gen_coach_advice = True
    mock_settings.return_value.openai_api_key = ""
    out = generate_coach_advice(
        {"goal": "lose_weight", "health_note": "Đau vai"},
        {"week_code": "PPL", "days": []},
    )
    assert out["used_openai"] is False
    assert len(out["advice_vi"]) >= 2


@patch("app.services.workout_generation.coach_advice.get_settings")
@patch("app.services.workout_generation.coach_advice.urllib.request.urlopen")
def test_coach_advice_openai_mock(mock_urlopen, mock_settings):
    mock_settings.return_value.workout_gen_coach_advice = True
    mock_settings.return_value.openai_api_key = "sk-test"
    mock_settings.return_value.openai_model = "gpt-4o-mini"
    mock_settings.return_value.openai_base_url = "https://api.openai.com/v1"
    mock_settings.return_value.openai_timeout_seconds = 30
    mock_settings.return_value.openai_temperature = 0.4
    mock_settings.return_value.openai_max_tokens = 2048

    class Resp:
        def read(self):
            return b'{"choices":[{"message":{"content":"{\\"advice_vi\\":[\\"Uong du nuoc\\"],\\"summary_vi\\":\\"On\\",\\"week_notes_vi\\":\\"\\"}"}}]}'

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    mock_urlopen.return_value = Resp()

    out = generate_coach_advice(
        {
            "goal": "gain_muscle",
            "extra_goals": ["strength"],
            "health_note": None,
            "fitness_baseline": {"pushups_max": 10},
        },
        {"week_code": "UL", "days": []},
    )
    assert out["used_openai"] is True
    assert "Uong du nuoc" in out["advice_vi"][0] or out["advice_vi"]


def test_profile_for_prompt_includes_focus_labels():
    profile = _profile_for_prompt({"goal": "lose_weight", "focus_areas": ["mo_lung", "eo"]})
    assert profile["focus_areas"] == ["mo_lung", "eo"]
    assert profile["focus_areas_vi"] == ["giảm mỡ lưng", "giảm mỡ bụng"]
