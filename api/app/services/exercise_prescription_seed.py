"""Canonical set/rep defaults by experience level × movement role."""

from __future__ import annotations

# (experience_level, movement_role, default_sets, default_reps)
PRESCRIPTION_SEED: list[tuple[int, str, int, int]] = [
    (1, "compound", 3, 10),
    (1, "isolation", 3, 15),
    (2, "compound", 3, 8),
    (2, "isolation", 3, 12),
    (3, "compound", 3, 6),
    (3, "isolation", 3, 10),
]

PRESCRIBABLE_ROLES = frozenset({"compound", "isolation"})
