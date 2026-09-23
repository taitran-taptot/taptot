from app.services.workout_generation.skill_gate import SkillSignals, gate_pool, skill_prompt_vi
from app.services.workout_generation.skill_ladder import (
    allowed_push_rungs,
    filter_pool_by_ladder,
    pull_rung,
    pushup_rung,
)


def _item(eid: int, name_en: str, name_vi: str) -> dict:
    return {"id": eid, "name_en": name_en, "name_vi": name_vi}


WALL = _item(10, "Wall Push-up", "Chống đẩy tường")
KNEE = _item(11, "Bodyweight Knee Push Ups", "Chống đẩy chống gối")
FLOOR = _item(12, "Push Up", "Chống đẩy")
DIAMOND = _item(13, "Diamond Push Ups", "Chống đẩy kim cương")
DECLINE = _item(14, "Decline Push Up", "Chống đẩy chân trên ghế")
RING_PUSH = _item(15, "Ring Push-Up", "Chống đẩy vòng treo")
INVERTED = _item(20, "Inverted Row", "Kéo người nằm")
PULL = _item(21, "Pull Ups", "Kéo xà")
HANG = _item(22, "Dead Hang", "Treo xà thả lỏng")


def test_pushup_rungs():
    assert pushup_rung("Chống đẩy tường", "Wall Push-up") == 0
    assert pushup_rung("Chống đẩy chống gối", "Bodyweight Knee Push Ups") == 3
    assert pushup_rung("Chống đẩy", "Push Up") == 4
    assert pushup_rung("Chống đẩy kim cương", "Diamond Push Ups") == 5
    assert pushup_rung("Chống đẩy chân trên ghế", "Decline Push Up") == 6
    assert pushup_rung("Chống đẩy vòng treo", "Ring Push-Up") == 6
    assert pushup_rung("Ép ngực tạ đơn", "Dumbbell Bench Press") is None


def test_floor_20_phase1_drops_wall_and_knee():
    base = {"pushup_variant": "standard", "pushups_max": 20}
    assert allowed_push_rungs(base, phase_i=0) == frozenset({4})
    pool = [WALL, KNEE, FLOOR, DIAMOND, RING_PUSH]
    out = filter_pool_by_ladder(pool, base, phase_i=0)
    ids = {int(x["id"]) for x in out}
    assert 12 in ids
    assert 10 not in ids
    assert 11 not in ids
    assert 13 not in ids


def test_floor_20_later_phase_allows_diamond_and_ring():
    base = {"pushup_variant": "standard", "pushups_max": 20}
    assert 5 in allowed_push_rungs(base, phase_i=1)
    assert 6 in allowed_push_rungs(base, phase_i=2)
    phase2 = filter_pool_by_ladder(
        [WALL, KNEE, FLOOR, DIAMOND, DECLINE, RING_PUSH], base, phase_i=2
    )
    ids = {int(x["id"]) for x in phase2}
    assert 12 in ids
    assert 13 in ids
    assert 15 in ids
    assert 10 not in ids
    assert 11 not in ids


def test_knee_variant_phase1_keeps_knee_drops_floor():
    base = {"pushup_variant": "knee", "pushups_max": 8}
    out = filter_pool_by_ladder([WALL, KNEE, FLOOR], base, phase_i=0)
    ids = {int(x["id"]) for x in out}
    assert 11 in ids
    assert 12 not in ids
    assert 10 not in ids


def test_pullups_max_blocks_inverted_as_main():
    base = {"pullups_max": 5, "pull_test_variant": "strict"}
    out = filter_pool_by_ladder([HANG, INVERTED, PULL], base, phase_i=0)
    ids = {int(x["id"]) for x in out}
    assert 21 in ids
    assert 20 not in ids
    assert 22 not in ids
    assert pull_rung("Kéo người nằm", "Inverted Row") == 1


def test_gate_pool_uses_baseline_on_signals():
    sig = SkillSignals(
        want_knee=False,
        want_ring_row_progress=False,
        can_pullup=True,
        fitness_baseline={"pushup_variant": "standard", "pushups_max": 20},
    )
    gated = gate_pool([WALL, KNEE, FLOOR, DIAMOND], 0, sig)
    ids = {int(x["id"]) for x in gated}
    assert 12 in ids
    assert 10 not in ids
    assert 11 not in ids
    prompt = skill_prompt_vi(0, sig)
    assert "tường" in prompt.lower() or "quỳ" in prompt.lower()
    assert "sàn" in prompt
