"""Tests for rule-based exercise picks (no LLM)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.workout_generation.rule_picker import (
    SLOT_PICKS_KEY,
    clamp_pick_count,
    deterministic_picks,
    fill_mobility_picks,
    isolation_ids_from_picks,
    merge_week_b_isolation_picks,
    repair_strength_picks,
)


def _day_blocks():
    return [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 2,
            "is_optional": False,
            "shortlist": [
                {"id": 1, "name_vi": "A"},
                {"id": 2, "name_vi": "B"},
                {"id": 3, "name_vi": "C"},
            ],
        },
        {
            "block_key": "accessory",
            "pick": True,
            "count_max": 2,
            "is_optional": False,
            "shortlist": [
                {"id": 10, "name_vi": "D"},
                {"id": 11, "name_vi": "E"},
                {"id": 12, "name_vi": "F"},
            ],
        },
        {
            "block_key": "core",
            "pick": True,
            "count_max": 1,
            "is_optional": True,
            "shortlist": [{"id": 20, "name_vi": "Plank"}],
        },
    ]


def _push_prompt_slots():
    return [
        {
            "key": "h_press",
            "block_key": "compound",
            "pick": 1,
            "required": True,
            "pool": [
                {"id": 1, "name_vi": "Đẩy ngực", "pattern": "h_push", "muscle": "chest"},
                {"id": 2, "name_vi": "Chống đẩy", "pattern": "h_push", "muscle": "chest"},
            ],
        },
        {
            "key": "v_press",
            "block_key": "compound",
            "pick": 1,
            "required": True,
            "pool": [
                {"id": 5, "name_vi": "Đẩy vai", "pattern": "v_push", "muscle": "shoulders"},
            ],
        },
        {
            "key": "chest_iso",
            "block_key": "accessory",
            "pick": 1,
            "required": True,
            "pool": [
                {"id": 10, "name_vi": "Ép ngực", "pattern": "other", "muscle": "chest"},
                {"id": 11, "name_vi": "Pec deck", "pattern": "other", "muscle": "chest"},
            ],
        },
        {
            "key": "push_arm_iso",
            "block_key": "accessory",
            "pick": 1,
            "required": True,
            "pool": [
                {"id": 20, "name_vi": "Đá tay sau", "pattern": "other", "muscle": "triceps"},
            ],
        },
    ]


def test_clamp_pick_count_lowers_to_shortlist():
    assert clamp_pick_count(4, 3) == 3
    assert clamp_pick_count(4, 4) == 4
    assert clamp_pick_count(4, 0) == 4
    assert clamp_pick_count(0, 3) == 0


@patch("app.services.workout_generation.assemble.build_shortlist")
@patch("app.services.workout_generation.assemble._recipe_for_day")
def test_collect_clamps_accessory_count_to_shortlist(mock_recipe, mock_shortlist):
    from app.services.session_blocks import BlockSpec
    from app.services.workout_generation.assemble import collect_day_shortlists_for_prompt
    from app.services.workout_generation.shortlist import ShortlistItem

    mock_recipe.return_value = [
        BlockSpec(
            block_key="accessory",
            label_vi="Isolation",
            plan_section="main",
            movement_role="isolation",
            count_min=4,
            count_max=4,
            duration_min_minutes=None,
            duration_max_minutes=None,
            is_optional=False,
            sort_order=40,
        )
    ]
    mock_shortlist.return_value = [
        ShortlistItem(id=10, name_vi="A", movement_role="isolation", movement_pattern="other", muscle_slug="chest", difficulty=2),
        ShortlistItem(id=11, name_vi="B", movement_role="isolation", movement_pattern="other", muscle_slug="chest", difficulty=2),
        ShortlistItem(id=12, name_vi="C", movement_role="isolation", movement_pattern="other", muscle_slug="triceps", difficulty=2),
    ]
    out = collect_day_shortlists_for_prompt(
        MagicMock(),
        frame_day=SimpleNamespace(split_role="push"),
        experience_level=2,
        session_minutes=60,
        equipment_slugs=[],
        no_equipment=False,
        ai_suggest_equipment=False,
        location="gym",
        split_role="push",
    )
    acc = out[0]
    assert acc["block_key"] == "accessory"
    assert acc["count_max"] == 3
    assert acc["count_min"] == 3
    assert len(acc["shortlist"]) == 3


def test_fill_mobility_warmup_skips_pullups():
    blocks = [
        {
            "block_key": "general_warmup",
            "pick": True,
            "count_max": 1,
            "is_optional": False,
            "shortlist": [
                {
                    "id": 103,
                    "name_vi": "Hít xà lòng bàn tay hướng vào",
                    "name_en": "Chin Ups",
                    "movement_role": "compound",
                    "muscle": "back",
                },
                {"id": 40, "name_vi": "Giãn xô vòng treo", "muscle": "back"},
            ],
        }
    ]
    out = fill_mobility_picks(blocks, {"general_warmup": [103]}, split_role="pull")
    assert out["general_warmup"] == [40]


def test_fill_mobility_picks_warmup_from_shortlist():
    blocks = [
        {
            "block_key": "general_warmup",
            "pick": True,
            "count_max": 1,
            "is_optional": False,
            "shortlist": [
                {"id": 31, "name_vi": "Giãn hamstring", "muscle": "hamstrings"},
                {"id": 30, "name_vi": "Xoay khớp vai", "muscle": "shoulders"},
            ],
        }
    ]
    out = fill_mobility_picks(blocks, {"general_warmup": []}, split_role="push")
    assert out["general_warmup"] == [30]


def test_fill_mobility_replaces_wrong_push_cooldown():
    blocks = [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 1,
            "shortlist": [
                {
                    "id": 1,
                    "movement_pattern": "h_push",
                    "movement_role": "compound",
                    "muscle": "chest",
                }
            ],
        },
        {
            "block_key": "cooldown",
            "pick": True,
            "count_max": 1,
            "is_optional": False,
            "shortlist": [
                {"id": 31, "name_vi": "Giãn hamstring", "muscle": "hamstrings"},
                {"id": 32, "name_vi": "Giãn ngực tại khung cửa", "muscle": "chest"},
            ],
        },
    ]
    out = fill_mobility_picks(
        blocks, {"compound": [1], "cooldown": [31]}, split_role="push"
    )
    assert out["cooldown"] == [32]


def test_repair_strength_does_not_invent_ids():
    blocks = [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 2,
            "shortlist": [
                {"id": 1, "movement_pattern": "h_push", "movement_role": "compound", "muscle": "chest"},
                {"id": 2, "movement_pattern": "h_push", "movement_role": "compound", "muscle": "chest"},
                {"id": 3, "movement_pattern": "v_push", "movement_role": "compound", "muscle": "shoulders"},
            ],
        },
        {
            "block_key": "accessory",
            "pick": True,
            "count_max": 2,
            "shortlist": [
                {"id": 10, "movement_pattern": "other", "movement_role": "isolation", "muscle": "chest"},
                {"id": 11, "movement_pattern": "other", "movement_role": "isolation", "muscle": "triceps"},
                {"id": 12, "movement_pattern": "other", "movement_role": "isolation", "muscle": "shoulders"},
            ],
        },
    ]
    out = repair_strength_picks(
        blocks,
        {"compound": [1, 2], "accessory": [10, 10]},
        split_role="push",
    )
    allowed = {1, 2, 3, 10, 11, 12}
    for ids in out.values():
        assert set(ids) <= allowed


def test_isolation_ids_skip_compounds():
    ids = isolation_ids_from_picks({"compound": [1, 2], "accessory": [10, 11], "core": [20]})
    assert ids == [10, 11, 20]


def test_merge_week_b_without_slots_copies_week_a():
    picks_a = {"compound": [1, 2], "accessory": [10, 11], "core": [20]}
    out = merge_week_b_isolation_picks(
        picks_a,
        {"blocks": [{"block_key": "accessory", "exercise_ids": [11, 12]}]},
        _day_blocks(),
        split_role="push",
    )
    assert out["compound"] == [1, 2]
    assert out["accessory"] == [10, 11]
    assert out["core"] == [20]


def test_merge_week_b_slots_keeps_compounds_swaps_isolation():
    slots = _push_prompt_slots()
    picks_a = {
        "compound": [1, 5],
        "accessory": [10, 20],
        SLOT_PICKS_KEY: {
            "h_press": [1],
            "v_press": [5],
            "chest_iso": [10],
            "push_arm_iso": [20],
        },
    }
    out = merge_week_b_isolation_picks(picks_a, None, [], split_role="push", slots=slots)
    assert out[SLOT_PICKS_KEY]["h_press"] == [1]
    assert out[SLOT_PICKS_KEY]["v_press"] == [5]
    assert out[SLOT_PICKS_KEY]["chest_iso"] == [11]
    assert out[SLOT_PICKS_KEY]["push_arm_iso"] == [20]
    assert out["compound"] == [1, 5]


def test_merge_week_b_slots_restores_empty_resistance_from_week_a():
    slots = [
        {
            "key": "h_pull",
            "block_key": "resistance",
            "pick": 1,
            "pool": [{"id": 2, "name_vi": "Alt row"}],
        },
        {
            "key": "v_pull",
            "block_key": "resistance",
            "pick": 1,
            "pool": [{"id": 3, "name_vi": "Alt pulldown"}],
        },
    ]
    picks_a = {
        "resistance": [1, 4],
        SLOT_PICKS_KEY: {"h_pull": [1], "v_pull": [4]},
    }
    out = merge_week_b_isolation_picks(
        picks_a, None, [], split_role="pull", slots=slots
    )
    assert out["resistance"] == [1, 4]


def test_merge_week_b_slots_falls_back_to_different_accessory():
    slots = _push_prompt_slots()
    picks_a = {
        "compound": [1, 5],
        "accessory": [10, 20],
        SLOT_PICKS_KEY: {
            "h_press": [1],
            "v_press": [5],
            "chest_iso": [10],
            "push_arm_iso": [20],
        },
    }
    out = merge_week_b_isolation_picks(picks_a, None, [], split_role="push", slots=slots)
    assert out["compound"] == [1, 5]
    assert out[SLOT_PICKS_KEY]["chest_iso"] == [11]
    assert out[SLOT_PICKS_KEY]["push_arm_iso"] == [20]


def test_deterministic_picks_fills_resistance():
    blocks = [
        {
            "block_key": "resistance",
            "pick": True,
            "count_max": 3,
            "is_optional": False,
            "shortlist": [
                {"id": 1, "movement_pattern": "h_push", "name_vi": "A", "movement_role": "compound", "muscle": "chest"},
                {"id": 2, "movement_pattern": "h_pull", "name_vi": "B", "movement_role": "compound", "muscle": "back"},
                {"id": 3, "movement_pattern": "squat", "name_vi": "C", "movement_role": "compound", "muscle": "quads"},
                {"id": 4, "movement_pattern": "hinge", "name_vi": "D", "movement_role": "compound", "muscle": "glutes"},
                {"id": 5, "movement_pattern": "h_push", "name_vi": "E", "movement_role": "isolation", "muscle": "chest"},
            ],
        }
    ]
    out = deterministic_picks(blocks, split_role="upper")
    assert len(out["resistance"]) == 3
