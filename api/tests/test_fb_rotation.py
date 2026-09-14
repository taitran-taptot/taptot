"""Full Body A/B rotation and week-level pick uniqueness."""

from app.services.workout_generation.coverage import family_of, required_patterns
from app.services.workout_generation.fb_rotation import (
    effective_pick_role,
    fb_session_title,
    fb_variant_for_offset,
)
from app.services.workout_generation.openai_picker import deterministic_picks
from app.services.workout_generation.split_map import patterns_for_split


def _fb_blocks():
    return [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 4,
            "is_optional": False,
            "shortlist": [
                {"id": 1, "movement_pattern": "h_push"},
                {"id": 2, "movement_pattern": "h_pull"},
                {"id": 3, "movement_pattern": "squat"},
                {"id": 4, "movement_pattern": "hinge"},
                {"id": 5, "movement_pattern": "v_push"},
                {"id": 6, "movement_pattern": "v_pull"},
                {"id": 7, "movement_pattern": "squat"},
                {"id": 8, "movement_pattern": "hinge"},
            ],
        },
        {
            "block_key": "accessory",
            "pick": True,
            "count_max": 2,
            "is_optional": False,
            "shortlist": [
                {"id": 10, "movement_pattern": "h_push"},
                {"id": 11, "movement_pattern": "v_push"},
                {"id": 12, "movement_pattern": "h_pull"},
                {"id": 13, "movement_pattern": "v_pull"},
                {"id": 14, "movement_pattern": "core"},
            ],
        },
    ]


def test_fb_week_is_aba():
    assert fb_variant_for_offset(0) == "fb_a"
    assert fb_variant_for_offset(1) == "fb_b"
    assert fb_variant_for_offset(2) == "fb_a"
    assert effective_pick_role("fb", fb_offset=1) == "fb_b"
    assert "Full Body A" in fb_session_title("fb_a", day_number=1)
    assert "Full Body B" in fb_session_title("fb_b", day_number=2)


def test_fb_variant_patterns():
    assert "h_push" in patterns_for_split("fb_a")
    assert "v_pull" in patterns_for_split("fb_b")
    assert required_patterns("fb_a") == ("h_push", "h_pull", "squat", "hinge")
    assert required_patterns("fb_b") == ("v_push", "v_pull", "squat", "hinge")


def test_fb_a_and_b_do_not_share_compounds():
    used: set[int] = set()
    picks_a = deterministic_picks(_fb_blocks(), split_role="fb_a", used_ids=used)
    used |= set(picks_a.get("compound", [])) | set(picks_a.get("accessory", []))
    picks_b = deterministic_picks(_fb_blocks(), split_role="fb_b", used_ids=used)
    a_comp = set(picks_a["compound"])
    b_comp = set(picks_b["compound"])
    assert a_comp.isdisjoint(b_comp)

    meta = {}
    for b in _fb_blocks():
        for x in b["shortlist"]:
            meta[x["id"]] = x["movement_pattern"]
    a_pats = {meta[i] for i in picks_a["compound"] + picks_a["accessory"] if i in meta}
    b_pats = {meta[i] for i in picks_b["compound"] + picks_b["accessory"] if i in meta}
    assert "h_push" in a_pats
    assert "h_pull" in a_pats
    assert "v_push" in b_pats
    assert "v_pull" in b_pats
    assert family_of("v_push") == "push"


def test_fb_two_compounds_two_accessories_cover_four_families():
    blocks = [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 2,
            "is_optional": False,
            "shortlist": [
                {"id": 1, "movement_pattern": "h_push"},
                {"id": 2, "movement_pattern": "h_pull"},
                {"id": 3, "movement_pattern": "squat"},
                {"id": 4, "movement_pattern": "hinge"},
            ],
        },
        {
            "block_key": "accessory",
            "pick": True,
            "count_max": 2,
            "is_optional": False,
            "shortlist": [
                {"id": 10, "movement_pattern": "h_push"},
                {"id": 11, "movement_pattern": "h_pull"},
                {"id": 12, "movement_pattern": "squat"},
                {"id": 13, "movement_pattern": "hinge"},
            ],
        },
    ]
    picks = deterministic_picks(blocks, split_role="fb_a")
    meta = {
        1: "h_push",
        2: "h_pull",
        3: "squat",
        4: "hinge",
        10: "h_push",
        11: "h_pull",
        12: "squat",
        13: "hinge",
    }
    ids = picks["compound"] + picks["accessory"]
    fams = {family_of(meta[i]) for i in ids if i in meta}
    assert fams >= {"push", "pull", "squat", "hinge"}
    assert set(picks["compound"]).issubset({1, 2, 3, 4})
    assert set(picks["accessory"]).issubset({10, 11, 12, 13})


def test_fb_warmup_pattern_does_not_steal_strength_coverage():
    blocks = [
        {
            "block_key": "general_warmup",
            "pick": True,
            "count_max": 1,
            "is_optional": False,
            "shortlist": [{"id": 90, "movement_pattern": "h_push"}],
        },
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 2,
            "is_optional": False,
            "shortlist": [
                {"id": 1, "movement_pattern": "h_push"},
                {"id": 2, "movement_pattern": "h_pull"},
                {"id": 3, "movement_pattern": "squat"},
                {"id": 4, "movement_pattern": "hinge"},
            ],
        },
        {
            "block_key": "accessory",
            "pick": True,
            "count_max": 2,
            "is_optional": False,
            "shortlist": [
                {"id": 10, "movement_pattern": "h_push"},
                {"id": 11, "movement_pattern": "h_pull"},
                {"id": 12, "movement_pattern": "squat"},
                {"id": 13, "movement_pattern": "hinge"},
            ],
        },
    ]
    picks = deterministic_picks(blocks, split_role="fb_a")
    meta = {
        1: "h_push",
        2: "h_pull",
        3: "squat",
        4: "hinge",
        10: "h_push",
        11: "h_pull",
        12: "squat",
        13: "hinge",
    }
    ids = picks["compound"] + picks["accessory"]
    fams = {family_of(meta[i]) for i in ids if i in meta}
    assert fams >= {"push", "pull", "squat", "hinge"}
