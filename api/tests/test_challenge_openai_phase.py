"""Production 100-day challenge uses rule picks, not Chat Completions."""

import inspect

from app.services.workout_generation.phase_templates import apply_phase_rpe
from app.services.workout_generation import rule_picker
from app.services.workout_generation.service import generate_workout


def test_generate_workout_uses_rule_picks_not_http():
    src = inspect.getsource(generate_workout)
    assert "deterministic_picks" in src
    assert "pick_challenge_phase_with_openai" not in src
    assert "pick_challenge_meals_with_openai" not in src
    assert "chat/completions" not in src
    assert "urllib" not in src
    assert "build_mesocycle_week_templates" not in src
    assert "apply_phase_rpe" in src
    assert callable(apply_phase_rpe)

    picker_src = inspect.getsource(rule_picker)
    assert "chat/completions" not in picker_src
    assert "urlopen" not in picker_src
    assert callable(rule_picker.deterministic_picks)
