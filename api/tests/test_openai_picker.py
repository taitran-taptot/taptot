"""Tests for OpenAI exercise pick (hard-fail, no deterministic fallback)."""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from app.services.workout_generation.openai_picker import (
    OPENAI_PICK_FAIL_VI,
    CHEST_COMPOUND_HINT,
    HOME_CHEST_COMPOUND_HINT,
    HOME_GEAR_HINT,
    OpenAIPickError,
    _index_llm_days,
    clamp_pick_count,
    compact_day_for_prompt,
    fill_mobility_picks,
    isolation_ids_from_picks,
    merge_week_b_isolation_picks,
    pick_challenge_phase_with_openai,
    pick_with_openai,
    picks_from_llm_day,
    repair_strength_picks,
    validate_openai_picks,
    validate_slot_picks,
    DOSE_PICKS_KEY,
    SLOT_PICKS_KEY,
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


def test_validate_openai_picks_happy():
    picks = {"compound": [1, 2], "accessory": [10, 11], "core": [20]}
    out = validate_openai_picks(_day_blocks(), picks)
    assert out["compound"] == [1, 2]
    assert out["accessory"] == [10, 11]
    assert out["core"] == [20]


def test_picker_keeps_optional_dose_for_validated_exercise():
    out = picks_from_llm_day(
        {
            "blocks": [
                {
                    "block_key": "compound",
                    "exercises": [
                        {"exercise_id": 1, "sets": 3, "reps": "8-10"},
                        {"exercise_id": 2, "sets": 3, "reps": "8-10"},
                    ],
                },
                {
                    "block_key": "accessory",
                    "exercise_ids": [10, 11],
                },
            ]
        },
        _day_blocks(),
    )
    assert out[DOSE_PICKS_KEY]["1"] == {"sets": 3, "reps": "8-10"}


def test_validate_fills_short_count_from_shortlist():
    out = validate_openai_picks(_day_blocks(), {"compound": [1], "accessory": [10, 11]})
    assert out["compound"][0] == 1
    assert len(out["compound"]) == 2
    assert set(out["compound"]) <= {1, 2, 3}


def test_validate_rejects_unknown_id():
    with pytest.raises(OpenAIPickError):
        validate_openai_picks(_day_blocks(), {"compound": [1, 999], "accessory": [10, 11]})


def test_validate_swaps_strength_duplicate_when_alt_exists():
    blocks = [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 1,
            "is_optional": False,
            "shortlist": [{"id": 1}, {"id": 2}],
        },
        {
            "block_key": "accessory",
            "pick": True,
            "count_max": 1,
            "is_optional": False,
            "shortlist": [{"id": 1}, {"id": 10}],
        },
    ]
    out = validate_openai_picks(blocks, {"compound": [1], "accessory": [1]})
    assert out["compound"] == [1]
    assert out["accessory"] == [10]


def test_validate_allows_strength_duplicate_when_pool_exhausted():
    blocks = [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 1,
            "is_optional": False,
            "shortlist": [{"id": 1}],
        },
        {
            "block_key": "accessory",
            "pick": True,
            "count_max": 1,
            "is_optional": False,
            "shortlist": [{"id": 1}],
        },
    ]
    out = validate_openai_picks(blocks, {"compound": [1], "accessory": [1]})
    assert out["compound"] == [1]
    assert out["accessory"] == [1]


def test_clamp_pick_count_lowers_to_shortlist():
    assert clamp_pick_count(4, 3) == 3
    assert clamp_pick_count(4, 4) == 4
    assert clamp_pick_count(4, 0) == 4
    assert clamp_pick_count(0, 3) == 0


def test_validate_clamps_accessory_when_shortlist_short():
    blocks = [
        {
            "block_key": "accessory",
            "pick": True,
            "count_max": 4,
            "is_optional": False,
            "shortlist": [{"id": 10}, {"id": 11}, {"id": 12}],
        }
    ]
    out = validate_openai_picks(blocks, {"accessory": [10, 11, 12]})
    assert out["accessory"] == [10, 11, 12]


def test_validate_empty_required_shortlist_still_fails():
    blocks = [
        {
            "block_key": "accessory",
            "pick": True,
            "count_max": 4,
            "is_optional": False,
            "shortlist": [],
        }
    ]
    with pytest.raises(OpenAIPickError) as ei:
        validate_openai_picks(blocks, {"accessory": []})
    assert "có 0" in ei.value.message


def test_picks_from_llm_day_no_fallback():
    with pytest.raises(OpenAIPickError):
        picks_from_llm_day(None, _day_blocks())


def test_picks_from_llm_day_ok():
    llm = {
        "day_index": 0,
        "blocks": [
            {"block_key": "compound", "exercise_ids": [1, 2]},
            {"block_key": "accessory", "exercise_ids": [10, 11]},
            {"block_key": "core", "exercise_ids": []},
        ],
    }
    out = picks_from_llm_day(llm, _day_blocks())
    assert out["compound"] == [1, 2]
    assert out["core"] == []


@patch("app.services.workout_generation.openai_picker.get_settings")
def test_pick_with_openai_missing_key(mock_settings):
    mock_settings.return_value.workout_gen_use_openai = True
    mock_settings.return_value.openai_api_key = ""
    with pytest.raises(OpenAIPickError) as ei:
        pick_with_openai([{"day_index": 0, "blocks": []}])
    assert "OPENAI_API_KEY" in ei.value.message


@patch("app.services.workout_generation.openai_picker.get_settings")
def test_pick_with_openai_flag_off(mock_settings):
    mock_settings.return_value.workout_gen_use_openai = False
    mock_settings.return_value.openai_api_key = "sk-test"
    with pytest.raises(OpenAIPickError) as ei:
        pick_with_openai([{"day_index": 0, "blocks": []}])
    assert "WORKOUT_GEN_USE_OPENAI" in ei.value.message


@patch("app.services.workout_generation.openai_picker.get_settings")
@patch("app.services.workout_generation.openai_picker.urllib.request.urlopen")
def test_pick_with_openai_http_error(mock_urlopen, mock_settings):
    mock_settings.return_value.workout_gen_use_openai = True
    mock_settings.return_value.openai_api_key = "sk-test"
    mock_settings.return_value.openai_model = "gpt-4o-mini"
    mock_settings.return_value.openai_base_url = "https://api.openai.com/v1"
    mock_settings.return_value.openai_timeout_seconds = 30
    mock_settings.return_value.openai_temperature = 0.2
    mock_settings.return_value.openai_max_tokens = 1024

    err = MagicMock()
    err.code = 500
    err.read.return_value = b"server error"
    import urllib.error

    mock_urlopen.side_effect = urllib.error.HTTPError(
        url="https://api.openai.com/v1/chat/completions",
        code=500,
        msg="err",
        hdrs=None,
        fp=BytesIO(b"server error"),
    )
    with pytest.raises(OpenAIPickError) as ei:
        pick_with_openai([{"day_index": 0, "split_role": "push", "blocks": []}])
    assert ei.value.message == OPENAI_PICK_FAIL_VI


@patch("app.services.workout_generation.openai_picker.get_settings")
@patch("app.services.workout_generation.openai_picker.urllib.request.urlopen")
def test_pick_with_openai_happy(mock_urlopen, mock_settings):
    mock_settings.return_value.workout_gen_use_openai = True
    mock_settings.return_value.openai_api_key = "sk-test"
    mock_settings.return_value.openai_model = "gpt-4o-mini"
    mock_settings.return_value.openai_base_url = "https://api.openai.com/v1"
    mock_settings.return_value.openai_timeout_seconds = 30
    mock_settings.return_value.openai_temperature = 0.2
    mock_settings.return_value.openai_max_tokens = 1024

    payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "days": [
                                {
                                    "day_index": 0,
                                    "blocks": [
                                        {"block_key": "compound", "exercise_ids": [1, 2]},
                                    ],
                                }
                            ]
                        }
                    )
                }
            }
        ]
    }
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    mock_urlopen.return_value = resp

    days = pick_with_openai(
        [{"day_index": 0, "split_role": "push", "label_vi": "Push", "blocks": []}],
        profile={"goal": "maintain"},
    )
    assert days[0]["day_index"] == 0
    assert days[0]["blocks"][0]["exercise_ids"] == [1, 2]


@patch("app.services.workout_generation.assemble.build_shortlist")
@patch("app.services.workout_generation.assemble._recipe_for_day")
def test_collect_clamps_accessory_count_before_openai(mock_recipe, mock_shortlist):
    from types import SimpleNamespace

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
        session_minutes=90,
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


def test_validate_mobility_short_does_not_raise():
    blocks = [
        {
            "block_key": "general_warmup",
            "pick": True,
            "count_max": 1,
            "is_optional": False,
            "shortlist": [{"id": 30, "name_vi": "Xoay vai", "muscle": "shoulders"}],
        }
    ]
    out = validate_openai_picks(blocks, {"general_warmup": []})
    assert out["general_warmup"] == []


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


def test_picks_from_llm_day_fills_omitted_warmup():
    blocks = _day_blocks() + [
        {
            "block_key": "general_warmup",
            "pick": True,
            "count_max": 1,
            "is_optional": False,
            "shortlist": [
                {"id": 30, "name_vi": "Xoay khớp vai", "muscle": "shoulders"},
            ],
        }
    ]
    llm = {
        "day_index": 0,
        "blocks": [
            {"block_key": "compound", "exercise_ids": [1, 2]},
            {"block_key": "accessory", "exercise_ids": [10, 11]},
            {"block_key": "core", "exercise_ids": []},
        ],
    }
    out = picks_from_llm_day(llm, blocks, split_role="push")
    assert out["compound"] == [1, 2]
    assert out["general_warmup"] == [30]


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


@patch("app.services.workout_generation.openai_picker.get_settings")
@patch("app.services.workout_generation.openai_picker.urllib.request.urlopen")
def test_pick_with_openai_batches_two_days(mock_urlopen, mock_settings):
    mock_settings.return_value.workout_gen_use_openai = True
    mock_settings.return_value.openai_api_key = "sk-test"
    mock_settings.return_value.openai_model = "gpt-4o-mini"
    mock_settings.return_value.openai_base_url = "https://api.openai.com/v1"
    mock_settings.return_value.openai_timeout_seconds = 30
    mock_settings.return_value.openai_temperature = 0.2
    mock_settings.return_value.openai_max_tokens = 1024

    def _resp_for_both():
        payload = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "days": [
                                    {
                                        "day_index": 0,
                                        "blocks": [
                                            {"block_key": "compound", "exercise_ids": [1]}
                                        ],
                                    },
                                    {
                                        "day_index": 1,
                                        "blocks": [
                                            {"block_key": "compound", "exercise_ids": [2]}
                                        ],
                                    },
                                ]
                            }
                        )
                    }
                }
            ]
        }
        resp = MagicMock()
        resp.read.return_value = json.dumps(payload).encode("utf-8")
        resp.__enter__.return_value = resp
        resp.__exit__.return_value = False
        return resp

    mock_urlopen.side_effect = [_resp_for_both()]
    days = pick_with_openai(
        [
            {"day_index": 0, "split_role": "push", "blocks": []},
            {"day_index": 1, "split_role": "pull", "blocks": []},
        ]
    )
    assert mock_urlopen.call_count == 1
    assert [d["day_index"] for d in days] == [0, 1]
    assert days[0]["blocks"][0]["exercise_ids"] == [1]


def test_compact_day_for_prompt_caps_shortlist():
    day = {
        "day_index": 0,
        "blocks": [
            {
                "block_key": "compound",
                "count_max": 2,
                "shortlist": [{"id": i} for i in range(1, 40)],
            }
        ],
    }
    out = compact_day_for_prompt(day, cap=20)
    assert len(out["blocks"][0]["shortlist"]) == 20
    assert out["blocks"][0]["count_max"] == 2


def test_compact_day_puts_fresh_ids_first():
    day = {
        "day_index": 0,
        "blocks": [
            {
                "block_key": "compound",
                "count_max": 1,
                "shortlist": [
                    {"id": 1, "name_vi": "Bước lên ghế", "name_en": "Step-up"},
                    {"id": 2, "name_vi": "Ngồi xổm", "name_en": "Squat"},
                    {"id": 3, "name_vi": "Leg Press"},
                ],
            }
        ],
    }
    out = compact_day_for_prompt(day, cap=2, avoid_ids={1}, avoid_stems={"step_up"})
    ids = [x["id"] for x in out["blocks"][0]["shortlist"]]
    assert 1 not in ids
    assert ids == [2, 3]


def test_validate_swaps_avoided_id_when_fresh_exists():
    blocks = [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 1,
            "is_optional": False,
            "shortlist": [
                {"id": 1, "name_vi": "Bước lên ghế", "name_en": "Step-up"},
                {"id": 2, "name_vi": "Ngồi xổm", "name_en": "Squat"},
            ],
        }
    ]
    out = validate_openai_picks(
        blocks, {"compound": [1]}, split_role="legs", avoid_ids={1}
    )
    assert out["compound"] == [2]


def test_validate_keeps_avoided_id_when_pool_exhausted():
    blocks = [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 1,
            "is_optional": False,
            "shortlist": [
                {"id": 1, "name_vi": "Bước lên ghế", "name_en": "Step-up"},
            ],
        }
    ]
    out = validate_openai_picks(
        blocks, {"compound": [1]}, split_role="legs", avoid_ids={1}
    )
    assert out["compound"] == [1]


def test_isolation_ids_skip_compounds():
    ids = isolation_ids_from_picks({"compound": [1, 2], "accessory": [10, 11], "core": [20]})
    assert ids == [10, 11, 20]


def test_merge_week_b_keeps_compounds_swaps_accessory():
    picks_a = {"compound": [1, 2], "accessory": [10, 11], "core": [20]}
    llm_b = {
        "day_index": 0,
        "blocks": [
            {"block_key": "compound", "exercise_ids": [3, 1]},
            {"block_key": "accessory", "exercise_ids": [11, 12]},
        ],
    }
    out = merge_week_b_isolation_picks(picks_a, llm_b, _day_blocks(), split_role="push")
    assert out["compound"] == [1, 2]
    assert out["accessory"] == [11, 12]


def test_merge_week_b_invalid_falls_back_to_a():
    picks_a = {"compound": [1, 2], "accessory": [10, 11]}
    llm_b = {"day_index": 0, "blocks": [{"block_key": "accessory", "exercise_ids": [999]}]}
    out = merge_week_b_isolation_picks(picks_a, llm_b, _day_blocks(), split_role="push")
    assert out["accessory"] == [10, 11]


@patch("app.services.workout_generation.openai_picker.get_settings")
def test_pick_challenge_phase_missing_key(mock_settings):
    mock_settings.return_value.workout_gen_use_openai = True
    mock_settings.return_value.openai_api_key = ""
    with pytest.raises(OpenAIPickError) as ei:
        pick_challenge_phase_with_openai([{"day_index": 0, "blocks": []}])
    assert "OPENAI_API_KEY" in ei.value.message


@patch("app.services.workout_generation.openai_picker.get_settings")
@patch("app.services.workout_generation.openai_picker.urllib.request.urlopen")
def test_pick_challenge_phase_with_openai_happy(mock_urlopen, mock_settings):
    mock_settings.return_value.workout_gen_use_openai = True
    mock_settings.return_value.openai_api_key = "sk-test"
    mock_settings.return_value.openai_model = "gpt-4o-mini"
    mock_settings.return_value.openai_base_url = "https://api.openai.com/v1"
    mock_settings.return_value.openai_timeout_seconds = 30
    mock_settings.return_value.openai_temperature = 0.2
    mock_settings.return_value.openai_max_tokens = 2048

    payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "days": [
                                {
                                    "day_index": 0,
                                    "blocks": [
                                        {"block_key": "compound", "exercise_ids": [1, 2]},
                                        {"block_key": "accessory", "exercise_ids": [10, 11]},
                                    ],
                                }
                            ],
                            "week_b": [
                                {
                                    "day_index": 0,
                                    "blocks": [
                                        {"block_key": "accessory", "exercise_ids": [11, 12]},
                                    ],
                                }
                            ],
                            "rationale_vi": "Pha 1 ưu tiên form và phục hồi.",
                        }
                    )
                }
            }
        ]
    }
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    mock_urlopen.return_value = resp

    out = pick_challenge_phase_with_openai(
        [{"day_index": 0, "split_role": "push", "label_vi": "Push", "blocks": []}],
        profile={"goal": "maintain"},
        phase={"key": "accumulation", "month": 1},
        avoid_ids=[99],
    )
    assert mock_urlopen.call_count == 1
    assert out["days"][0]["blocks"][0]["exercise_ids"] == [1, 2]
    assert out["week_b"][0]["blocks"][0]["exercise_ids"] == [11, 12]
    assert "meals" not in out
    assert "form" in out["rationale_vi"]
    body = json.loads(mock_urlopen.call_args[0][0].data.decode("utf-8"))
    system = body["messages"][0]["content"]
    user = json.loads(body["messages"][1]["content"])
    assert "food_pool" not in user
    assert "nutrition" not in user
    assert "do not pick foods" in system.lower()
    assert user["avoid_ids"] == [99]
    assert user["phase"]["month"] == 1
    assert user["required_day_indexes"] == [0]


def test_index_llm_days_accepts_one_based_and_positional():
    payload = [{"day_index": 0}, {"day_index": 1}, {"day_index": 2}]
    one_based = _index_llm_days(
        [
            {"day_index": 1, "blocks": [{"exercise_ids": [1]}]},
            {"day_index": 2, "blocks": [{"exercise_ids": [2]}]},
            {"day_index": 3, "blocks": [{"exercise_ids": [3]}]},
        ],
        payload,
    )
    assert set(one_based) == {0, 1, 2}
    assert one_based[0]["blocks"][0]["exercise_ids"] == [1]
    assert one_based[2]["blocks"][0]["exercise_ids"] == [3]

    positional = _index_llm_days(
        [
            {"blocks": [{"exercise_ids": [10]}]},
            {"blocks": [{"exercise_ids": [20]}]},
            {"blocks": [{"exercise_ids": [30]}]},
        ],
        payload,
    )
    assert positional[1]["blocks"][0]["exercise_ids"] == [20]


def _mock_chat_resp(content_obj: dict) -> MagicMock:
    payload = {"choices": [{"message": {"content": json.dumps(content_obj)}}]}
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


@patch("app.services.workout_generation.openai_picker.get_settings")
@patch("app.services.workout_generation.openai_picker.urllib.request.urlopen")
def test_pick_challenge_retries_missing_day(mock_urlopen, mock_settings):
    mock_settings.return_value.workout_gen_use_openai = True
    mock_settings.return_value.openai_api_key = "sk-test"
    mock_settings.return_value.openai_model = "gpt-4o-mini"
    mock_settings.return_value.openai_base_url = "https://api.openai.com/v1"
    mock_settings.return_value.openai_timeout_seconds = 30
    mock_settings.return_value.openai_temperature = 0.2
    mock_settings.return_value.openai_max_tokens = 4096

    first = {
        "days": [
            {"day_index": 0, "blocks": [{"block_key": "compound", "exercise_ids": [1]}]},
        ],
        "rationale_vi": "Pha 1.",
    }
    second = {
        "days": [
            {"day_index": 1, "blocks": [{"block_key": "compound", "exercise_ids": [2]}]},
        ]
    }
    mock_urlopen.side_effect = [_mock_chat_resp(first), _mock_chat_resp(second)]
    week = [
        {"day_index": 0, "split_role": "push", "blocks": []},
        {"day_index": 1, "split_role": "pull", "blocks": []},
    ]
    out = pick_challenge_phase_with_openai(week)
    assert mock_urlopen.call_count == 2
    assert [d["day_index"] for d in out["days"]] == [0, 1]
    assert out["days"][1]["blocks"][0]["exercise_ids"] == [2]
    assert out["rationale_vi"] == "Pha 1."
    assert "meals" not in out
    second_body = json.loads(mock_urlopen.call_args_list[1][0][0].data.decode("utf-8"))
    user2 = json.loads(second_body["messages"][1]["content"])
    assert "food_pool" not in user2
    assert user2["required_day_indexes"] == [1]


@patch("app.services.workout_generation.openai_picker.get_settings")
@patch("app.services.workout_generation.openai_picker.urllib.request.urlopen")
def test_pick_challenge_accepts_one_based_day_index(mock_urlopen, mock_settings):
    mock_settings.return_value.workout_gen_use_openai = True
    mock_settings.return_value.openai_api_key = "sk-test"
    mock_settings.return_value.openai_model = "gpt-4o-mini"
    mock_settings.return_value.openai_base_url = "https://api.openai.com/v1"
    mock_settings.return_value.openai_timeout_seconds = 30
    mock_settings.return_value.openai_temperature = 0.2
    mock_settings.return_value.openai_max_tokens = 4096
    mock_urlopen.return_value = _mock_chat_resp(
        {
            "days": [
                {"day_index": 1, "blocks": [{"block_key": "compound", "exercise_ids": [1]}]},
                {"day_index": 2, "blocks": [{"block_key": "compound", "exercise_ids": [2]}]},
                {"day_index": 3, "blocks": [{"block_key": "compound", "exercise_ids": [3]}]},
            ],
            "rationale_vi": "ok",
        }
    )
    week = [
        {"day_index": 0, "blocks": []},
        {"day_index": 1, "blocks": []},
        {"day_index": 2, "blocks": []},
    ]
    out = pick_challenge_phase_with_openai(week)
    assert mock_urlopen.call_count == 1
    assert [d["day_index"] for d in out["days"]] == [0, 1, 2]
    assert out["days"][2]["blocks"][0]["exercise_ids"] == [3]


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


def test_validate_slot_picks_keeps_gpt_ids():
    llm = {
        "day_index": 0,
        "slots": [
            {"key": "h_press", "exercise_ids": [2]},
            {"key": "v_press", "exercise_ids": [5]},
            {"key": "chest_iso", "exercise_ids": [11]},
            {"key": "push_arm_iso", "exercise_ids": [20]},
        ],
    }
    out = validate_slot_picks(_push_prompt_slots(), llm, split_role="push")
    assert out["compound"] == [2, 5]
    assert out["accessory"] == [11, 20]
    assert out[SLOT_PICKS_KEY]["h_press"] == [2]


def test_validate_slot_picks_drops_unknown_id_and_fills_from_pool():
    llm = {"slots": [{"key": "h_press", "exercise_ids": [999]}]}
    out = validate_slot_picks(_push_prompt_slots(), llm, split_role="push")
    assert 999 not in out["compound"]
    assert out[SLOT_PICKS_KEY]["h_press"][0] in {1, 2}


def test_validate_slot_picks_rejects_empty_required_pool():
    slots = [
        {
            "key": "h_press",
            "block_key": "compound",
            "pick": 1,
            "required": True,
            "pool": [],
        }
    ]
    with pytest.raises(OpenAIPickError):
        validate_slot_picks(slots, {"slots": [{"key": "h_press", "exercise_ids": [1]}]})


def test_picks_from_llm_day_slot_path_skips_quota_repair():
    slots = _push_prompt_slots()
    llm = {
        "slots": [
            {"key": "h_press", "exercise_ids": [1]},
            {"key": "v_press", "exercise_ids": [5]},
            {"key": "chest_iso", "exercise_ids": [10]},
            {"key": "push_arm_iso", "exercise_ids": [20]},
        ]
    }
    blocks = [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 2,
            "shortlist": [{"id": 1}, {"id": 5}],
        },
        {
            "block_key": "accessory",
            "pick": True,
            "count_max": 2,
            "shortlist": [{"id": 10}, {"id": 20}],
        },
        {
            "block_key": "general_warmup",
            "pick": True,
            "count_max": 1,
            "shortlist": [{"id": 90, "muscle": "chest", "name_vi": "Giãn ngực"}],
        },
    ]
    out = picks_from_llm_day(llm, blocks, split_role="push", slots=slots)
    assert out["compound"] == [1, 5]
    assert out["accessory"] == [10, 20]


def test_merge_week_b_slots_keeps_compounds():
    slots = _push_prompt_slots()
    picks_a = validate_slot_picks(
        slots,
        {
            "slots": [
                {"key": "h_press", "exercise_ids": [1]},
                {"key": "v_press", "exercise_ids": [5]},
                {"key": "chest_iso", "exercise_ids": [10]},
                {"key": "push_arm_iso", "exercise_ids": [20]},
            ]
        },
        split_role="push",
    )
    llm_b = {
        "slots": [
            {"key": "h_press", "exercise_ids": [2]},
            {"key": "chest_iso", "exercise_ids": [11]},
        ]
    }
    out = merge_week_b_isolation_picks(
        picks_a, llm_b, [], split_role="push", slots=slots
    )
    assert out[SLOT_PICKS_KEY]["h_press"] == [1]
    assert out[SLOT_PICKS_KEY]["v_press"] == [5]
    assert out[SLOT_PICKS_KEY]["chest_iso"] == [11]
    assert out["compound"] == [1, 5]


def test_merge_week_b_slots_falls_back_to_different_accessory():
    slots = _push_prompt_slots()
    picks_a = validate_slot_picks(
        slots,
        {
            "slots": [
                {"key": "h_press", "exercise_ids": [1]},
                {"key": "v_press", "exercise_ids": [5]},
                {"key": "chest_iso", "exercise_ids": [10]},
                {"key": "push_arm_iso", "exercise_ids": [20]},
            ]
        },
        split_role="push",
    )
    for llm_b in (None, {"slots": [{"key": "chest_iso", "exercise_ids": [10]}]}):
        out = merge_week_b_isolation_picks(
            picks_a, llm_b, [], split_role="push", slots=slots
        )
        assert out["compound"] == [1, 5]
        assert out[SLOT_PICKS_KEY]["chest_iso"] == [11]
        assert out[SLOT_PICKS_KEY]["push_arm_iso"] == [20]


def test_compact_day_does_not_cap_slot_pools():
    day = {
        "day_index": 0,
        "slots": [
            {
                "key": "h_press",
                "block_key": "compound",
                "pick": 1,
                "pool": [{"id": i} for i in range(1, 40)],
            }
        ],
        "blocks": [
            {
                "block_key": "compound",
                "shortlist": [{"id": i} for i in range(1, 40)],
            }
        ],
    }
    out = compact_day_for_prompt(day, cap=12)
    assert len(out["slots"][0]["pool"]) == 39
    assert out["chest_compound_hint"] == CHEST_COMPOUND_HINT
    assert "Never decline" in out["chest_compound_hint"]
    assert "L2+ barbell or dumbbell" in out["chest_compound_hint"]
    assert "blocks" not in out or "compound" not in [
        b.get("block_key") for b in out.get("blocks") or []
    ]


def test_compact_day_home_uses_home_chest_hint():
    day = {
        "day_index": 0,
        "location": "home",
        "slots": [
            {
                "key": "h_press",
                "block_key": "resistance",
                "pick": 1,
                "pool": [{"id": 1}],
            }
        ],
    }
    out = compact_day_for_prompt(day)
    assert out["chest_compound_hint"] == HOME_CHEST_COMPOUND_HINT
    assert "barbell or dumbbell" not in out["chest_compound_hint"]
    assert "band press" in out["chest_compound_hint"]
    assert "tube band" in HOME_GEAR_HINT
    assert "resistance-band-1" in HOME_GEAR_HINT


def test_validate_slot_picks_drops_decline_from_h_press():
    slots = [
        {
            "key": "h_press",
            "block_key": "compound",
            "pick": 1,
            "required": True,
            "pool": [
                {
                    "id": 1,
                    "name_vi": "Đẩy ngực nằm",
                    "name_en": "Barbell Bench Press",
                },
                {
                    "id": 4,
                    "name_vi": "Đẩy ngực dốc xuống",
                    "name_en": "Decline Bench",
                },
            ],
        }
    ]
    out = validate_slot_picks(
        slots, {"slots": [{"key": "h_press", "exercise_ids": [4]}]}
    )
    assert out[SLOT_PICKS_KEY]["h_press"] == [1]


def test_validate_slot_picks_drops_tate_from_h_press():
    slots = [
        {
            "key": "h_press",
            "block_key": "compound",
            "pick": 1,
            "required": True,
            "pool": [
                {
                    "id": 1,
                    "name_vi": "Đẩy ngực nằm tạ đơn",
                    "name_en": "Dumbbell Bench Press",
                    "muscle": "chest",
                },
                {
                    "id": 90,
                    "name_vi": "Ép tay sau nằm xoay cổ tay",
                    "name_en": "Tate Press",
                    "muscle": "triceps",
                },
            ],
        }
    ]
    out = validate_slot_picks(
        slots, {"slots": [{"key": "h_press", "exercise_ids": [90]}]}
    )
    assert out[SLOT_PICKS_KEY]["h_press"] == [1]


def test_validate_slot_picks_l2_swaps_machine_for_free_weight_chest():
    slots = [
        {
            "key": "h_press",
            "block_key": "compound",
            "pick": 1,
            "required": True,
            "pool": [
                {
                    "id": 1,
                    "name_vi": "Đẩy ngực nằm tạ đòn",
                    "name_en": "Barbell Bench Press",
                    "muscle": "chest",
                },
                {
                    "id": 2,
                    "name_vi": "Đẩy ngực máy",
                    "name_en": "Machine Chest Press",
                    "muscle": "chest",
                },
            ],
        }
    ]
    out = validate_slot_picks(
        slots,
        {"slots": [{"key": "h_press", "exercise_ids": [2]}]},
        experience_level=2,
    )
    assert out[SLOT_PICKS_KEY]["h_press"] == [1]


def test_validate_slot_picks_l1_keeps_machine_chest():
    slots = [
        {
            "key": "h_press",
            "block_key": "compound",
            "pick": 1,
            "required": True,
            "pool": [
                {
                    "id": 1,
                    "name_vi": "Đẩy ngực nằm tạ đòn",
                    "name_en": "Barbell Bench Press",
                    "muscle": "chest",
                },
                {
                    "id": 2,
                    "name_vi": "Đẩy ngực máy",
                    "name_en": "Machine Chest Press",
                    "muscle": "chest",
                },
            ],
        }
    ]
    out = validate_slot_picks(
        slots,
        {"slots": [{"key": "h_press", "exercise_ids": [2]}]},
        experience_level=1,
    )
    assert out[SLOT_PICKS_KEY]["h_press"] == [2]
