from types import SimpleNamespace

from pydantic import ValidationError
import pytest

from app.api.v1.ai import WorkoutScheduleRequest
from app.services.workout_generation.fitness_advanced_curriculum import (
    STANDARDS,
    WEEKS,
    build_fitness_advanced_week_templates,
    clamp_sessions,
    normalize_fitness_advanced_offer,
)


def _base(**overrides):
    data = {
        "goal": "maintain",
        "gender": "male",
        "age": 25,
        "height_cm": 170,
        "weight_kg": 70,
        "activity": "moderate",
        "sessions_per_week": 4,
        "session_minutes": 45,
        "duration_weeks": 4,
        "generation_mode": "fitness_advanced",
        "equipment_list": ["pull-up-bar"],
    }
    data.update(overrides)
    return data


def test_normalize_alias_and_clamp():
    assert normalize_fitness_advanced_offer("fitness_soldier") == "fitness_advanced"
    assert clamp_sessions(3) == 4
    assert clamp_sessions(7) == 6
    assert clamp_sessions("5") == 5


def test_request_forces_12_weeks_and_bar():
    req = WorkoutScheduleRequest(**_base(sessions_per_week=5, location="gym"))
    assert req.generation_mode == "fitness_advanced"
    assert req.duration_weeks == 12
    assert req.session_minutes == 55
    assert req.challenge_100_days is False
    assert "pull-up-bar" in req.equipment_list
    assert req.no_equipment is False


def test_soldier_alias_maps_to_advanced():
    req = WorkoutScheduleRequest(**_base(generation_mode="fitness_soldier"))
    assert req.generation_mode == "fitness_advanced"
    assert req.duration_weeks == 12


def test_rejects_sessions_outside_4_to_6():
    with pytest.raises(ValidationError):
        WorkoutScheduleRequest(**_base(sessions_per_week=3))
    with pytest.raises(ValidationError):
        WorkoutScheduleRequest(**_base(sessions_per_week=7))


def _catalog():
    def fake(i, name):
        return SimpleNamespace(id=i, name_vi=name, name_en=name)

    return {
        "push": fake(1, "Chống đẩy"),
        "incline_push": fake(2, "Incline push-up"),
        "pull": fake(3, "Pull-up"),
        "chin": fake(4, "Chin-up"),
        "row": fake(5, "Inverted row"),
        "squat": fake(6, "Bodyweight squat"),
        "plank": fake(7, "Plank"),
        "run_easy": fake(8, "Chạy bền"),
        "run_tempo": fake(9, "Tempo run"),
        "run_interval": fake(10, "Running interval"),
        "lunge": fake(11, "Lunge"),
    }


def test_week_templates_last_day_is_camera_test():
    templates = build_fitness_advanced_week_templates(
        None,  # type: ignore[arg-type]
        {"gender": "male", "sessions_per_week": 4},
        catalog=_catalog(),
    )
    assert len(templates) == WEEKS
    assert all(len(week) == 7 for week in templates)
    last = templates[-1][-1]
    assert last.split_role == "test"
    assert last.exercises == []
    week1_train = [d for d in templates[0] if d.exercises]
    assert len(week1_train) == 4
    week8_d = next(d for d in templates[7] if (d.split_role or "") == "d")
    assert any("10 phút" in (ex.reps or "") for ex in week8_d.exercises)


def test_female_dat_standards():
    assert STANDARDS["male"]["dat"]["plank"] == 150
    assert STANDARDS["female"]["dat"] == {
        "push": 10,
        "pull": 4,
        "squat": 40,
        "plank": 120,
        "run_m": 1700,
    }
