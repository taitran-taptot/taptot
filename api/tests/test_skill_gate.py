"""Phase skill gates: knee → floor, ring row → pull-up."""

from app.services.workout_generation.shortlist import is_home_denied_exercise
from app.services.workout_generation.skill_gate import (
    SkillSignals,
    apply_skill_gate_to_week,
    gate_pool,
    item_allowed_for_phase,
    replace_gated_ids,
    resolve_skill_signals,
)
from app.services.workout_generation.weekly_volume import prefer_knee_pushups


def _item(eid: int, name_en: str, name_vi: str) -> dict:
    return {"id": eid, "name_en": name_en, "name_vi": name_vi}


FLOOR = _item(1, "Push Up", "Chống đẩy")
KNEE = _item(2, "Bodyweight Knee Push Ups", "Chống đẩy chống gối")
PULL = _item(3, "Pull Ups", "Kéo xà")
ROW = _item(4, "Ring Row", "Chèo vòng treo")
SCAP = _item(5, "Scapular Pull-up", "Kéo xà bằng bả vai")


def test_prefer_knee_when_variant_knee_even_with_kit():
    assert prefer_knee_pushups(
        location="home",
        no_equipment=False,
        pushups_max=12,
        pushup_variant="knee",
    )
    assert prefer_knee_pushups(
        location="home",
        no_equipment=False,
        pushups_max=12,
        fitness_baseline={"pushup_variant": "knee"},
    )
    assert not prefer_knee_pushups(
        location="home",
        no_equipment=False,
        pushups_max=12,
        pushup_variant="standard",
    )


def test_signals_ring_row_without_pullups():
    sig = resolve_skill_signals(
        {
            "pushup_variant": "knee",
            "pushups_max": 8,
            "pull_test_variant": "inverted_row",
            "inverted_rows_max": 10,
        },
        location="home",
        no_equipment=False,
    )
    assert sig.want_knee
    assert sig.want_ring_row_progress
    assert not sig.can_pullup


def test_signals_pullups_max_blocks_row_progress():
    sig = resolve_skill_signals(
        {
            "pull_test_variant": "strict",
            "pullups_max": 4,
            "inverted_rows_max": 12,
        }
    )
    assert sig.can_pullup
    assert not sig.want_ring_row_progress


def test_phase1_drops_floor_and_raw_pullup():
    sig = SkillSignals(want_knee=True, want_ring_row_progress=True, can_pullup=False)
    pool = [FLOOR, KNEE, PULL, ROW, SCAP]
    gated = gate_pool(pool, 0, sig)
    ids = {int(x["id"]) for x in gated}
    assert 1 not in ids
    assert 3 not in ids
    assert 2 in ids
    assert 4 in ids
    assert 5 in ids
    assert not item_allowed_for_phase(FLOOR, 0, sig)
    assert item_allowed_for_phase(FLOOR, 2, sig)
    assert item_allowed_for_phase(PULL, 2, sig)


def test_phase3_keeps_both_and_ranks_hard_first():
    sig = SkillSignals(want_knee=True, want_ring_row_progress=True, can_pullup=False)
    pool = [FLOOR, KNEE, PULL, ROW]
    gated = gate_pool(pool, 2, sig)
    ids = [int(x["id"]) for x in gated]
    assert set(ids) == {1, 2, 3, 4}
    assert ids.index(1) < ids.index(2)
    assert ids.index(3) < ids.index(4)


def test_apply_skill_gate_to_week_clones_pools():
    sig = SkillSignals(want_knee=True, want_ring_row_progress=True, can_pullup=False)
    week = [
        {
            "day_index": 0,
            "slots": [{"key": "h_press", "pool": [FLOOR, KNEE]}],
            "blocks": [{"block_key": "compound", "shortlist": [PULL, ROW]}],
        }
    ]
    out = apply_skill_gate_to_week(week, 0, sig)
    press_ids = {int(x["id"]) for x in out[0]["slots"][0]["pool"]}
    pull_ids = {int(x["id"]) for x in out[0]["blocks"][0]["shortlist"]}
    assert press_ids == {2}
    assert 3 not in pull_ids
    assert {int(x["id"]) for x in week[0]["slots"][0]["pool"]} == {1, 2}


def test_replace_gated_ids_swaps_floor_in_phase1():
    sig = SkillSignals(want_knee=True, want_ring_row_progress=False, can_pullup=False)
    out = replace_gated_ids([1], [FLOOR, KNEE], 0, sig)
    assert out == [2]


def test_l1_home_allows_pullup_when_tested():
    common = dict(
        name_en="Pull-Up",
        name_vi="Hít xà",
        location="home",
        no_equipment=False,
        user_slugs=["pull-up-bar"],
        experience_level=1,
    )
    assert is_home_denied_exercise(**common)
    assert not is_home_denied_exercise(
        **common, fitness_baseline={"pullups_max": 4, "pull_test_variant": "strict"}
    )
    assert is_home_denied_exercise(
        name_en="Bar Dip",
        name_vi="Dip xà kép",
        location="home",
        no_equipment=False,
        user_slugs=["parallel-bars"],
        experience_level=1,
        fitness_baseline={"pullups_max": 8},
    )
