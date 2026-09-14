"""Canonical session block templates by experience level (structure for AI gen)."""

from __future__ import annotations

# (
#   experience_level, sort_order, block_key, label_vi, plan_section, movement_role,
#   count_min, count_max, duration_min_minutes, duration_max_minutes, is_optional
# )
SessionBlockSeed = tuple[
    int, int, str, str, str, str | None, int, int, int | None, int | None, bool
]


def _blocks_for_level(
    level: int,
    *,
    mobility_dyn: tuple[int, int],
    compound: tuple[int, int],
    accessory: tuple[int, int],
    core: tuple[int, int],
) -> list[SessionBlockSeed]:
    return [
        (level, 10, "general_warmup", "Khởi động chung", "warmup", "mobility", 1, 1, 3, 5, False),
        (
            level,
            20,
            "dynamic_mobility",
            "Mobility động",
            "warmup",
            "mobility",
            mobility_dyn[0],
            mobility_dyn[1],
            3,
            5,
            False,
        ),
        (
            level,
            30,
            "ramp_sets",
            "Set khởi động tăng dần mức tạ",
            "main",
            None,
            0,
            0,
            5,
            10,
            False,
        ),
        (
            level,
            40,
            "compound",
            "Bài tập chính (compound)",
            "main",
            "compound",
            compound[0],
            compound[1],
            None,
            None,
            False,
        ),
        (
            level,
            50,
            "accessory",
            "Bài tập phụ (isolation)",
            "main",
            "isolation",
            accessory[0],
            accessory[1],
            None,
            None,
            False,
        ),
        (
            level,
            60,
            "core",
            "Core",
            "main",
            "isolation",
            core[0],
            core[1],
            None,
            None,
            True,
        ),
        (level, 70, "cardio", "Cardio", "cardio", "cardio", 0, 1, 10, 30, True),
        (level, 80, "cooldown", "Thả lỏng / giãn cơ", "cooldown", "mobility", 1, 1, 3, 5, False),
    ]


SESSION_BLOCK_SEED: list[SessionBlockSeed] = [
    *_blocks_for_level(1, mobility_dyn=(1, 2), compound=(1, 1), accessory=(3, 3), core=(0, 1)),
    *_blocks_for_level(2, mobility_dyn=(1, 2), compound=(2, 2), accessory=(4, 4), core=(1, 1)),
    *_blocks_for_level(3, mobility_dyn=(2, 2), compound=(2, 2), accessory=(5, 5), core=(1, 2)),
]

BLOCK_KEYS = (
    "general_warmup",
    "dynamic_mobility",
    "ramp_sets",
    "compound",
    "accessory",
    "core",
    "cardio",
    "cooldown",
)
