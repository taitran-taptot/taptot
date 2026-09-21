"""Unit tests for split_map, repair, coverage, deterministic picks."""

from app.services.session_blocks import BlockSpec
from app.services.workout_generation.coverage import (
    diversified_pick,
    family_of,
    repair_day_coverage,
    repair_plan_day_upper_pull,
    required_families,
)
from app.services.workout_generation.openai_picker import deterministic_picks
from app.services.workout_generation.repair import repair_block_picks
from app.services.workout_generation.shortlist import ShortlistItem
from app.services.workout_generation.split_map import (
    all_seed_split_roles,
    muscle_hints_for_split,
    patterns_for_split,
)


def test_split_map_covers_all_frame_roles():
    roles = {"push", "pull", "legs", "upper", "fb", "core"}
    known = all_seed_split_roles()
    assert roles <= known, f"Unmapped split roles: {roles - known}"
    for role in roles:
        assert len(patterns_for_split(role)) >= 1


def test_upper_and_fb_have_muscle_hints():
    assert "co-nguc" in muscle_hints_for_split("upper")
    assert "co-lung" in muscle_hints_for_split("upper")
    assert "v_push" in patterns_for_split("fb")
    assert "v_pull" in patterns_for_split("fb")


def test_final_upper_coverage_replaces_core_with_pull_without_adding_sets():
    from app.schemas.plans import PlanDayIn, PlanExerciseIn

    day = PlanDayIn(
        day_number=1,
        split_role="upper",
        exercises=[
            PlanExerciseIn(exercise_id=1, sets=3, section="main"),
            PlanExerciseIn(exercise_id=2, sets=2, section="main"),
            PlanExerciseIn(exercise_id=3, sets=2, section="main"),
        ],
    )
    meta = {
        1: {
            "movement_role": "compound",
            "movement_pattern": "h_push",
            "muscle_slug": "chest",
        },
        2: {
            "movement_role": "isolation",
            "movement_pattern": "other",
            "muscle_slug": "biceps",
        },
        3: {
            "movement_role": "isolation",
            "movement_pattern": "core",
            "muscle_slug": "core-upper",
        },
    }
    pool = [
        ShortlistItem(
            id=10,
            name_vi="Kéo cáp ngang",
            movement_role="compound",
            movement_pattern="h_pull",
            muscle_slug="back",
            difficulty=2,
        )
    ]
    before_sets = sum(e.sets for e in day.exercises)
    assert repair_plan_day_upper_pull(day, candidates=pool, meta_by_id=meta)
    assert [e.exercise_id for e in day.exercises] == [1, 2, 10]
    assert sum(e.sets for e in day.exercises) == before_sets
    assert meta[10]["movement_pattern"] == "h_pull"


def test_repair_drops_invalid_and_fills():
    block = BlockSpec(
        block_key="compound",
        label_vi="Compound",
        plan_section="main",
        movement_role="compound",
        count_min=1,
        count_max=2,
        duration_min_minutes=None,
        duration_max_minutes=None,
        is_optional=False,
        sort_order=40,
    )
    short = [
        ShortlistItem(1, "A", "compound", "h_push", "chest", 2),
        ShortlistItem(2, "B", "compound", "v_push", "shoulders", 2),
        ShortlistItem(3, "C", "compound", "h_push", "chest", 3),
    ]
    out = repair_block_picks(
        block=block,
        picked_ids=[99, 1, 1, 2, 3],
        shortlist=short,
        used_ids=set(),
    )
    assert out == [1, 2]


def test_repair_optional_empty_when_no_shortlist():
    block = BlockSpec(
        block_key="core",
        label_vi="Core",
        plan_section="main",
        movement_role="isolation",
        count_min=0,
        count_max=1,
        duration_min_minutes=None,
        duration_max_minutes=None,
        is_optional=True,
        sort_order=60,
    )
    assert repair_block_picks(block=block, picked_ids=[1], shortlist=[], used_ids=set()) == []


def test_deterministic_picks_respects_count_max():
    blocks = [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 2,
            "is_optional": False,
            "shortlist": [
                {"id": 10, "movement_pattern": "h_push"},
                {"id": 11, "movement_pattern": "h_pull"},
                {"id": 12, "movement_pattern": "h_push"},
            ],
        },
        {"block_key": "ramp_sets", "pick": False, "count_max": 0, "shortlist": []},
    ]
    picks = deterministic_picks(blocks, split_role="upper")
    assert len(picks["compound"]) == 2
    assert "ramp_sets" not in picks


def _upper_day_blocks(*, compound_n=2, accessory_n=3):
    return [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": compound_n,
            "is_optional": False,
            "shortlist": [
                {"id": 1, "movement_pattern": "h_pull", "name_vi": "Row"},
                {"id": 2, "movement_pattern": "h_pull", "name_vi": "Row2"},
                {"id": 3, "movement_pattern": "h_push", "name_vi": "Bench"},
                {"id": 4, "movement_pattern": "v_pull", "name_vi": "Pulldown"},
            ],
        },
        {
            "block_key": "accessory",
            "pick": True,
            "count_max": accessory_n,
            "is_optional": False,
            "shortlist": [
                {"id": 10, "movement_pattern": "h_pull", "name_vi": "Curl"},
                {"id": 11, "movement_pattern": "h_pull", "name_vi": "Face"},
                {"id": 12, "movement_pattern": "h_push", "name_vi": "Fly"},
                {"id": 13, "movement_pattern": "v_push", "name_vi": "Lateral"},
            ],
        },
    ]


def test_upper_diversified_has_push_and_pull():
    picks = deterministic_picks(_upper_day_blocks(), split_role="upper")
    all_ids = picks.get("compound", []) + picks.get("accessory", [])
    meta = {}
    for b in _upper_day_blocks():
        for x in b["shortlist"]:
            meta[x["id"]] = x["movement_pattern"]
    fams = {family_of(meta[i]) for i in all_ids}
    assert "push" in fams
    assert "pull" in fams


def test_push_day_no_pull_preferred():
    blocks = [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 2,
            "is_optional": False,
            "shortlist": [
                {"id": 1, "movement_pattern": "h_push"},
                {"id": 2, "movement_pattern": "v_push"},
                {"id": 3, "movement_pattern": "h_pull"},
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
            ],
        },
    ]
    picks = deterministic_picks(blocks, split_role="push")
    meta = {1: "h_push", 2: "v_push", 3: "h_pull", 10: "h_push", 11: "v_push", 12: "h_pull"}
    for ids in picks.values():
        for eid in ids:
            assert family_of(meta[eid]) == "push"


def test_lower_covers_squat_and_hinge():
    blocks = [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 2,
            "is_optional": False,
            "shortlist": [
                {"id": 1, "movement_pattern": "squat"},
                {"id": 2, "movement_pattern": "hinge"},
                {"id": 3, "movement_pattern": "squat"},
            ],
        },
        {
            "block_key": "accessory",
            "pick": True,
            "count_max": 2,
            "is_optional": False,
            "shortlist": [
                {"id": 10, "movement_pattern": "squat"},
                {"id": 11, "movement_pattern": "hinge"},
            ],
        },
    ]
    picks = deterministic_picks(blocks, split_role="lower")
    all_ids = picks["compound"] + picks["accessory"]
    meta = {1: "squat", 2: "hinge", 3: "squat", 10: "squat", 11: "hinge"}
    fams = {family_of(meta[i]) for i in all_ids}
    assert "squat" in fams and "hinge" in fams


def test_repair_day_swaps_missing_push():
    blocks = _upper_day_blocks(compound_n=2, accessory_n=3)
    # All pull — should swap in a push from shortlist
    skewed = {"compound": [1, 2], "accessory": [10, 11, 4]}
    # id 4 is v_pull in compound shortlist; repair looks at both shortlists for candidates
    fixed = repair_day_coverage(blocks, skewed, split_role="upper")
    meta = {}
    for b in blocks:
        for x in b["shortlist"]:
            meta[x["id"]] = x["movement_pattern"]
    all_ids = fixed.get("compound", []) + fixed.get("accessory", [])
    fams = {family_of(meta[i]) for i in all_ids if i in meta}
    assert "push" in fams
    assert "pull" in fams


def test_missing_pull_catalog_no_crash():
    blocks = [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 2,
            "is_optional": False,
            "shortlist": [
                {"id": 1, "movement_pattern": "h_push"},
                {"id": 2, "movement_pattern": "v_push"},
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
            ],
        },
    ]
    picks = deterministic_picks(blocks, split_role="upper")
    assert picks["compound"]
    assert required_families("upper") == ("push", "pull")


def test_diversified_pick_round_robin():
    short = [
        {"id": 1, "movement_pattern": "h_pull"},
        {"id": 2, "movement_pattern": "h_pull"},
        {"id": 3, "movement_pattern": "h_push"},
    ]
    ids = diversified_pick(short, count=2, split_role="upper", block_key="compound")
    fams = {family_of(next(x["movement_pattern"] for x in short if x["id"] == i)) for i in ids}
    assert fams == {"push", "pull"}


def _pull_skewed_blocks(*, compound_n=2, accessory_n=4):
    """Many curls + few back + one rear-delt iso."""
    return [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": compound_n,
            "is_optional": False,
            "shortlist": [
                {"id": 1, "movement_pattern": "h_pull", "movement_role": "compound", "muscle": "co-lung"},
                {"id": 2, "movement_pattern": "v_pull", "movement_role": "compound", "muscle": "co-lung"},
                {"id": 3, "movement_pattern": "h_pull", "movement_role": "compound", "muscle": "co-lung"},
            ],
        },
        {
            "block_key": "accessory",
            "pick": True,
            "count_max": accessory_n,
            "is_optional": False,
            "shortlist": [
                {"id": 10, "movement_pattern": "h_pull", "movement_role": "isolation", "muscle": "co-tay-truoc"},
                {"id": 11, "movement_pattern": "h_pull", "movement_role": "isolation", "muscle": "co-tay-truoc"},
                {"id": 12, "movement_pattern": "h_pull", "movement_role": "isolation", "muscle": "co-tay-truoc"},
                {"id": 13, "movement_pattern": "h_pull", "movement_role": "isolation", "muscle": "co-tay-truoc"},
                {"id": 14, "movement_pattern": "h_pull", "movement_role": "isolation", "muscle": "co-vai"},
                {"id": 15, "movement_pattern": "h_pull", "movement_role": "isolation", "muscle": "co-lung"},
            ],
        },
    ]


def test_pull_muscle_quota_back_shoulder_biceps():
    from app.services.workout_generation.muscle_quotas import (
        _match_back,
        _match_biceps,
        _match_rear_delt,
    )

    picks = deterministic_picks(_pull_skewed_blocks(), split_role="pull")
    meta = {}
    for b in _pull_skewed_blocks():
        for x in b["shortlist"]:
            meta[x["id"]] = x
    all_ids = picks.get("compound", []) + picks.get("accessory", [])
    backs = sum(1 for i in all_ids if _match_back(meta[i]))
    rears = sum(1 for i in all_ids if _match_rear_delt(meta[i]))
    bis = sum(1 for i in all_ids if _match_biceps(meta[i]))
    assert backs >= 2
    assert bis >= 1
    assert rears <= 1


def test_pull_poor_slots_prioritize_back():
    from app.services.workout_generation.muscle_quotas import _match_back

    # 1 compound + 3 accessory = 4 slots; mins want 2+1+1
    picks = deterministic_picks(_pull_skewed_blocks(compound_n=1, accessory_n=3), split_role="pull")
    meta = {}
    for b in _pull_skewed_blocks():
        for x in b["shortlist"]:
            meta[x["id"]] = x
    all_ids = picks.get("compound", []) + picks.get("accessory", [])
    backs = sum(1 for i in all_ids if _match_back(meta[i]))
    assert backs >= 2
    assert len(all_ids) == 4


def test_push_muscle_quota_has_chest_not_back():
    from app.services.workout_generation.muscle_quotas import _match_back, _match_chest

    blocks = [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 2,
            "is_optional": False,
            "shortlist": [
                {"id": 1, "movement_pattern": "h_push", "movement_role": "compound", "muscle": "co-nguc"},
                {"id": 2, "movement_pattern": "v_push", "movement_role": "compound", "muscle": "co-vai"},
                {"id": 3, "movement_pattern": "h_pull", "movement_role": "compound", "muscle": "co-lung"},
            ],
        },
        {
            "block_key": "accessory",
            "pick": True,
            "count_max": 3,
            "is_optional": False,
            "shortlist": [
                {"id": 10, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "co-nguc"},
                {"id": 11, "movement_pattern": "v_push", "movement_role": "isolation", "muscle": "co-vai"},
                {"id": 12, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "co-tay-sau"},
                {"id": 13, "movement_pattern": "h_pull", "movement_role": "isolation", "muscle": "co-lung"},
            ],
        },
    ]
    picks = deterministic_picks(blocks, split_role="push")
    meta = {}
    for b in blocks:
        for x in b["shortlist"]:
            meta[x["id"]] = x
    all_ids = picks["compound"] + picks["accessory"]
    assert sum(1 for i in all_ids if _match_chest(meta[i])) >= 2
    assert sum(1 for i in all_ids if _match_back(meta[i])) == 0


def test_repair_push_swaps_third_triceps_for_chest_or_shoulder():
    from app.services.workout_generation.muscle_quotas import (
        _match_chest,
        _match_push_shoulder,
        _match_triceps,
        repair_muscle_quotas,
    )

    blocks = [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 2,
            "shortlist": [
                {"id": 1, "movement_pattern": "h_push", "movement_role": "compound", "muscle": "chest"},
                {"id": 2, "movement_pattern": "v_push", "movement_role": "compound", "muscle": "shoulders-front"},
            ],
        },
        {
            "block_key": "accessory",
            "pick": True,
            "count_max": 3,
            "shortlist": [
                {"id": 20, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
                {"id": 21, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
                {"id": 22, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
                {"id": 10, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "chest-mid"},
                {
                    "id": 11,
                    "movement_pattern": "other",
                    "movement_role": "isolation",
                    "muscle": "shoulders-lateral",
                },
            ],
        },
    ]
    out = repair_muscle_quotas(
        blocks,
        {"compound": [1, 2], "accessory": [20, 21, 22]},
        split_role="push",
    )
    meta = {x["id"]: x for b in blocks for x in b["shortlist"]}
    ids = out["compound"] + out["accessory"]
    chest = sum(1 for i in ids if _match_chest(meta[i]))
    sh = sum(1 for i in ids if _match_push_shoulder(meta[i]))
    tri = sum(1 for i in ids if _match_triceps(meta[i]))
    assert chest >= 2
    assert sh >= 1
    assert tri <= 2
    assert chest + sh + tri == 5
    assert (chest, sh, tri) in {(2, 2, 1), (2, 1, 2)}


def test_allocate_five_lift_push_is_two_chest_not_three_triceps():
    from app.services.workout_generation.muscle_quotas import allocate_muscle_quotas

    pool = [
        {"id": 1, "movement_pattern": "h_push", "movement_role": "compound", "muscle": "chest"},
        {"id": 3, "movement_pattern": "v_push", "movement_role": "compound", "muscle": "shoulders"},
        {"id": 10, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "chest"},
        {
            "id": 11,
            "movement_pattern": "other",
            "movement_role": "isolation",
            "muscle": "shoulders-lateral",
        },
        {"id": 20, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
        {"id": 21, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
        {"id": 22, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
    ]
    c, a = allocate_muscle_quotas("push", pool, compound_n=2, accessory_n=3)
    picked = {x["id"]: x for x in pool if x["id"] in set(c + a)}
    chest = sum(1 for x in picked.values() if str(x["muscle"]).startswith("chest"))
    tri = sum(1 for x in picked.values() if x["muscle"] == "triceps")
    assert len(c + a) == 5
    assert chest >= 2
    assert tri <= 2


def test_lateral_raise_counts_as_push_shoulder():
    from app.services.workout_generation.muscle_quotas import _match_push_shoulder

    raise_ = {
        "id": 11,
        "movement_pattern": "other",
        "movement_role": "isolation",
        "muscle": "shoulders-lateral",
    }
    face_pull = {
        "id": 12,
        "movement_pattern": "h_pull",
        "movement_role": "isolation",
        "muscle": "shoulders-rear",
    }
    assert _match_push_shoulder(raise_)
    assert not _match_push_shoulder(face_pull)


def test_allocate_muscle_quotas_direct():
    from app.services.workout_generation.muscle_quotas import allocate_muscle_quotas

    pool = [
        {"id": 1, "movement_pattern": "squat", "movement_role": "compound", "muscle": "co-dui-truoc"},
        {"id": 2, "movement_pattern": "hinge", "movement_role": "compound", "muscle": "co-dui-sau"},
        {"id": 3, "movement_pattern": "squat", "movement_role": "isolation", "muscle": "co-dui-truoc"},
        {"id": 4, "movement_pattern": "hinge", "movement_role": "isolation", "muscle": "co-mong"},
        {"id": 5, "movement_pattern": "other", "movement_role": "isolation", "muscle": "co-bap-chan"},
    ]
    c, a = allocate_muscle_quotas("legs", pool, compound_n=2, accessory_n=3)
    all_ids = c + a
    assert 1 in all_ids or 3 in all_ids
    assert 2 in all_ids or 4 in all_ids


def test_allocate_muscle_quotas_canonical_en_slugs():
    from app.services.workout_generation.muscle_quotas import (
        _match_hinge_post,
        _match_squat_quad,
        allocate_muscle_quotas,
    )

    pool = [
        {"id": 1, "movement_pattern": "squat", "movement_role": "compound", "muscle": "quads"},
        {"id": 2, "movement_pattern": "hinge", "movement_role": "compound", "muscle": "hamstrings"},
        {"id": 3, "movement_pattern": "hinge", "movement_role": "isolation", "muscle": "glutes"},
        {"id": 4, "movement_pattern": "squat", "movement_role": "isolation", "muscle": "quads"},
        {"id": 5, "movement_pattern": "other", "movement_role": "isolation", "muscle": "calves"},
    ]
    assert _match_squat_quad(pool[0])
    assert _match_hinge_post(pool[1])
    assert _match_hinge_post(pool[2])
    c, a = allocate_muscle_quotas("legs", pool, compound_n=2, accessory_n=3)
    all_ids = c + a
    assert 1 in all_ids or 4 in all_ids
    assert 2 in all_ids or 3 in all_ids


def test_match_hinge_post_includes_hamstring_curl():
    from app.services.workout_generation.muscle_quotas import _match_hinge_post

    curl = {
        "id": 9,
        "movement_pattern": "other",
        "movement_role": "isolation",
        "muscle": "hamstrings",
    }
    calf = {
        "id": 10,
        "movement_pattern": "other",
        "movement_role": "isolation",
        "muscle": "calves",
    }
    assert _match_hinge_post(curl)
    assert not _match_hinge_post(calf)


def test_allocate_push_respects_triceps_max_on_long_session():
    from app.services.workout_generation.muscle_quotas import allocate_muscle_quotas

    pool = [
        {"id": 1, "movement_pattern": "h_push", "movement_role": "compound", "muscle": "chest"},
        {"id": 2, "movement_pattern": "h_push", "movement_role": "compound", "muscle": "chest"},
        {"id": 3, "movement_pattern": "v_push", "movement_role": "compound", "muscle": "shoulders"},
        {"id": 4, "movement_pattern": "h_push", "movement_role": "compound", "muscle": "chest"},
        {"id": 10, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "chest"},
        {"id": 11, "movement_pattern": "v_push", "movement_role": "isolation", "muscle": "shoulders"},
        {"id": 20, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
        {"id": 21, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
        {"id": 22, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
        {"id": 23, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
    ]
    c, a = allocate_muscle_quotas("push", pool, compound_n=3, accessory_n=4)
    picked = {x["id"]: x for x in pool if x["id"] in set(c + a)}
    tri = sum(1 for x in picked.values() if x["muscle"] == "triceps")
    chest = sum(1 for x in picked.values() if x["muscle"] == "chest")
    assert chest >= 2
    assert tri <= 2
    assert len(c + a) == 7


def test_allocate_push_orders_chest_then_shoulders_then_triceps():
    from app.services.workout_generation.muscle_quotas import allocate_muscle_quotas

    pool = [
        {"id": 1, "movement_pattern": "h_push", "movement_role": "compound", "muscle": "chest"},
        {"id": 2, "movement_pattern": "h_push", "movement_role": "compound", "muscle": "chest"},
        {"id": 3, "movement_pattern": "v_push", "movement_role": "compound", "muscle": "shoulders"},
        {"id": 10, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "chest"},
        {"id": 11, "movement_pattern": "v_push", "movement_role": "isolation", "muscle": "shoulders"},
        {"id": 12, "movement_pattern": "v_push", "movement_role": "isolation", "muscle": "shoulders"},
        {"id": 20, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
        {"id": 21, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
    ]
    c, a = allocate_muscle_quotas("push", pool, compound_n=3, accessory_n=4)
    meta = {x["id"]: x for x in pool}
    seq = c + a
    muscles = [meta[i]["muscle"] for i in seq]

    def first(m: str) -> int:
        return next(i for i, x in enumerate(muscles) if x == m)

    def last(m: str) -> int:
        return max(i for i, x in enumerate(muscles) if x == m)

    assert first("chest") < first("shoulders") < first("triceps")
    assert last("chest") < first("triceps")
    assert last("shoulders") < first("triceps")


def test_reorder_main_puts_triceps_after_shoulders():
    from app.schemas.plans import PlanExerciseIn
    from app.services.workout_generation.muscle_quotas import reorder_main_section_exercises

    exercises = [
        PlanExerciseIn(exercise_id=1, section="warmup", sort_order=1),
        PlanExerciseIn(exercise_id=10, section="main", sort_order=2),
        PlanExerciseIn(exercise_id=20, section="main", sort_order=3),
        PlanExerciseIn(exercise_id=21, section="main", sort_order=4),
        PlanExerciseIn(exercise_id=11, section="main", sort_order=5),
        PlanExerciseIn(exercise_id=12, section="main", sort_order=6),
        PlanExerciseIn(exercise_id=99, section="cardio", sort_order=7),
        PlanExerciseIn(exercise_id=2, section="cooldown", sort_order=8),
    ]
    meta = {
        10: {"id": 10, "movement_pattern": "h_push", "movement_role": "compound", "muscle": "chest"},
        20: {"id": 20, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
        21: {"id": 21, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
        11: {"id": 11, "movement_pattern": "v_push", "movement_role": "isolation", "muscle": "shoulders"},
        12: {"id": 12, "movement_pattern": "v_push", "movement_role": "isolation", "muscle": "shoulders"},
    }
    out = reorder_main_section_exercises("push", exercises, meta)
    main_ids = [e.exercise_id for e in out if e.section == "main"]
    assert main_ids == [10, 11, 12, 20, 21]
    assert [e.exercise_id for e in out[:1]] == [1]
    assert [e.exercise_id for e in out[-2:]] == [99, 2]


def test_reorder_main_compounds_before_isolation():
    from app.schemas.plans import PlanExerciseIn
    from app.services.workout_generation.muscle_quotas import reorder_main_section_exercises

    exercises = [
        PlanExerciseIn(exercise_id=1, section="warmup", sort_order=1),
        PlanExerciseIn(exercise_id=10, section="main", sort_order=2),
        PlanExerciseIn(exercise_id=13, section="main", sort_order=3),
        PlanExerciseIn(exercise_id=3, section="main", sort_order=4),
        PlanExerciseIn(exercise_id=20, section="main", sort_order=5),
        PlanExerciseIn(exercise_id=2, section="cooldown", sort_order=6),
    ]
    meta = {
        10: {"id": 10, "movement_pattern": "h_push", "movement_role": "compound", "muscle": "chest"},
        13: {"id": 13, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "chest"},
        3: {"id": 3, "movement_pattern": "v_push", "movement_role": "compound", "muscle": "shoulders"},
        20: {"id": 20, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
    }
    out = reorder_main_section_exercises("push", exercises, meta)
    main_ids = [e.exercise_id for e in out if e.section == "main"]
    assert main_ids == [10, 13, 3, 20]
    assert [e.exercise_id for e in out[:1]] == [1]
    assert [e.exercise_id for e in out[-1:]] == [2]


def test_reorder_legs_calf_last_among_main():
    from app.schemas.plans import PlanExerciseIn
    from app.services.workout_generation.muscle_quotas import reorder_main_section_exercises

    exercises = [
        PlanExerciseIn(exercise_id=1, section="warmup", sort_order=1),
        PlanExerciseIn(exercise_id=10, section="main", sort_order=2),
        PlanExerciseIn(exercise_id=40, section="main", sort_order=3),
        PlanExerciseIn(exercise_id=20, section="main", sort_order=4),
        PlanExerciseIn(exercise_id=30, section="main", sort_order=5),
        PlanExerciseIn(exercise_id=99, section="cardio", sort_order=6),
        PlanExerciseIn(exercise_id=2, section="cooldown", sort_order=7),
    ]
    meta = {
        10: {
            "id": 10,
            "movement_pattern": "squat",
            "movement_role": "compound",
            "muscle": "quads",
        },
        40: {
            "id": 40,
            "movement_pattern": "other",
            "movement_role": "isolation",
            "muscle": "calves",
            "name_vi": "Nâng bắp chân",
            "name_en": "Calf raise",
        },
        20: {
            "id": 20,
            "movement_pattern": "other",
            "movement_role": "isolation",
            "muscle": "hamstrings",
        },
        30: {
            "id": 30,
            "movement_pattern": "other",
            "movement_role": "isolation",
            "muscle": "quads",
        },
    }
    out = reorder_main_section_exercises("legs", exercises, meta)
    main_ids = [e.exercise_id for e in out if e.section == "main"]
    assert main_ids[-1] == 40
    assert 40 not in main_ids[:-1]
    assert [e.exercise_id for e in out[:1]] == [1]
    assert [e.exercise_id for e in out[-2:]] == [99, 2]


def test_reorder_legs_extra_after_cooldown_calf_last_before_cardio():
    from app.schemas.plans import PlanExerciseIn
    from app.services.workout_generation.muscle_quotas import reorder_main_section_exercises

    exercises = [
        PlanExerciseIn(exercise_id=1, section="warmup", sort_order=1),
        PlanExerciseIn(exercise_id=10, section="main", sort_order=2),
        PlanExerciseIn(exercise_id=20, section="main", sort_order=3),
        PlanExerciseIn(exercise_id=40, section="main", sort_order=4),
        PlanExerciseIn(exercise_id=99, section="cardio", sort_order=5),
        PlanExerciseIn(exercise_id=2, section="cooldown", sort_order=6),
        PlanExerciseIn(exercise_id=50, section="main", sort_order=7),
    ]
    meta = {
        10: {
            "id": 10,
            "movement_pattern": "squat",
            "movement_role": "compound",
            "muscle": "quads",
        },
        20: {
            "id": 20,
            "movement_pattern": "hinge",
            "movement_role": "isolation",
            "muscle": "hamstrings",
        },
        40: {
            "id": 40,
            "movement_pattern": "other",
            "movement_role": "isolation",
            "muscle": "calves",
            "name_vi": "Nhón bắp chân đứng máy",
            "name_en": "Standing Calf Raise",
        },
        50: {
            "id": 50,
            "movement_pattern": "hinge",
            "movement_role": "isolation",
            "muscle": "glutes",
            "name_vi": "Kéo cáp qua háng",
            "name_en": "Cable Pull Through",
        },
    }
    out = reorder_main_section_exercises("lower", exercises, meta)
    main_ids = [e.exercise_id for e in out if e.section == "main"]
    assert 50 in main_ids
    assert main_ids[-1] == 40
    assert 40 not in main_ids[:-1]
    sections = [e.section for e in out]
    cardio_i = sections.index("cardio")
    cooldown_i = sections.index("cooldown")
    extra_i = next(i for i, e in enumerate(out) if e.exercise_id == 50)
    calf_i = next(i for i, e in enumerate(out) if e.exercise_id == 40)
    assert extra_i < cardio_i < cooldown_i
    assert calf_i == cardio_i - 1
    assert extra_i < calf_i


def test_reorder_push_chest_then_shoulders_then_triceps():
    from app.schemas.plans import PlanExerciseIn
    from app.services.workout_generation.muscle_quotas import reorder_main_section_exercises

    exercises = [
        PlanExerciseIn(exercise_id=1, section="warmup", sort_order=1),
        PlanExerciseIn(exercise_id=20, section="main", sort_order=2),
        PlanExerciseIn(exercise_id=12, section="main", sort_order=3),
        PlanExerciseIn(exercise_id=10, section="main", sort_order=4),
        PlanExerciseIn(exercise_id=3, section="main", sort_order=5),
        PlanExerciseIn(exercise_id=13, section="main", sort_order=6),
        PlanExerciseIn(exercise_id=2, section="cooldown", sort_order=7),
    ]
    meta = {
        10: {"id": 10, "movement_pattern": "h_push", "movement_role": "compound", "muscle": "chest"},
        13: {"id": 13, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "chest"},
        3: {"id": 3, "movement_pattern": "v_push", "movement_role": "compound", "muscle": "shoulders"},
        12: {"id": 12, "movement_pattern": "v_push", "movement_role": "isolation", "muscle": "shoulders"},
        20: {"id": 20, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
    }
    out = reorder_main_section_exercises("push", exercises, meta)
    main_ids = [e.exercise_id for e in out if e.section == "main"]
    assert main_ids == [10, 13, 3, 12, 20]


def test_allocate_push_slots_chest_and_ohp():
    from app.services.workout_generation.muscle_quotas import allocate_muscle_quotas

    pool = [
        {"id": 1, "movement_pattern": "h_push", "movement_role": "compound", "muscle": "chest"},
        {"id": 2, "movement_pattern": "h_push", "movement_role": "compound", "muscle": "chest"},
        {"id": 3, "movement_pattern": "v_push", "movement_role": "compound", "muscle": "shoulders"},
        {"id": 10, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "chest"},
        {"id": 20, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
    ]
    c, a = allocate_muscle_quotas("push", pool, compound_n=2, accessory_n=2)
    meta = {x["id"]: x for x in pool}
    assert {meta[i]["movement_pattern"] for i in c} == {"h_push", "v_push"}
    assert 20 in a
    assert 10 in a


def test_allocate_upper_avoids_h_push_after_push_day():
    from app.services.workout_generation.muscle_quotas import allocate_muscle_quotas

    pool = [
        {"id": 1, "movement_pattern": "h_push", "movement_role": "compound", "muscle": "chest"},
        {"id": 3, "movement_pattern": "h_pull", "movement_role": "compound", "muscle": "back"},
        {"id": 4, "movement_pattern": "v_pull", "movement_role": "compound", "muscle": "back"},
        {"id": 5, "movement_pattern": "v_push", "movement_role": "compound", "muscle": "shoulders"},
        {"id": 10, "movement_pattern": "other", "movement_role": "isolation", "muscle": "biceps"},
        {"id": 11, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
    ]
    c, a = allocate_muscle_quotas(
        "upper",
        pool,
        compound_n=2,
        accessory_n=2,
        avoid_compound_patterns=frozenset({"h_push"}),
    )
    assert 1 not in c
    assert 3 in c
    assert 1 not in c + a or 1 in a


def test_allocate_biceps_other_pattern_on_pull():
    from app.services.workout_generation.muscle_quotas import allocate_muscle_quotas

    pool = [
        {"id": 1, "movement_pattern": "v_pull", "movement_role": "compound", "muscle": "back"},
        {"id": 2, "movement_pattern": "h_pull", "movement_role": "compound", "muscle": "back"},
        {"id": 3, "movement_pattern": "v_pull", "movement_role": "compound", "muscle": "back"},
        {"id": 10, "movement_pattern": "other", "movement_role": "isolation", "muscle": "biceps"},
        {"id": 11, "movement_pattern": "h_pull", "movement_role": "isolation", "muscle": "shoulders"},
        {"id": 12, "movement_pattern": "h_pull", "movement_role": "isolation", "muscle": "shoulders"},
    ]
    c, a = allocate_muscle_quotas("pull", pool, compound_n=2, accessory_n=2)
    assert 10 in c + a
    assert sum(1 for i in c + a if i in {11, 12}) <= 1


def test_allocate_legs_rejects_laterals():
    from app.services.workout_generation.muscle_quotas import allocate_muscle_quotas

    pool = [
        {"id": 1, "movement_pattern": "squat", "movement_role": "compound", "muscle": "quads"},
        {"id": 2, "movement_pattern": "hinge", "movement_role": "compound", "muscle": "hamstrings"},
        {"id": 3, "movement_pattern": "squat", "movement_role": "isolation", "muscle": "quads"},
        {"id": 4, "movement_pattern": "v_push", "movement_role": "isolation", "muscle": "shoulders"},
        {"id": 5, "movement_pattern": "other", "movement_role": "isolation", "muscle": "calves"},
    ]
    c, a = allocate_muscle_quotas("legs", pool, compound_n=2, accessory_n=2)
    assert 4 not in c + a
    assert 1 in c + a
    assert 2 in c + a


def test_upper_quota_has_horizontal_push_and_pull():
    from app.services.workout_generation.muscle_quotas import allocate_muscle_quotas

    pool = [
        {"id": 1, "movement_pattern": "v_push", "movement_role": "compound", "muscle": "shoulders"},
        {"id": 2, "movement_pattern": "v_push", "movement_role": "compound", "muscle": "shoulders"},
        {"id": 3, "movement_pattern": "h_push", "movement_role": "compound", "muscle": "chest"},
        {"id": 4, "movement_pattern": "h_pull", "movement_role": "compound", "muscle": "back"},
        {"id": 5, "movement_pattern": "v_push", "movement_role": "isolation", "muscle": "shoulders"},
        {"id": 6, "movement_pattern": "other", "movement_role": "isolation", "muscle": "biceps"},
    ]
    c, a = allocate_muscle_quotas("upper", pool, compound_n=2, accessory_n=3)
    picked = set(c + a)
    assert 3 in picked
    assert 4 in picked
    assert sum(1 for i in picked if i in {1, 2}) <= 1


def test_upper_anchors_pull_not_second_press():
    from app.services.workout_generation.muscle_quotas import allocate_muscle_quotas

    pool = [
        {"id": 1, "movement_pattern": "h_push", "movement_role": "compound", "muscle": "chest"},
        {"id": 2, "movement_pattern": "h_push", "movement_role": "compound", "muscle": "chest"},
        {"id": 3, "movement_pattern": "h_pull", "movement_role": "compound", "muscle": "back"},
        {"id": 10, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
        {"id": 11, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
        {"id": 12, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
        {"id": 13, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
        {"id": 14, "movement_pattern": "other", "movement_role": "isolation", "muscle": "biceps"},
    ]
    c, a = allocate_muscle_quotas(
        "upper",
        pool,
        compound_n=2,
        accessory_n=4,
        focus_slugs=frozenset({"biceps", "triceps"}),
    )
    assert 3 in c
    assert 1 in c or 2 in c
    tri = sum(1 for i in c + a if i in {10, 11, 12, 13})
    assert tri <= 1
    assert 14 in c + a


def test_upper_h_push_bucket_does_not_take_triceps_first():
    from app.services.workout_generation.muscle_quotas import allocate_muscle_quotas

    pool = [
        {"id": 10, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
        {"id": 11, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
        {"id": 12, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
        {"id": 1, "movement_pattern": "h_push", "movement_role": "compound", "muscle": "chest"},
        {"id": 3, "movement_pattern": "h_pull", "movement_role": "compound", "muscle": "back"},
        {"id": 14, "movement_pattern": "other", "movement_role": "isolation", "muscle": "biceps"},
    ]
    c, a = allocate_muscle_quotas("upper", pool, compound_n=2, accessory_n=4)
    assert 1 in c
    assert 3 in c
    tri = sum(1 for i in c + a if i in {10, 11, 12})
    assert tri <= 1


def test_keep_outside_preferred_pattern_push_chest_fly():
    from app.services.workout_generation.muscle_quotas import keep_outside_preferred_pattern

    assert keep_outside_preferred_pattern("push", muscle_slug="chest", pattern="other")
    assert keep_outside_preferred_pattern("push", muscle_slug="triceps", pattern="other")
    assert keep_outside_preferred_pattern("push", muscle_slug="shoulders", pattern="other")
    assert not keep_outside_preferred_pattern("push", muscle_slug="biceps", pattern="other")
    assert keep_outside_preferred_pattern("pull", muscle_slug="biceps", pattern="other")
    assert keep_outside_preferred_pattern("legs", muscle_slug="quads", pattern="other")
    assert keep_outside_preferred_pattern("lower", muscle_slug="glutes", pattern="other")
    assert keep_outside_preferred_pattern("upper", muscle_slug="chest", pattern="other")


def test_narrow_accessory_keeps_isolation_other_when_pool_thin():
    from app.services.workout_generation.shortlist import ShortlistItem, narrow_preferred_shortlist
    from app.services.workout_generation.split_map import patterns_for_split

    def item(eid: int, pattern: str, muscle: str) -> ShortlistItem:
        return ShortlistItem(
            id=eid,
            name_vi=str(eid),
            movement_role="isolation",
            movement_pattern=pattern,
            muscle_slug=muscle,
            difficulty=2,
        )

    scored = [
        (0, item(1, "h_push", "chest")),
        (0, item(2, "h_push", "chest")),
        (0, item(3, "v_push", "shoulders")),
        (0, item(4, "other", "chest")),
    ]
    out = narrow_preferred_shortlist(
        scored,
        block_key="accessory",
        preferred_patterns=patterns_for_split("push"),
        split_role="push",
        count_max=4,
    )
    ids = {it.id for _, it in out}
    assert 4 in ids
    assert {1, 2, 3, 4} <= ids


def test_narrow_accessory_keeps_fly_when_preferred_pool_is_large():
    from app.services.workout_generation.shortlist import ShortlistItem, narrow_preferred_shortlist
    from app.services.workout_generation.split_map import patterns_for_split

    def item(eid: int, pattern: str, muscle: str) -> ShortlistItem:
        return ShortlistItem(
            id=eid,
            name_vi=str(eid),
            movement_role="isolation",
            movement_pattern=pattern,
            muscle_slug=muscle,
            difficulty=2,
        )

    scored = [(0, item(i, "h_push", "chest")) for i in range(1, 12)]
    scored.append((0, item(99, "other", "chest")))
    out = narrow_preferred_shortlist(
        scored,
        block_key="accessory",
        preferred_patterns=patterns_for_split("push"),
        split_role="push",
        count_max=4,
    )
    ids = {it.id for _, it in out}
    assert 99 in ids
    assert len(ids) >= 8


def test_wizard_inputs_recap_is_short_and_has_user_choices():
    from app.services.workout_generation.service import build_wizard_inputs

    data = build_wizard_inputs(
        {
            "gender": "male",
            "age": 28,
            "height_cm": 170,
            "weight_kg": 70,
            "activity": "moderate",
        },
        goal="lose_weight",
        location="home",
        sessions=3,
        session_minutes=60,
        duration_weeks=14,
        experience_level=1,
        no_equipment=True,
        equipment_list=[],
        focus_labels=["mông"],
    )
    recap = data["recap_vi"]
    assert "Nam" in recap
    assert "Nhà" in recap
    assert "không dụng cụ" in recap.lower()
    assert "3 buổi/tuần" in recap
    assert "60 phút" in recap
    assert "Master" not in recap
    assert "LISS" not in recap
    assert "Giảm cân" in data["chips"]
    assert "Ưu tiên: mông" in recap
