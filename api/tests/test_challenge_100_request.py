"""API request validation for Thử thách 100 ngày."""

import pytest
from pydantic import ValidationError

from app.api.v1.ai import WorkoutScheduleRequest
from app.services.workout_generation.session_policy import CHALLENGE_WEEKS


def _base(**overrides):
    data = {
        "goal": "lose_weight",
        "gender": "male",
        "age": 25,
        "height_cm": 170,
        "weight_kg": 70,
        "activity": "moderate",
        "sessions_per_week": 3,
        "session_minutes": 45,
        "duration_weeks": 4,
        "challenge_100_days": True,
        "equipment_list": ["dumbbell"],
    }
    data.update(overrides)
    return data


def test_challenge_forces_14_weeks():
    req = WorkoutScheduleRequest(**_base(challenge_100_days=True, duration_weeks=4))
    assert req.challenge_100_days is True
    assert req.duration_weeks == CHALLENGE_WEEKS == 14
    assert req.curriculum_12_weeks is False


def test_curriculum_alias_maps_to_challenge():
    req = WorkoutScheduleRequest(**_base(curriculum_12_weeks=True, duration_weeks=8))
    assert req.challenge_100_days is True
    assert req.duration_weeks == 14
    assert req.curriculum_12_weeks is False


def test_regular_four_week_request_rejected():
    with pytest.raises(ValidationError) as ei:
        WorkoutScheduleRequest(**_base(challenge_100_days=False, duration_weeks=4))
    assert "Nhập môn" in str(ei.value) or "100 ngày" in str(ei.value)


def test_free_home_mode_is_rejected():
    with pytest.raises(ValidationError):
        WorkoutScheduleRequest(**_base(generation_mode="free_home"))


def test_gym_location_is_rejected():
    with pytest.raises(ValidationError):
        WorkoutScheduleRequest(**_base(location="gym"))


def test_no_equipment_is_rejected():
    with pytest.raises(ValidationError):
        WorkoutScheduleRequest(**_base(no_equipment=True, equipment_list=["dumbbell"]))


def test_unknown_equipment_slug_is_rejected():
    with pytest.raises(ValidationError):
        WorkoutScheduleRequest(**_base(equipment_list=["jump-rope"]))


def test_bar_rings_are_paired():
    req = WorkoutScheduleRequest(**_base(equipment_list=["pull-up-bar"]))
    assert set(req.equipment_list) >= {"pull-up-bar", "gymnastic-rings"}
    assert req.location == "home"
    assert req.no_equipment is False


def test_familiarization_keeps_food_ids_and_blocks_ai_suggest():
    req = WorkoutScheduleRequest(
        **_base(
            generation_mode="familiarization",
            familiarization_path="basic_foundation",
            challenge_100_days=True,
            duration_weeks=14,
            location="home",
            no_equipment=False,
            equipment_list=["dumbbell"],
            food_ids=[1, 2],
            ai_suggest_foods=True,
            sessions_per_week=6,
            session_minutes=60,
        )
    )
    assert req.generation_mode == "familiarization"
    assert req.familiarization_path == "first_push_pull"
    assert req.challenge_100_days is False
    assert req.duration_weeks == 9
    assert req.sessions_per_week == 3
    assert req.session_minutes == 45
    assert req.location == "home"
    assert req.no_equipment is False
    assert "dumbbell" in req.equipment_list
    assert req.food_ids == [1, 2]
    assert req.ai_suggest_foods is False


def test_familiarization_defaults_unknown_path_to_first_push_pull():
    req = WorkoutScheduleRequest(
        **_base(generation_mode="familiarization", familiarization_path="unknown")
    )
    assert req.familiarization_path == "first_push_pull"
    retired = WorkoutScheduleRequest(
        **_base(
            generation_mode="familiarization",
            familiarization_path="advanced_foundation",
        )
    )
    assert retired.familiarization_path == "first_push_pull"
    alias = WorkoutScheduleRequest(
        **_base(
            generation_mode="familiarization",
            familiarization_path="basic_foundation",
        )
    )
    assert alias.familiarization_path == "first_push_pull"


def test_retired_fitness_advanced_is_rejected():
    with pytest.raises(ValidationError):
        WorkoutScheduleRequest(**_base(generation_mode="fitness_advanced"))
    with pytest.raises(ValidationError):
        WorkoutScheduleRequest(**_base(generation_mode="fitness_soldier"))


def test_first_push_pull_forces_fixed_60_day_schedule():
    req = WorkoutScheduleRequest(
        **_base(
            generation_mode="familiarization",
            familiarization_path="first_push_pull",
            duration_weeks=4,
            sessions_per_week=6,
            session_minutes=60,
            no_equipment=False,
            equipment_list=["dumbbell"],
        )
    )
    assert req.duration_weeks == 9
    assert req.sessions_per_week == 3
    assert req.session_minutes == 45
    assert req.location == "home"
    assert req.no_equipment is False
    assert "dumbbell" in req.equipment_list


def test_familiarization_keeps_preferred_schedule():
    req = WorkoutScheduleRequest(
        **_base(
            generation_mode="familiarization",
            preferred_weekdays=[1, 3, 5, 99],
            preferred_start_time="19:00",
        )
    )
    assert req.preferred_weekdays == [1, 3, 5]
    assert req.preferred_start_time == "19:00"
