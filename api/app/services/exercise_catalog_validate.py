"""Validate exercise catalog fields used by Generator V1.6."""

from __future__ import annotations

from typing import Any

from app.core.exceptions import BadRequestError
from app.services.exercise_catalog_classify import DIFFICULTY_LABELS, VALID_VENUES
from app.services.exercise_movement_pattern import VALID_PATTERNS
from app.services.exercise_movement_role import VALID_ROLES

VALID_EXERCISE_TYPES = frozenset({"warmup", "main", "cooldown", "cardio"})


def validate_exercise_catalog_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Mutate a create/update payload: clamp enums and sync difficulty_label."""
    out = dict(data)
    if "movement_pattern" in out and out["movement_pattern"] is not None:
        pat = str(out["movement_pattern"]).strip().lower()
        if pat not in VALID_PATTERNS:
            raise BadRequestError(
                f"movement_pattern phải là một trong: {', '.join(sorted(VALID_PATTERNS))}"
            )
        out["movement_pattern"] = pat
    if "venue" in out and out["venue"] is not None:
        venue = str(out["venue"]).strip().lower()
        if venue not in VALID_VENUES:
            raise BadRequestError("venue phải là gym, home hoặc both")
        out["venue"] = venue
    if "movement_role" in out and out["movement_role"] is not None:
        role = str(out["movement_role"]).strip().lower()
        if role not in VALID_ROLES:
            raise BadRequestError(
                f"movement_role phải là một trong: {', '.join(sorted(VALID_ROLES))}"
            )
        out["movement_role"] = role
    if "exercise_type" in out and out["exercise_type"] is not None:
        et = str(out["exercise_type"]).strip().lower()
        if et not in VALID_EXERCISE_TYPES:
            raise BadRequestError("exercise_type phải là warmup, main, cooldown hoặc cardio")
        out["exercise_type"] = et
    if "difficulty" in out and out["difficulty"] is not None:
        try:
            diff = int(out["difficulty"])
        except (TypeError, ValueError) as exc:
            raise BadRequestError("difficulty phải là số 1–4") from exc
        if diff < 1 or diff > 4:
            raise BadRequestError("difficulty phải từ 1 đến 4")
        out["difficulty"] = diff
        out["difficulty_label"] = DIFFICULTY_LABELS[diff]
    return out
