"""API request validation for Thử thách 100 ngày."""

from app.api.v1.ai import WorkoutScheduleRequest
from app.services.workout_generation.session_policy import CHALLENGE_WEEKS, MAX_WEEKS


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


def test_non_challenge_clamps_above_max_weeks():
    req = WorkoutScheduleRequest(**_base(challenge_100_days=False, duration_weeks=10))
    assert req.challenge_100_days is False
    assert req.duration_weeks == MAX_WEEKS == 8


def test_non_challenge_keeps_valid_weeks():
    req = WorkoutScheduleRequest(**_base(challenge_100_days=False, duration_weeks=6))
    assert req.duration_weeks == 6


def test_free_home_forces_home_no_equip_8_weeks():
    req = WorkoutScheduleRequest(
        **_base(
            generation_mode="free_home",
            challenge_100_days=True,
            duration_weeks=14,
            location="gym",
            no_equipment=False,
            equipment_list=["dumbbell"],
            food_ids=[1, 2],
            ai_suggest_foods=True,
        )
    )
    assert req.generation_mode == "free_home"
    assert req.challenge_100_days is False
    assert req.curriculum_12_weeks is False
    assert req.duration_weeks == 8
    assert req.location == "home"
    assert req.no_equipment is True
    assert req.equipment_list == []
    assert req.food_ids == []
    assert req.ai_suggest_foods is False
    assert req.foundation_motive == "build_habit"


def test_free_home_keeps_valid_motive():
    req = WorkoutScheduleRequest(**_base(generation_mode="free_home", foundation_motive="daily_energy"))
    assert req.foundation_motive == "daily_energy"


def test_familiarization_keeps_food_ids_and_blocks_ai_suggest():
    req = WorkoutScheduleRequest(
        **_base(
            generation_mode="familiarization",
            familiarization_path="advanced_foundation",
            challenge_100_days=True,
            duration_weeks=14,
            location="gym",
            no_equipment=True,
            equipment_list=["dumbbell"],
            food_ids=[1, 2],
            ai_suggest_foods=True,
            sessions_per_week=6,
            session_minutes=90,
        )
    )
    assert req.generation_mode == "familiarization"
    assert req.familiarization_path == "advanced_foundation"
    assert req.challenge_100_days is False
    assert req.duration_weeks == 9
    assert req.sessions_per_week == 3
    assert req.session_minutes == 45
    assert req.location == "home"
    assert req.no_equipment is False
    assert req.equipment_list == ["pull-up-bar"]
    assert req.food_ids == [1, 2]
    assert req.ai_suggest_foods is False


def test_familiarization_defaults_unknown_path_to_basic():
    req = WorkoutScheduleRequest(
        **_base(generation_mode="familiarization", familiarization_path="unknown")
    )
    assert req.familiarization_path == "basic_foundation"


def test_first_push_pull_forces_fixed_60_day_schedule():
    req = WorkoutScheduleRequest(
        **_base(
            generation_mode="familiarization",
            familiarization_path="first_push_pull",
            duration_weeks=4,
            sessions_per_week=6,
            session_minutes=90,
            no_equipment=False,
            equipment_list=["dumbbell"],
        )
    )
    assert req.duration_weeks == 9
    assert req.sessions_per_week == 3
    assert req.session_minutes == 45
    assert req.location == "home"
    assert req.no_equipment is True
    assert req.equipment_list == []


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
