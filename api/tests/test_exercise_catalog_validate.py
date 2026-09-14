"""Tests for generator-facing exercise catalog field validation."""

import pytest

from app.core.exceptions import BadRequestError
from app.services.exercise_catalog_validate import validate_exercise_catalog_fields


def test_validate_clamps_and_labels():
    out = validate_exercise_catalog_fields(
        {
            "movement_pattern": "H_PUSH",
            "venue": "Gym",
            "movement_role": "compound",
            "difficulty": 2,
        }
    )
    assert out["movement_pattern"] == "h_push"
    assert out["venue"] == "gym"
    assert out["difficulty"] == 2
    assert out["difficulty_label"] == "Cơ bản"


def test_validate_rejects_bad_pattern():
    with pytest.raises(BadRequestError):
        validate_exercise_catalog_fields({"movement_pattern": "press"})


def test_validate_rejects_bad_venue_role_difficulty():
    with pytest.raises(BadRequestError):
        validate_exercise_catalog_fields({"venue": "park"})
    with pytest.raises(BadRequestError):
        validate_exercise_catalog_fields({"movement_role": "accessory"})
    with pytest.raises(BadRequestError):
        validate_exercise_catalog_fields({"difficulty": 5})
    with pytest.raises(BadRequestError):
        validate_exercise_catalog_fields({"difficulty": 0})
