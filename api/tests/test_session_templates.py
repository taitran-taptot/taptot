"""Golden tests for standard session slot templates + retagged classifiers."""

from app.services.exercise_movement_pattern import infer_movement_pattern
from app.services.exercise_movement_role import infer_movement_role
from app.services.workout_generation.coverage import family_of
from app.services.workout_generation.openai_picker import deterministic_picks
from app.services.workout_generation.session_templates import (
    fill_strength_slots,
    slots_for_session,
)


def test_face_pull_is_isolation_h_pull():
    ex = {"name_en": "Face Pull", "name_vi": "Kéo dây mặt", "exercise_type": "main"}
    assert infer_movement_role(ex) == "isolation"
    assert infer_movement_pattern(ex) == "h_pull"


def test_ep_nguc_without_press_is_isolation_other():
    ex = {"name_en": "Chest Fly", "name_vi": "Ép ngực", "exercise_type": "main"}
    assert infer_movement_role(ex) == "isolation"
    assert infer_movement_pattern(ex) == "other"


def test_bench_press_stays_compound_h_push():
    ex = {
        "name_en": "Barbell Bench Press",
        "name_vi": "Ép ngực tạ đòn",
        "exercise_type": "main",
    }
    assert infer_movement_role(ex) == "compound"
    assert infer_movement_pattern(ex) == "h_push"


def test_lateral_raise_is_isolation_not_v_push():
    ex = {"name_en": "Dumbbell Lateral Raise", "name_vi": "Dang vai", "exercise_type": "main"}
    assert infer_movement_role(ex) == "isolation"
    assert infer_movement_pattern(ex) == "other"


def test_ohp_stays_compound_v_push():
    ex = {"name_en": "Overhead Press", "name_vi": "Đẩy vai trên đầu", "exercise_type": "main"}
    assert infer_movement_role(ex) == "compound"
    assert infer_movement_pattern(ex) == "v_push"


def _push_45_blocks():
    return [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 2,
            "is_optional": False,
            "shortlist": [
                {
                    "id": 1,
                    "name_vi": "Bench Press",
                    "movement_pattern": "h_push",
                    "movement_role": "compound",
                    "muscle": "chest",
                },
                {
                    "id": 2,
                    "name_vi": "Overhead Press",
                    "movement_pattern": "v_push",
                    "movement_role": "compound",
                    "muscle": "shoulders",
                },
                {
                    "id": 3,
                    "name_vi": "Incline Press",
                    "movement_pattern": "h_push",
                    "movement_role": "compound",
                    "muscle": "chest",
                },
            ],
        },
        {
            "block_key": "accessory",
            "pick": True,
            "count_max": 2,
            "is_optional": False,
            "shortlist": [
                {
                    "id": 10,
                    "name_vi": "Chest Fly",
                    "movement_pattern": "other",
                    "movement_role": "isolation",
                    "muscle": "chest",
                },
                {
                    "id": 11,
                    "name_vi": "Lateral Raise",
                    "movement_pattern": "other",
                    "movement_role": "isolation",
                    "muscle": "shoulders",
                },
                {
                    "id": 12,
                    "name_vi": "Pushdown",
                    "movement_pattern": "other",
                    "movement_role": "isolation",
                    "muscle": "triceps",
                },
                {
                    "id": 99,
                    "name_vi": "Face Pull",
                    "movement_pattern": "h_pull",
                    "movement_role": "isolation",
                    "muscle": "shoulders",
                },
            ],
        },
    ]


def test_push_45_slots_presses_then_isos():
    picks = deterministic_picks(_push_45_blocks(), split_role="push")
    assert picks["compound"] == [1, 2]
    assert 10 in picks["accessory"]
    assert 99 not in picks["compound"]
    assert 11 not in picks["compound"]
    assert 10 not in picks["compound"]


def test_push_slots_reject_biceps_curl():
    from app.services.workout_generation.session_templates import candidate_matches_slot

    slots = slots_for_session("push", compound_n=1, accessory_n=3, location="home")
    extra = next(s for s in slots if s.key == "push_extra_iso")
    assert "curl" not in extra.prefer
    curl = {
        "id": 50,
        "name_vi": "Cuốn tay với dây",
        "name_en": "Band Curl",
        "movement_pattern": "other",
        "movement_role": "isolation",
        "muscle": "biceps",
    }
    assert not candidate_matches_slot(extra, curl, split_role="push")


def test_push_slots_reject_ring_rear_delt_and_face_pull():
    from app.services.workout_generation.session_templates import candidate_matches_slot

    slots = slots_for_session("push", compound_n=1, accessory_n=4, location="home")
    push_iso_slots = [s for s in slots if s.key in {
        "chest_iso", "push_arm_iso", "push_extra_iso", "push_finisher_iso"
    }]
    assert push_iso_slots
    face_pull = {
        "id": 842,
        "name_vi": "Face pull vòng treo",
        "name_en": "Ring Face Pull",
        "movement_pattern": "other",
        "movement_role": "isolation",
        "muscle": "shoulders-rear",
    }
    rear_fly = {
        "id": 843,
        "name_vi": "Bay vai sau vòng treo",
        "name_en": "Ring Rear Delt Fly",
        "movement_pattern": "h_pull",
        "movement_role": "isolation",
        "muscle": "shoulders-rear",
    }
    for slot in push_iso_slots:
        assert not candidate_matches_slot(slot, face_pull, split_role="push")
        assert not candidate_matches_slot(slot, rear_fly, split_role="push")


def test_fly_does_not_fill_ohp_or_bench_slot():
    slots = slots_for_session("push", compound_n=2, accessory_n=2, location="gym")
    pool = [
        {
            "id": 10,
            "name_vi": "Chest Fly",
            "movement_pattern": "other",
            "movement_role": "isolation",
            "muscle": "chest",
            "_block": "accessory",
        },
        {
            "id": 11,
            "name_vi": "Lateral Raise",
            "movement_pattern": "other",
            "movement_role": "isolation",
            "muscle": "shoulders",
            "_block": "accessory",
        },
        {
            "id": 1,
            "name_vi": "Bench Press",
            "movement_pattern": "h_push",
            "movement_role": "compound",
            "muscle": "chest",
            "_block": "compound",
        },
        {
            "id": 2,
            "name_vi": "OHP",
            "movement_pattern": "v_push",
            "movement_role": "compound",
            "muscle": "shoulders",
            "_block": "compound",
        },
    ]
    filled = fill_strength_slots("push", slots, pool)
    assert filled["compound"] == [1, 2]
    assert 10 not in filled["compound"]
    assert 11 not in filled["compound"]


def test_home_push_45_two_patterns_plus_iso():
    blocks = [
        {
            "block_key": "resistance",
            "pick": True,
            "count_max": 3,
            "is_optional": False,
            "shortlist": [
                {
                    "id": 1,
                    "name_vi": "Chống đẩy",
                    "movement_pattern": "h_push",
                    "movement_role": "resistance",
                    "muscle": "chest",
                },
                {
                    "id": 2,
                    "name_vi": "Pike Push-Up",
                    "movement_pattern": "v_push",
                    "movement_role": "resistance",
                    "muscle": "shoulders",
                },
                {
                    "id": 3,
                    "name_vi": "Ép ngực band",
                    "movement_pattern": "other",
                    "movement_role": "resistance",
                    "muscle": "chest",
                },
                {
                    "id": 4,
                    "name_vi": "Dip",
                    "movement_pattern": "h_push",
                    "movement_role": "resistance",
                    "muscle": "chest",
                },
            ],
        },
        {
            "block_key": "conditioning",
            "pick": True,
            "count_max": 1,
            "is_optional": False,
            "shortlist": [{"id": 50, "movement_pattern": "other", "movement_role": "conditioning"}],
        },
    ]
    picks = deterministic_picks(blocks, split_role="push")
    ids = picks["resistance"]
    assert len(ids) == 3
    assert 1 in ids
    assert 2 in ids
    assert 3 in ids
    meta = {1: "h_push", 2: "v_push", 3: "other", 4: "h_push"}
    fams = {family_of(meta[i]) for i in ids if meta[i] != "other"}
    assert "push" in fams
    assert picks["conditioning"] == [50]


def test_upper_45_has_chest_press_and_fly_not_pullover():
    blocks = [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 2,
            "is_optional": False,
            "shortlist": [
                {
                    "id": 1,
                    "name_vi": "Đẩy ngực cáp",
                    "movement_pattern": "h_push",
                    "movement_role": "compound",
                    "muscle": "chest",
                },
                {
                    "id": 2,
                    "name_vi": "Chèo cáp ngồi",
                    "movement_pattern": "h_pull",
                    "movement_role": "compound",
                    "muscle": "back",
                },
                {
                    "id": 3,
                    "name_vi": "Kéo xô",
                    "movement_pattern": "v_pull",
                    "movement_role": "compound",
                    "muscle": "back",
                },
            ],
        },
        {
            "block_key": "accessory",
            "pick": True,
            "count_max": 2,
            "is_optional": False,
            "shortlist": [
                {
                    "id": 10,
                    "name_vi": "Mở ngực tạ đơn",
                    "movement_pattern": "other",
                    "movement_role": "isolation",
                    "muscle": "chest",
                },
                {
                    "id": 11,
                    "name_vi": "Kéo cáp qua đầu dây thừng",
                    "movement_pattern": "h_pull",
                    "movement_role": "isolation",
                    "muscle": "back",
                },
                {
                    "id": 12,
                    "name_vi": "Nhún vai tạ đơn",
                    "movement_pattern": "h_pull",
                    "movement_role": "isolation",
                    "muscle": "back",
                },
                {
                    "id": 13,
                    "name_vi": "Kéo dây về mặt cáp",
                    "movement_pattern": "h_pull",
                    "movement_role": "isolation",
                    "muscle": "shoulders",
                },
            ],
        },
    ]
    picks = deterministic_picks(blocks, split_role="upper", day_index=0)
    assert picks["compound"] == [1, 2]
    assert 10 in picks["accessory"]
    assert 11 not in picks["accessory"] or 10 in picks["accessory"]
    assert 12 not in picks["compound"]
    chest_ids = {1, 10}
    all_ids = set(picks["compound"] + picks["accessory"])
    assert chest_ids <= all_ids


def test_upper_b_uses_pulldown_not_second_row():
    blocks = [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 2,
            "is_optional": False,
            "shortlist": [
                {
                    "id": 1,
                    "name_vi": "Đẩy ngực dốc lên",
                    "movement_pattern": "h_push",
                    "movement_role": "compound",
                    "muscle": "chest",
                },
                {
                    "id": 2,
                    "name_vi": "Chèo cáp",
                    "movement_pattern": "h_pull",
                    "movement_role": "compound",
                    "muscle": "back",
                },
                {
                    "id": 3,
                    "name_vi": "Kéo xô",
                    "movement_pattern": "v_pull",
                    "movement_role": "compound",
                    "muscle": "back",
                },
            ],
        },
        {
            "block_key": "accessory",
            "pick": True,
            "count_max": 2,
            "is_optional": False,
            "shortlist": [
                {
                    "id": 10,
                    "name_vi": "Mở ngực",
                    "movement_pattern": "other",
                    "movement_role": "isolation",
                    "muscle": "chest",
                },
                {
                    "id": 13,
                    "name_vi": "Face Pull",
                    "movement_pattern": "h_pull",
                    "movement_role": "isolation",
                    "muscle": "shoulders",
                },
            ],
        },
    ]
    picks = deterministic_picks(blocks, split_role="upper", day_index=2)
    assert 1 in picks["compound"]
    assert 3 in picks["compound"]
    assert 10 in picks["accessory"]


def test_upper_slots_skip_hip_abduction():
    slots = slots_for_session("upper", compound_n=1, accessory_n=4, location="gym")
    pool = [
        {
            "id": 1,
            "name_vi": "Bench Press",
            "movement_pattern": "h_push",
            "movement_role": "compound",
            "muscle": "chest",
            "_block": "compound",
        },
        {
            "id": 2,
            "name_vi": "Bent-over Row",
            "movement_pattern": "h_pull",
            "movement_role": "compound",
            "muscle": "back",
            "_block": "compound",
        },
        {
            "id": 10,
            "name_vi": "Ép ngực",
            "movement_pattern": "other",
            "movement_role": "isolation",
            "muscle": "chest",
            "_block": "accessory",
        },
        {
            "id": 11,
            "name_vi": "Curl",
            "movement_pattern": "other",
            "movement_role": "isolation",
            "muscle": "biceps",
            "_block": "accessory",
        },
        {
            "id": 12,
            "name_vi": "Pushdown",
            "movement_pattern": "other",
            "movement_role": "isolation",
            "muscle": "triceps",
            "_block": "accessory",
        },
        {
            "id": 13,
            "name_vi": "Dang vai",
            "movement_pattern": "other",
            "movement_role": "isolation",
            "muscle": "shoulders",
            "_block": "accessory",
        },
        {
            "id": 99,
            "name_vi": "Dạng hông",
            "name_en": "Bodyweight Hip Abduction",
            "movement_pattern": "other",
            "movement_role": "isolation",
            "muscle": "glutes",
            "_block": "accessory",
        },
    ]
    filled = fill_strength_slots("upper", slots, pool)
    picked = [i for ids in filled.values() for i in ids]
    assert 99 not in picked
    assert 1 in picked


def test_prefer_knee_pushup_over_standard():
    slots = slots_for_session(
        "upper", compound_n=1, accessory_n=0, location="home", allow_bar_moves=False
    )
    pool = [
        {
            "id": 1,
            "name_vi": "Chống đẩy",
            "name_en": "Push-up",
            "movement_pattern": "h_push",
            "movement_role": "resistance",
            "muscle": "chest",
            "_block": "resistance",
        },
        {
            "id": 2,
            "name_vi": "Chống đẩy chống gối",
            "name_en": "Knee Push-ups",
            "movement_pattern": "h_push",
            "movement_role": "resistance",
            "muscle": "chest",
            "_block": "resistance",
        },
    ]
    filled = fill_strength_slots("upper", slots, pool, prefer_knee=True)
    picked = [i for ids in filled.values() for i in ids]
    assert picked == [2]


def test_phase_avoid_ids_then_fallback():
    slots = slots_for_session(
        "upper", compound_n=1, accessory_n=0, location="home", allow_bar_moves=False
    )
    pool = [
        {
            "id": 1,
            "name_vi": "Chống đẩy tường",
            "name_en": "Wall Push-up",
            "movement_pattern": "h_push",
            "movement_role": "resistance",
            "muscle": "chest",
            "_block": "resistance",
        },
        {
            "id": 2,
            "name_vi": "Chống đẩy dốc",
            "name_en": "Incline Push-up",
            "movement_pattern": "h_push",
            "movement_role": "resistance",
            "muscle": "chest",
            "_block": "resistance",
        },
    ]
    fresh = fill_strength_slots("upper", slots, pool, avoid_ids={1})
    assert [i for ids in fresh.values() for i in ids] == [2]
    reuse = fill_strength_slots("upper", slots, [pool[0]], avoid_ids={1})
    assert [i for ids in reuse.values() for i in ids] == [1]


def test_phase_avoid_step_up_stem():
    slots = slots_for_session("legs", compound_n=1, accessory_n=0, location="gym")
    pool = [
        {
            "id": 1,
            "name_vi": "Bước lên ghế",
            "name_en": "Step-up",
            "movement_pattern": "squat",
            "movement_role": "compound",
            "muscle": "quads",
            "_block": "compound",
        },
        {
            "id": 2,
            "name_vi": "Ngồi xổm",
            "name_en": "Squat",
            "movement_pattern": "squat",
            "movement_role": "compound",
            "muscle": "quads",
            "_block": "compound",
        },
    ]
    filled = fill_strength_slots("legs", slots, pool, avoid_stems={"step_up"})
    assert [i for ids in filled.values() for i in ids] == [2]


def test_pools_for_slots_push_two_chest_excludes_fly_from_h_press():
    from app.services.workout_generation.muscle_quotas import CHEST_SLUGS
    from app.services.workout_generation.session_templates import pools_for_slots

    slots = slots_for_session("push", compound_n=2, accessory_n=2, location="gym")
    keys = [s.key for s in slots]
    assert "h_press" in keys
    assert "chest_iso" in keys
    pool = [
        {
            "id": 1,
            "name_vi": "Đẩy ngực nằm",
            "name_en": "Barbell Bench Press",
            "movement_pattern": "h_push",
            "movement_role": "compound",
            "muscle": "chest",
            "_block": "compound",
        },
        {
            "id": 2,
            "name_vi": "Đẩy vai",
            "name_en": "Overhead Press",
            "movement_pattern": "v_push",
            "movement_role": "compound",
            "muscle": "shoulders",
            "_block": "compound",
        },
        {
            "id": 3,
            "name_vi": "Ép ngực",
            "name_en": "Chest Fly",
            "movement_pattern": "other",
            "movement_role": "isolation",
            "muscle": "chest",
            "_block": "accessory",
        },
        {
            "id": 4,
            "name_vi": "Đá tay sau",
            "name_en": "Tricep Kickback",
            "movement_pattern": "other",
            "movement_role": "isolation",
            "muscle": "triceps",
            "_block": "accessory",
        },
    ]
    pools = pools_for_slots(pool, slots, split_role="push")
    h_ids = {x["id"] for x in pools["h_press"]}
    chest_iso_ids = {x["id"] for x in pools["chest_iso"]}
    assert 1 in h_ids
    assert 3 not in h_ids
    assert all(x["muscle"] in CHEST_SLUGS for x in pools["h_press"] + pools["chest_iso"])
    assert 3 in chest_iso_ids
    assert 1 not in chest_iso_ids


def _chest_pool_candidates():
    return [
        {
            "id": 1,
            "name_vi": "Đẩy ngực nằm tạ đòn",
            "name_en": "Barbell Bench Press",
            "movement_pattern": "h_push",
            "movement_role": "compound",
            "muscle": "chest",
            "_block": "compound",
        },
        {
            "id": 2,
            "name_vi": "Máy đẩy ngực",
            "name_en": "Machine Chest Press",
            "movement_pattern": "h_push",
            "movement_role": "compound",
            "muscle": "chest",
            "_block": "compound",
        },
        {
            "id": 3,
            "name_vi": "Đẩy ngực dốc lên tạ đơn",
            "name_en": "Incline Dumbbell Press",
            "movement_pattern": "h_push",
            "movement_role": "compound",
            "muscle": "chest",
            "_block": "compound",
        },
        {
            "id": 4,
            "name_vi": "Đẩy ngực dốc xuống",
            "name_en": "Decline Bench Press",
            "movement_pattern": "h_push",
            "movement_role": "compound",
            "muscle": "chest",
            "_block": "compound",
        },
        {
            "id": 5,
            "name_vi": "Dip ngực",
            "name_en": "Chest Dip",
            "movement_pattern": "h_push",
            "movement_role": "compound",
            "muscle": "chest",
            "_block": "compound",
        },
        {
            "id": 6,
            "name_vi": "Đẩy vai",
            "name_en": "Overhead Press",
            "movement_pattern": "v_push",
            "movement_role": "compound",
            "muscle": "shoulders",
            "_block": "compound",
        },
    ]


def test_h_press_pool_excludes_decline_and_dip():
    from app.services.workout_generation.session_templates import pools_for_slots

    slots = slots_for_session("push", compound_n=3, accessory_n=2, location="gym")
    pools = pools_for_slots(_chest_pool_candidates(), slots, split_role="push")
    h_ids = [x["id"] for x in pools["h_press"]]
    extra_ids = [x["id"] for x in pools.get("extra_press") or []]
    assert 4 not in h_ids
    assert 5 not in h_ids
    assert 4 not in extra_ids
    assert 5 not in extra_ids
    h_slot = next(s for s in slots if s.key == "h_press")
    extra_slot = next(s for s in slots if s.key == "extra_press")
    assert any("decline" in a for a in h_slot.avoid)
    assert any("dip" in a for a in extra_slot.avoid)
    assert extra_slot.prefer and any("incline" in p for p in extra_slot.prefer)
    assert not any(p == "dip" for p in extra_slot.prefer)


def test_h_press_pool_l1_machine_before_barbell():
    from app.services.workout_generation.session_templates import pools_for_slots

    slots = slots_for_session(
        "push", compound_n=2, accessory_n=2, location="gym", experience_level=1
    )
    pools = pools_for_slots(
        _chest_pool_candidates(), slots, split_role="push", experience_level=1
    )
    h_ids = [x["id"] for x in pools["h_press"]]
    assert h_ids[0] == 2
    assert 1 in h_ids
    assert h_ids.index(2) < h_ids.index(1)


def test_h_press_pool_l2_barbell_before_machine():
    from app.services.workout_generation.session_templates import pools_for_slots

    slots = slots_for_session(
        "push", compound_n=3, accessory_n=2, location="gym", experience_level=2
    )
    pools = pools_for_slots(
        _chest_pool_candidates(), slots, split_role="push", experience_level=2
    )
    h_ids = [x["id"] for x in pools["h_press"]]
    extra_ids = [x["id"] for x in pools["extra_press"]]
    assert h_ids[0] == 1
    assert extra_ids[0] == 3
    assert 2 in h_ids
    assert h_ids.index(1) < h_ids.index(2)


def test_h_press_is_chest_only_and_excludes_tate():
    from app.services.workout_generation.muscle_quotas import CHEST_SLUGS, TRICEPS_SLUGS
    from app.services.workout_generation.session_templates import pools_for_slots

    slots = slots_for_session("push", compound_n=3, accessory_n=2, location="gym")
    h_slot = next(s for s in slots if s.key == "h_press")
    assert h_slot.muscles == CHEST_SLUGS
    assert h_slot.muscles.isdisjoint(TRICEPS_SLUGS)
    assert any("tate" in a for a in h_slot.avoid)
    assert any("ép tay sau" in a for a in h_slot.avoid)
    pool = _chest_pool_candidates() + [
        {
            "id": 90,
            "name_vi": "Ép tay sau nằm xoay cổ tay",
            "name_en": "Tate Press",
            "movement_pattern": "h_push",
            "movement_role": "compound",
            "muscle": "triceps",
            "_block": "compound",
        },
        {
            "id": 91,
            "name_vi": "Ép tay sau nằm xoay cổ tay",
            "name_en": "Tate Press",
            "movement_pattern": "h_push",
            "movement_role": "compound",
            "muscle": "chest",
            "_block": "compound",
        },
    ]
    pools = pools_for_slots(pool, slots, split_role="push", experience_level=2)
    h_ids = {x["id"] for x in pools["h_press"]}
    extra_ids = {x["id"] for x in pools.get("extra_press") or []}
    assert 90 not in h_ids
    assert 91 not in h_ids
    assert 90 not in extra_ids
    assert 91 not in extra_ids
    assert 1 in h_ids

