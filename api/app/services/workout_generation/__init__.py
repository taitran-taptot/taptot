"""Workout generation package (hybrid deterministic + OpenAI shortlist pick)."""

from app.services.workout_generation.service import generate_workout

__all__ = ["generate_workout"]
