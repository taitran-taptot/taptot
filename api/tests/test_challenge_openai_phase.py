"""Production 100-day challenge uses OpenAI phase picks, not deterministic swaps."""

import inspect

from app.services.workout_generation.openai_picker import pick_challenge_phase_with_openai
from app.services.workout_generation.phase_templates import apply_phase_rpe
from app.services.workout_generation.service import generate_workout


def test_generate_workout_uses_openai_challenge_phases():
    src = inspect.getsource(generate_workout)
    assert "pick_challenge_phase_with_openai" in src
    assert "build_mesocycle_week_templates" not in src
    assert "apply_phase_rpe" in src
    assert callable(pick_challenge_phase_with_openai)
    assert callable(apply_phase_rpe)
