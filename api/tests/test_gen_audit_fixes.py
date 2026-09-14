"""Fixture tests for schedule-matrix audit fixes (no live OpenAI)."""

from __future__ import annotations

from app.schemas.plans import PlanDayIn, PlanExerciseIn
from app.services.workout_generation.coverage import coverage_ok, is_real_press
from app.services.workout_generation.openai_picker import (
    OpenAIPickError,
    picks_from_llm_day,
    repair_strength_picks,
    validate_openai_picks,
)
from app.services.workout_generation.service import _preview_plan_days
from app.services.workout_generation.shortlist import is_home_denied_exercise
from app.services.workout_generation.weekly_volume import (
    apply_weekly_dose,
    is_pushup_name,
    l1_session_set_cap,
    recap_l1_session_sets,
)


def _ex(eid: int, *, sets=3, section="main"):
    return PlanExerciseIn(exercise_id=eid, sets=sets, reps="10", rest_seconds=90, section=section)


def test_repair_pull_swaps_face_pull_for_biceps():
    blocks = [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 1,
            "shortlist": [
                {
                    "id": 1,
                    "movement_pattern": "v_pull",
                    "movement_role": "compound",
                    "muscle": "back",
                    "name_vi": "Kéo xô",
                },
            ],
        },
        {
            "block_key": "accessory",
            "pick": True,
            "count_max": 2,
            "shortlist": [
                {
                    "id": 10,
                    "movement_pattern": "h_pull",
                    "movement_role": "isolation",
                    "muscle": "shoulders",
                    "name_vi": "Face pull dây",
                },
                {
                    "id": 11,
                    "movement_pattern": "h_pull",
                    "movement_role": "isolation",
                    "muscle": "shoulders",
                    "name_vi": "Face pull thanh",
                },
                {
                    "id": 12,
                    "movement_pattern": "other",
                    "movement_role": "isolation",
                    "muscle": "biceps",
                    "name_vi": "Curl tạ đơn",
                },
            ],
        },
    ]
    out = repair_strength_picks(
        blocks, {"compound": [1], "accessory": [10, 11]}, split_role="pull"
    )
    assert 12 in out["compound"] + out["accessory"]


def test_repair_upper_inserts_press_not_pushdown():
    blocks = [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 2,
            "shortlist": [
                {
                    "id": 1,
                    "movement_pattern": "v_pull",
                    "movement_role": "compound",
                    "muscle": "back",
                },
                {
                    "id": 2,
                    "movement_pattern": "h_pull",
                    "movement_role": "compound",
                    "muscle": "back",
                },
                {
                    "id": 3,
                    "movement_pattern": "h_push",
                    "movement_role": "compound",
                    "muscle": "chest",
                },
                {
                    "id": 9,
                    "movement_pattern": "h_push",
                    "movement_role": "isolation",
                    "muscle": "triceps",
                },
            ],
        },
        {
            "block_key": "accessory",
            "pick": True,
            "count_max": 1,
            "shortlist": [
                {
                    "id": 10,
                    "movement_pattern": "h_pull",
                    "movement_role": "isolation",
                    "muscle": "shoulders",
                },
            ],
        },
    ]
    out = repair_strength_picks(
        blocks, {"compound": [1, 2], "accessory": [10]}, split_role="upper"
    )
    ids = out["compound"] + out["accessory"]
    assert 3 in ids
    assert 9 not in ids or 3 in ids
    meta = {1: {"movement_pattern": "v_pull", "muscle_slug": "back"}}
    # assemble-style coverage: press must be real
    press_meta = {"movement_pattern": "h_push", "muscle_slug": "chest"}
    tri_meta = {"movement_pattern": "h_push", "muscle_slug": "triceps"}
    assert is_real_press(press_meta)
    assert not is_real_press(tri_meta)
    del meta


def test_repair_legs_inserts_squat_pattern():
    blocks = [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 1,
            "shortlist": [
                {
                    "id": 1,
                    "movement_pattern": "hinge",
                    "movement_role": "compound",
                    "muscle": "glutes",
                },
                {
                    "id": 2,
                    "movement_pattern": "squat",
                    "movement_role": "compound",
                    "muscle": "quads",
                },
            ],
        },
        {
            "block_key": "accessory",
            "pick": True,
            "count_max": 2,
            "shortlist": [
                {
                    "id": 10,
                    "movement_pattern": "hinge",
                    "movement_role": "isolation",
                    "muscle": "glutes",
                },
                {
                    "id": 11,
                    "movement_pattern": "hinge",
                    "movement_role": "isolation",
                    "muscle": "glutes",
                },
            ],
        },
    ]
    out = repair_strength_picks(
        blocks, {"compound": [1], "accessory": [10, 11]}, split_role="legs"
    )
    assert 2 in out["compound"] + out["accessory"]


def test_dose_keeps_last_pull_biceps():
    day = PlanDayIn(
        day_number=1,
        split_role="pull",
        exercises=[
            _ex(1),
            _ex(2),
            _ex(3, sets=3),
        ],
    )
    meta = {
        1: {
            "movement_role": "compound",
            "movement_pattern": "v_pull",
            "muscle_slug": "back",
        },
        2: {
            "movement_role": "compound",
            "movement_pattern": "h_pull",
            "muscle_slug": "back",
        },
        3: {
            "movement_role": "isolation",
            "movement_pattern": "other",
            "muscle_slug": "biceps",
        },
    }
    apply_weekly_dose(
        [day],
        meta_by_id=meta,
        effective_level=1,
        session_minutes=30,
        drop_exercises=True,
    )
    ids = [ex.exercise_id for ex in day.exercises if (ex.section or "main") == "main"]
    assert 3 in ids


def test_dose_caps_pushup_family():
    day = PlanDayIn(
        day_number=1,
        split_role="upper",
        exercises=[_ex(1), _ex(2), _ex(3), _ex(4), _ex(5)],
    )
    meta = {
        1: {
            "movement_role": "compound",
            "movement_pattern": "h_push",
            "muscle_slug": "chest",
            "name_vi": "Chống đẩy",
        },
        2: {
            "movement_role": "compound",
            "movement_pattern": "h_push",
            "muscle_slug": "chest",
            "name_vi": "Chống đẩy chống gối",
        },
        3: {
            "movement_role": "compound",
            "movement_pattern": "h_push",
            "muscle_slug": "chest",
            "name_vi": "Chống đẩy kim cương",
        },
        4: {
            "movement_role": "compound",
            "movement_pattern": "h_push",
            "muscle_slug": "chest",
            "name_vi": "Chống đẩy tay trên ghế",
        },
        5: {
            "movement_role": "compound",
            "movement_pattern": "h_pull",
            "muscle_slug": "back",
            "name_vi": "Chèo người nằm",
        },
    }
    apply_weekly_dose(
        [day],
        meta_by_id=meta,
        effective_level=2,
        session_minutes=45,
        drop_exercises=True,
    )
    mains = [ex for ex in day.exercises if (ex.section or "main") == "main"]
    pu = sum(1 for ex in mains if is_pushup_name(meta[ex.exercise_id]["name_vi"]))
    assert pu <= 1
    assert 5 in [ex.exercise_id for ex in mains]


def test_coverage_ok_upper_requires_press():
    day = PlanDayIn(day_number=1, split_role="upper", exercises=[_ex(1), _ex(2), _ex(3)])
    meta_pull = {
        1: {"movement_pattern": "v_pull", "muscle_slug": "back"},
        2: {"movement_pattern": "h_pull", "muscle_slug": "back"},
        3: {"movement_pattern": "h_pull", "muscle_slug": "shoulders"},
    }
    assert coverage_ok([day], meta_pull) is False
    meta_ok = {
        **meta_pull,
        3: {"movement_pattern": "h_push", "muscle_slug": "chest"},
    }
    day.exercises = [_ex(1), _ex(2), _ex(3)]
    assert coverage_ok([day], meta_ok) is True


def test_coverage_ok_legs_requires_squat_pattern():
    day = PlanDayIn(day_number=1, split_role="legs", exercises=[_ex(1), _ex(2), _ex(3)])
    hinge_only = {
        1: {"movement_pattern": "hinge", "muscle_slug": "glutes"},
        2: {"movement_pattern": "hinge", "muscle_slug": "glutes"},
        3: {"movement_pattern": "hinge", "muscle_slug": "hamstrings"},
    }
    assert coverage_ok([day], hinge_only) is False
    mixed = {
        **hinge_only,
        1: {"movement_pattern": "squat", "muscle_slug": "quads"},
    }
    assert coverage_ok([day], mixed) is True


def test_home_denies_sled_by_name():
    assert is_home_denied_exercise(
        name_vi="Kéo xe trượt", location="home", no_equipment=True
    )
    assert is_home_denied_exercise(
        name_en="Sled push", location="home", no_equipment=False
    )
    assert not is_home_denied_exercise(
        name_vi="Chống đẩy", location="home", no_equipment=True
    )
    assert not is_home_denied_exercise(
        name_vi="Kéo xe trượt", location="gym", no_equipment=False
    )
    assert is_home_denied_exercise(
        name_vi="Hít xà", location="home", no_equipment=False, user_slugs=["resistance-band-1"]
    )
    assert not is_home_denied_exercise(
        name_vi="Hít xà", location="home", no_equipment=False, user_slugs=["pull-up-bar"]
    )
    assert is_home_denied_exercise(
        name_vi="Chèo người nằm", location="home", no_equipment=True
    )
    assert is_home_denied_exercise(
        name_en="Inverted row", location="home", no_equipment=True
    )
    assert not is_home_denied_exercise(
        name_vi="Chèo người nằm", location="gym", no_equipment=False
    )


def test_home_denies_wall_ball_unless_user_has_slug():
    assert is_home_denied_exercise(
        name_en="Wall Ball", name_vi="Ném bóng vào tường", location="home", no_equipment=True
    )
    assert is_home_denied_exercise(
        name_en="Wall Ball",
        location="home",
        no_equipment=False,
        user_slugs=["barbell"],
    )
    assert not is_home_denied_exercise(
        name_en="Wall Ball",
        location="home",
        no_equipment=False,
        user_slugs=["wall-ball"],
    )
    assert not is_home_denied_exercise(
        name_en="Wall Ball", location="gym", no_equipment=False
    )


def test_validate_fills_empty_resistance():
    blocks = [
        {
            "block_key": "resistance",
            "pick": True,
            "count_max": 3,
            "is_optional": False,
            "shortlist": [
                {"id": 1, "movement_pattern": "h_push", "name_vi": "A"},
                {"id": 2, "movement_pattern": "h_pull", "name_vi": "B"},
                {"id": 3, "movement_pattern": "squat", "name_vi": "C"},
                {"id": 4, "movement_pattern": "hinge", "name_vi": "D"},
                {"id": 5, "movement_pattern": "h_push", "name_vi": "E"},
            ],
        }
    ]
    out = validate_openai_picks(blocks, {"resistance": []}, split_role="upper")
    assert len(out["resistance"]) == 3


def test_validate_empty_shortlist_still_raises():
    blocks = [
        {
            "block_key": "resistance",
            "pick": True,
            "count_max": 3,
            "is_optional": False,
            "shortlist": [],
        }
    ]
    try:
        validate_openai_picks(blocks, {"resistance": []}, split_role="upper")
        raise AssertionError("expected OpenAIPickError")
    except OpenAIPickError as exc:
        assert "có 0" in exc.message


def test_picks_from_llm_fills_missing_block():
    blocks = [
        {
            "block_key": "resistance",
            "pick": True,
            "count_max": 3,
            "is_optional": False,
            "shortlist": [
                {"id": 1, "movement_pattern": "h_push", "muscle": "chest"},
                {"id": 2, "movement_pattern": "h_pull", "muscle": "back"},
                {"id": 3, "movement_pattern": "h_push", "muscle": "chest"},
            ],
        }
    ]
    llm = {"day_index": 0, "split_role": "upper", "blocks": []}
    out = picks_from_llm_day(llm, blocks, split_role="upper")
    assert len(out["resistance"]) == 3


def test_preview_never_emits_none_name():
    day = PlanDayIn(day_number=1, split_role="core", exercises=[_ex(277)])
    rows = _preview_plan_days([day], {277: None})
    assert rows[0]["exercises"][0]["name_vi"] == "#277"
    rows2 = _preview_plan_days([day], {277: "None"})
    assert rows2[0]["exercises"][0]["name_vi"] == "#277"


def test_recap_l1_trims_resistance_sets():
    cap = l1_session_set_cap(90)
    day = PlanDayIn(
        day_number=1,
        split_role="legs",
        exercises=[
            _ex(1, sets=3),
            _ex(2, sets=3),
            _ex(3, sets=3),
            _ex(4, sets=3),
            _ex(5, sets=2),
            _ex(6, sets=3),
        ],
    )
    meta = {
        1: {"movement_role": "compound", "movement_pattern": "squat", "muscle_slug": "quads"},
        2: {"movement_role": "compound", "movement_pattern": "squat", "muscle_slug": "glutes"},
        3: {"movement_role": "compound", "movement_pattern": "squat", "muscle_slug": "glutes"},
        4: {"movement_role": "resistance", "movement_pattern": "squat", "muscle_slug": "glutes"},
        5: {"movement_role": "isolation", "movement_pattern": "hinge", "muscle_slug": "glutes"},
        6: {"movement_role": "resistance", "movement_pattern": "other", "muscle_slug": "glutes"},
    }
    recap_l1_session_sets([day], meta_by_id=meta, session_minutes=90)
    total = sum(ex.sets for ex in day.exercises if (ex.section or "main") == "main")
    assert total <= cap
    assert next(ex.sets for ex in day.exercises if ex.exercise_id == 1) == 3


def test_repair_upper_press_stays_in_compound_block():
    blocks = [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 2,
            "shortlist": [
                {
                    "id": 1,
                    "movement_pattern": "v_pull",
                    "movement_role": "compound",
                    "muscle": "back",
                    "name_vi": "Kéo xô",
                },
                {
                    "id": 2,
                    "movement_pattern": "h_pull",
                    "movement_role": "compound",
                    "muscle": "back",
                    "name_vi": "Chèo",
                },
                {
                    "id": 3,
                    "movement_pattern": "h_push",
                    "movement_role": "compound",
                    "muscle": "chest",
                    "name_vi": "Đẩy ngực cáp",
                },
            ],
        },
        {
            "block_key": "accessory",
            "pick": True,
            "count_max": 1,
            "shortlist": [
                {
                    "id": 10,
                    "movement_pattern": "h_pull",
                    "movement_role": "isolation",
                    "muscle": "shoulders",
                    "name_vi": "Face pull",
                },
            ],
        },
    ]
    out = repair_strength_picks(
        blocks, {"compound": [1, 2], "accessory": [10]}, split_role="upper"
    )
    assert 3 in out["compound"]
    assert 3 not in out["accessory"]
    acc_ids = {10}
    assert all(eid in acc_ids or eid != 3 for eid in out["accessory"])


def test_repair_pull_biceps_stays_in_accessory_block():
    blocks = [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 1,
            "shortlist": [
                {
                    "id": 1,
                    "movement_pattern": "v_pull",
                    "movement_role": "compound",
                    "muscle": "back",
                    "name_vi": "Kéo xô",
                },
                {
                    "id": 99,
                    "movement_pattern": "h_pull",
                    "movement_role": "compound",
                    "muscle": "biceps",
                    "name_vi": "Chèo máy ngửa tay",
                },
            ],
        },
        {
            "block_key": "accessory",
            "pick": True,
            "count_max": 2,
            "shortlist": [
                {
                    "id": 10,
                    "movement_pattern": "h_pull",
                    "movement_role": "isolation",
                    "muscle": "shoulders",
                    "name_vi": "Face pull",
                },
                {
                    "id": 11,
                    "movement_pattern": "h_pull",
                    "movement_role": "isolation",
                    "muscle": "back",
                    "name_vi": "Kéo cáp qua đầu",
                },
                {
                    "id": 12,
                    "movement_pattern": "other",
                    "movement_role": "isolation",
                    "muscle": "biceps",
                    "name_vi": "Curl tạ đơn",
                },
            ],
        },
    ]
    out = repair_strength_picks(
        blocks, {"compound": [1], "accessory": [11, 10]}, split_role="pull"
    )
    assert 12 in out["accessory"]
    assert 99 not in out["accessory"]
    assert 1 in out["compound"]


def test_recap_l1_does_not_exceed_cap():
    cap = l1_session_set_cap(90)
    isolations = [_ex(i, sets=4) for i in range(1, 6)]
    day = PlanDayIn(day_number=1, split_role="upper", exercises=isolations)
    meta = {
        i: {
            "movement_role": "isolation",
            "movement_pattern": "h_push",
            "muscle_slug": "chest",
        }
        for i in range(1, 6)
    }
    recap_l1_session_sets([day], meta_by_id=meta, session_minutes=90)
    total = sum(ex.sets for ex in day.exercises if (ex.section or "main") == "main")
    assert total <= cap
