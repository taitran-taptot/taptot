"""Production 100-day challenge uses OpenAI phase picks, not deterministic swaps."""

import inspect

from app.services.workout_generation.openai_picker import pick_challenge_meals_with_openai, pick_challenge_phase_with_openai
from app.services.workout_generation.phase_templates import apply_phase_rpe
from app.services.workout_generation.service import generate_workout


def test_generate_workout_uses_openai_challenge_phases():
    src = inspect.getsource(generate_workout)
    assert "pick_challenge_phase_with_openai" in src
    assert "pick_challenge_meals_with_openai" in src
    assert "build_mesocycle_week_templates" not in src
    assert "apply_phase_rpe" in src
    assert callable(pick_challenge_phase_with_openai)
    assert callable(pick_challenge_meals_with_openai)
    assert callable(apply_phase_rpe)


def test_challenge_phase_prompt_uses_load_hints():
    src = inspect.getsource(pick_challenge_phase_with_openai)
    assert "load_hints" in src
    assert "load_kg" in src
    assert "test_kit" in src
    assert '"reps":"8-10","rest_seconds":90' not in src
    assert "12-15" in src
    assert "knowledge_playbook_vi" in src
    assert "skill_prompt_vi" in src
    assert "HARD limits" in src
    assert "raw test AMRAP" in src
    assert "4 bài test" in src
    assert "không một hệ số k" in src
    assert "0-5" in src
    assert "Never copy one kilogram" in src
    assert "Jumping Jack" in src
    assert "leftover minutes" in src


def test_challenge_meal_prompt_uses_phase_knowledge():
    src = inspect.getsource(pick_challenge_meals_with_openai)
    assert "knowledge_by_phase" in src
    assert "never carb-cycle L1" in src
    assert "Do not include a snack slot" in src
    assert "pick fruit only for snack" in src
