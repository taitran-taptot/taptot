from app.schemas.plans import PlanDayIn, PlanExerciseIn
from app.services.workout_generation.pull_day_menu import (
    repair_plan_day_legs_menu,
    repair_plan_day_pull_menu,
    repair_plan_day_ring_dip,
)
from app.services.workout_generation.shortlist import is_home_denied_exercise
from app.services.workout_generation.skill_gate import skill_prompt_vi, resolve_skill_signals
from app.services.workout_generation.split_map import is_denied_for_split

GEAR = ["pull-up-bar", "gymnastic-rings"]

CATALOG = {
    1: {"name_vi": "Chèo vòng treo", "name_en": "Ring Row", "movement_pattern": "h_pull", "muscle_slug": "back"},
    2: {
        "name_vi": "Bay vai sau vòng treo",
        "name_en": "Ring Rear Delt Fly",
        "movement_pattern": "h_pull",
        "muscle_slug": "shoulders-rear",
    },
    3: {
        "name_vi": "Kéo mặt vòng treo",
        "name_en": "Ring Face Pull",
        "movement_pattern": "h_pull",
        "muscle_slug": "shoulders-rear",
    },
    4: {
        "name_vi": "Hít xà",
        "name_en": "Pull-Up",
        "movement_pattern": "v_pull",
        "muscle_slug": "back",
        "movement_role": "compound",
    },
    5: {
        "name_vi": "Hít xà úp",
        "name_en": "Chin-Up",
        "movement_pattern": "v_pull",
        "muscle_slug": "back",
        "movement_role": "compound",
    },
    6: {
        "name_vi": "Hít xà vòng treo",
        "name_en": "Ring Pull-Up",
        "movement_pattern": "v_pull",
        "muscle_slug": "back",
        "movement_role": "compound",
    },
    7: {
        "name_vi": "Chèo ba lô cúi người",
        "name_en": "Bent-Over Backpack Row",
        "movement_pattern": "h_pull",
        "muscle_slug": "back",
    },
    8: {
        "name_vi": "Duỗi tay sau vòng treo",
        "name_en": "Ring Triceps Extension",
        "movement_pattern": "h_push",
        "muscle_slug": "triceps",
    },
    9: {
        "name_vi": "Bay ngực vòng treo",
        "name_en": "Ring Chest Fly",
        "movement_pattern": "h_push",
        "muscle_slug": "chest",
    },
    10: {
        "name_vi": "Nâng gối treo xà",
        "name_en": "Hanging Knee Raises",
        "movement_pattern": "core",
        "muscle_slug": "core",
    },
    11: {
        "name_vi": "Toes-to-Bar",
        "name_en": "Toes-to-Bar",
        "movement_pattern": "core",
        "muscle_slug": "core",
    },
    12: {
        "name_vi": "Chống đẩy",
        "name_en": "Push-Up",
        "movement_pattern": "h_push",
        "muscle_slug": "chest",
        "movement_role": "compound",
    },
    13: {
        "name_vi": "Cuốn đùi sau vòng treo",
        "name_en": "Ring Hamstring Curl",
        "movement_pattern": "hinge",
        "muscle_slug": "hamstrings",
        "movement_role": "isolation",
    },
    14: {
        "name_vi": "Squat Bulgaria vòng treo",
        "name_en": "Bulgarian Ring Squat",
        "movement_pattern": "squat",
        "muscle_slug": "quads",
        "movement_role": "compound",
    },
    15: {
        "name_vi": "Ngồi xổm không tạ",
        "name_en": "Bodyweight Squat",
        "movement_pattern": "squat",
        "muscle_slug": "quads",
        "movement_role": "compound",
    },
    16: {
        "name_vi": "Dip vòng có trợ",
        "name_en": "Assisted Ring Dip",
        "movement_pattern": "h_push",
        "muscle_slug": "chest-lower",
        "movement_role": "compound",
    },
    17: {
        "name_vi": "Dip vòng treo",
        "name_en": "Ring Dip",
        "movement_pattern": "h_push",
        "muscle_slug": "chest-lower",
        "movement_role": "compound",
    },
}


def _cands():
    return [{"id": eid, **meta} for eid, meta in CATALOG.items()]


def _day(split: str, ids: list[int]) -> PlanDayIn:
    return PlanDayIn(
        day_number=1,
        split_role=split,
        exercises=[PlanExerciseIn(exercise_id=i, section="main", sets=3, reps="8") for i in ids],
    )


def _meta() -> dict:
    return {k: dict(v) for k, v in CATALOG.items()}


def _ids(day: PlanDayIn) -> list[int]:
    return [ex.exercise_id for ex in day.exercises]


def test_weak_pull_uses_ring_row_menu_no_strict_no_backpack():
    day = _day("pull", [7, 8, 8, 9])
    meta = _meta()
    repair_plan_day_pull_menu(
        day,
        candidates=_cands(),
        meta_by_id=meta,
        fitness_baseline={"pullups_max": 4},
        equipment_slugs=GEAR,
        location="home",
    )
    names = " ".join(
        (meta[i].get("name_en") or "") for i in _ids(day)
    ).lower()
    assert "ring row" in names
    assert "pull-up" not in names.replace("ring pull-up", "")
    assert "chin-up" not in names
    assert "backpack" not in names
    assert "triceps" not in names
    assert "chest fly" not in names
    assert len(_ids(day)) == len(set(_ids(day)))


def test_mid_pull_requires_bar_or_chin_no_backpack_no_leak():
    day = _day("pull", [7, 8, 9])
    meta = _meta()
    repair_plan_day_pull_menu(
        day,
        candidates=_cands(),
        meta_by_id=meta,
        fitness_baseline={"pullups_max": 6},
        equipment_slugs=GEAR,
        location="home",
    )
    names = " ".join((meta[i].get("name_en") or "") for i in _ids(day)).lower()
    assert "pull-up" in names or "chin-up" in names
    assert "backpack" not in names
    assert "triceps" not in names
    assert "chest fly" not in names


def test_strong_pull_adds_ring_combo():
    day = _day("pull", [4])
    meta = _meta()
    repair_plan_day_pull_menu(
        day,
        candidates=_cands(),
        meta_by_id=meta,
        fitness_baseline={"pullups_max": 12},
        equipment_slugs=GEAR,
        location="home",
    )
    names = " ".join((meta[i].get("name_en") or "") for i in _ids(day)).lower()
    assert "ring pull-up" in names
    assert "ring row" in names
    assert "rear delt" in names or "face pull" in names


def test_session_dedupes_same_exercise_id():
    day = _day("pull", [1, 1, 2])
    meta = _meta()
    repair_plan_day_pull_menu(
        day,
        candidates=_cands(),
        meta_by_id=meta,
        fitness_baseline={"pullups_max": 4},
        equipment_slugs=GEAR,
        location="home",
    )
    assert _ids(day).count(1) == 1


def test_push_short_day_fills_core_not_duplicate_press():
    day = _day("push", [12, 12])
    meta = _meta()
    repair_plan_day_pull_menu(
        day,
        candidates=_cands(),
        meta_by_id=meta,
        fitness_baseline={"pullups_max": 6},
        equipment_slugs=GEAR,
        location="home",
    )
    ids = _ids(day)
    assert ids.count(12) == 1
    assert 10 in ids or 11 in ids


def test_band_only_does_not_inject_menu():
    day = _day("pull", [7, 8])
    meta = _meta()
    assert not repair_plan_day_pull_menu(
        day,
        candidates=_cands(),
        meta_by_id=meta,
        fitness_baseline={"pullups_max": 12},
        equipment_slugs=["resistance-band-2"],
        location="home",
    )
    assert _ids(day) == [7, 8]


def test_backpack_denied_when_bar_rings_and_pullups_ge_3():
    common = dict(
        name_en="Bent-Over Backpack Row",
        name_vi="Chèo ba lô cúi người",
        location="home",
        no_equipment=False,
        user_slugs=GEAR,
    )
    assert is_home_denied_exercise(**common, fitness_baseline={"pullups_max": 3})
    assert not is_home_denied_exercise(**common, fitness_baseline={"pullups_max": 2})
    assert not is_home_denied_exercise(
        name_en="Bent-Over Backpack Row",
        name_vi="Chèo ba lô cúi người",
        location="home",
        no_equipment=True,
        fitness_baseline={"pullups_max": 8},
    )


def test_pull_denies_front_delt_slug():
    assert is_denied_for_split("pull", muscle_slug="shoulders-front")
    assert not is_denied_for_split("pull", muscle_slug="shoulders-rear")


def test_unspecified_injects_pullup_even_if_gpt_pool_empty():
    """L1 shortlists omit difficulty-3 Pull Ups — menu still injects from catalog cands."""
    day = _day("pull", [2, 3])
    meta = _meta()
    repair_plan_day_pull_menu(
        day,
        candidates=_cands(),
        meta_by_id=meta,
        fitness_baseline={},
        equipment_slugs=GEAR,
        location="home",
    )
    names = " ".join((meta[i].get("name_en") or "") for i in _ids(day)).lower()
    assert "pull-up" in names or "chin-up" in names


def test_unspecified_pullups_injects_bar_pullup_over_chin_hold():
    day = _day("pull", [7])
    meta = _meta()
    meta[20] = {
        "name_vi": "Giữ cằm qua xà rồi hạ chậm",
        "name_en": "Chin-over-bar Hold Negative",
        "movement_pattern": "v_pull",
        "muscle_slug": "back",
    }
    day = _day("pull", [20])
    repair_plan_day_pull_menu(
        day,
        candidates=_cands(),
        meta_by_id=meta,
        fitness_baseline={},
        equipment_slugs=GEAR,
        location="home",
    )
    names = " ".join((meta[i].get("name_en") or "") for i in _ids(day)).lower()
    assert "pull-up" in names or "chin-up" in names
    assert "hold negative" not in names


def test_skill_prompt_three_bands():
    assert "ring row" in skill_prompt_vi(0, resolve_skill_signals({"pullups_max": 4})).lower()
    assert "BẮT BUỘC" in skill_prompt_vi(0, resolve_skill_signals({"pullups_max": 6}))
    strong = skill_prompt_vi(0, resolve_skill_signals({"pullups_max": 12}))
    assert "Ring Pull-Up" in strong
    assert "face pull" in strong.lower()


def test_strong_squat_l2_injects_both_ring_leg_lifts():
    day = _day("legs", [15])
    meta = _meta()
    repair_plan_day_legs_menu(
        day,
        candidates=_cands(),
        meta_by_id=meta,
        fitness_baseline={"squats_max": 31},
        equipment_slugs=GEAR,
        location="home",
        experience_level=2,
    )
    names = " ".join((meta[i].get("name_en") or "") for i in _ids(day)).lower()
    assert "bulgarian ring squat" in names
    assert "ring hamstring curl" in names


def test_ring_legs_skipped_when_squat_30_or_l1():
    meta = _meta()
    day = _day("legs", [15])
    assert not repair_plan_day_legs_menu(
        day,
        candidates=_cands(),
        meta_by_id=meta,
        fitness_baseline={"squats_max": 30},
        equipment_slugs=GEAR,
        location="home",
        experience_level=2,
    )
    weak_exp = _day("legs", [15])
    assert not repair_plan_day_legs_menu(
        weak_exp,
        candidates=_cands(),
        meta_by_id=meta,
        fitness_baseline={"squats_max": 50},
        equipment_slugs=GEAR,
        location="home",
        experience_level=1,
    )


def test_push_replaces_assisted_ring_dip_with_ring_dip():
    day = _day("push", [16, 12])
    meta = _meta()
    repair_plan_day_ring_dip(
        day,
        candidates=_cands(),
        meta_by_id=meta,
        equipment_slugs=GEAR,
        location="home",
    )
    names = " ".join((meta[i].get("name_en") or "") for i in _ids(day)).lower()
    assert "ring dip" in names
    assert "assisted" not in names
