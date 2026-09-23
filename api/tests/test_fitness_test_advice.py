from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.workout_generation.fitness_test_advice import (
    build_fitness_test_advice,
    package_level_for_offer,
)


def test_offer_maps_to_parent_standard_level():
    assert package_level_for_offer("challenge_100") == "advanced"
    assert package_level_for_offer("pushup_30") == "advanced"
    assert package_level_for_offer("") == "advanced"


@patch("app.services.workout_generation.fitness_test_advice.get_settings")
def test_stretch_skip_fails_overall(mock_settings):
    mock_settings.return_value.openai_api_key = ""
    out = build_fitness_test_advice(
        gender="male",
        offer="challenge_100",
        fitness_baseline={
            "pushup_variant": "standard",
            "pushups_max": 20,
            "pull_test_variant": "strict",
            "pullups_max": 10,
            "squats_max": 50,
            "plank_seconds": 100,
            "run_10min_meters": 1900,
        },
        stretch_completed=False,
    )
    assert out["stretch_failed"] is True
    assert out["overall_failed"] is True
    assert out["package_pass"] is True
    assert out["used_openai"] is False
    assert out["advice_vi"][0].startswith("Bạn bỏ giãn cơ")
    assert "run" not in out["checks"]
    assert all(row.get("key") != "run" for row in out["standards"])


@patch("app.services.workout_generation.fitness_test_advice.get_settings")
def test_challenge_100_advice_ignores_run(mock_settings):
    mock_settings.return_value.openai_api_key = ""
    out = build_fitness_test_advice(
        gender="male",
        offer="challenge_100",
        fitness_baseline={
            "pushup_variant": "standard",
            "pushups_max": 20,
            "pull_test_variant": "strict",
            "pullups_max": 10,
            "squats_max": 50,
            "plank_seconds": 100,
        },
        stretch_completed=True,
    )
    assert "run" not in out["checks"]
    assert "run" not in out["not_met"]
    assert all(row.get("key") != "run" for row in out["standards"])
    assert out["package_pass"] is True
    assert out["overall_failed"] is False


@patch("app.services.workout_generation.fitness_test_advice.get_settings")
def test_unknown_offer_uses_advanced_checks(mock_settings):
    mock_settings.return_value.openai_api_key = ""
    out = build_fitness_test_advice(
        gender="male",
        offer="pushup_30",
        fitness_baseline={
            "pushup_variant": "standard",
            "pushups_max": 10,
            "pull_test_variant": "strict",
            "pullups_max": 4,
            "squats_max": 36,
            "plank_seconds": 76,
            "run_10min_meters": 1500,
        },
        stretch_completed=True,
    )
    assert out["package_level"] == "advanced"
    assert out["package_pass"] is False
    assert out["overall_failed"] is True


def test_advice_endpoint_public():
    client = TestClient(create_app())
    with patch(
        "app.api.v1.ai.build_fitness_test_advice",
        return_value={
            "overall_failed": False,
            "stretch_failed": False,
            "package_level": "advanced",
            "package_pass": True,
            "checks": {"push": True},
            "not_met": [],
            "standards": [],
            "advice_vi": ["ok"],
            "used_openai": False,
        },
    ):
        res = client.post(
            "/api/v1/ai/fitness-test/advice",
            json={
                "gender": "female",
                "offer": "challenge_100",
                "stretch_completed": True,
                "fitness_baseline": {"pushups_max": 3, "plank_seconds": 40},
            },
        )
    assert res.status_code == 200
    assert res.json()["advice_vi"] == ["ok"]
