"""Home-with-gear implement coverage."""

import pytest

from app.schemas.plans import PlanDayIn, PlanExerciseIn
from app.services.workout_generation.home_implements import (
    apply_home_implement_coverage,
    classify_home_implement,
    _preferred_implement_for_day,
)
from app.services.workout_generation.session_policy import resolve_session_policy
from app.services.workout_generation.shortlist import (
    is_hiit_cardio_name,
    is_home_denied_exercise,
    is_home_improvised_exercise,
    is_jump_rope_name,
    score_candidate,
)
from app.services.workout_generation.split_map import muscle_hints_for_split, patterns_for_split
from app.services.workout_generation.capacity import resolve_capacity


def _ex(eid: int) -> PlanExerciseIn:
    return PlanExerciseIn(exercise_id=eid, section="main")


def test_back_extension_bench_denied_from_schedule_gen():
    common = dict(location="home", no_equipment=False, user_slugs=["dumbbell"])
    assert is_home_denied_exercise(
        name_en="Back Extension",
        name_vi="Duỗi lưng ghế 45 độ",
        **common,
    )
    assert not is_home_denied_exercise(
        name_en="Dumbbell Back Extension",
        name_vi="Duỗi lưng với tạ đơn",
        **common,
    )
    assert not is_home_denied_exercise(
        name_en="Machine 45 Degree Back Extension",
        name_vi="Duỗi lưng máy 45 độ",
        **common,
    )


def test_retired_band_pushup_and_face_pull_denied_at_home():
    common = dict(location="home", no_equipment=False, user_slugs=["resistance-band-2"])
    assert is_home_denied_exercise(
        name_en="Band Push-Up",
        name_vi="Chống đẩy với dây kháng lực",
        **common,
    )
    assert is_home_denied_exercise(
        name_en="Band Face Pull",
        name_vi="Kéo mặt với dây kháng lực",
        **common,
    )


def test_band_row_allowed_when_user_has_band():
    assert not is_home_denied_exercise(
        name_en="Band Row",
        name_vi="Chèo dây",
        location="home",
        no_equipment=False,
        user_slugs=["resistance-band-2"],
    )
    assert not is_home_denied_exercise(
        name_vi="Kéo ngang dây",
        location="home",
        no_equipment=False,
        user_slugs=["resistance-band"],
    )
    assert not is_home_denied_exercise(
        name_en="Face Pull dây",
        location="home",
        no_equipment=False,
        user_slugs=["resistance-band-1"],
    )


def test_band_seated_pulldown_allowed_when_user_has_band():
    common = dict(location="home", no_equipment=False, user_slugs=["resistance-band-2"])
    assert not is_home_denied_exercise(
        name_en="Band Seated Pulldown",
        name_vi="Kéo xô ngồi với dây kháng lực",
        **common,
    )
    assert not is_home_denied_exercise(
        name_en="Band Seated Pulldown",
        name_vi="Kéo xà ngồi với dây kháng lực",
        **common,
    )
    assert is_home_denied_exercise(
        name_en="Band Seated Pulldown",
        name_vi="Kéo xà ngồi với dây kháng lực",
        location="home",
        no_equipment=True,
    )


def test_band_row_denied_without_band_or_no_equip():
    assert is_home_denied_exercise(
        name_en="Band Row",
        name_vi="Chèo dây",
        location="home",
        no_equipment=True,
    )
    assert is_home_denied_exercise(
        name_en="Band Row",
        location="home",
        no_equipment=False,
        user_slugs=["dumbbell"],
    )


def test_captains_chair_knee_raise_denied_without_gear():
    assert is_home_denied_exercise(
        name_en="Captain's Chair Knee Raise",
        name_vi="Nâng đầu gối trên ghế Captain",
        location="home",
        no_equipment=True,
    )
    assert is_home_denied_exercise(
        name_en="Captain's Chair Knee Raise",
        location="home",
        no_equipment=False,
        user_slugs=["dumbbell"],
    )
    assert not is_home_denied_exercise(
        name_en="Captain's Chair Knee Raise",
        location="home",
        no_equipment=False,
        user_slugs=["parallel-bars"],
    )
    assert not is_home_denied_exercise(
        name_en="Captain's Chair Knee Raise",
        location="gym",
        no_equipment=False,
    )


def test_inverted_and_gym_rows_still_denied_at_home():
    assert is_home_denied_exercise(
        name_en="Inverted row",
        location="home",
        no_equipment=False,
        user_slugs=["resistance-band-2"],
    )
    assert is_home_denied_exercise(
        name_en="Seated Cable Row",
        location="home",
        no_equipment=False,
        user_slugs=["resistance-band-2"],
    )
    assert is_home_denied_exercise(
        name_en="Barbell Row",
        name_vi="Chèo tạ đòn",
        location="home",
        no_equipment=False,
        user_slugs=["resistance-band-2", "dumbbell"],
    )


def test_improvised_home_rows_allowed_without_gear():
    for name_en, name_vi in (
        ("Towel Seated Row", "Kéo khăn ngồi"),
        ("Bent-Over Backpack Row", "Chèo ba lô cúi người"),
        ("Table Inverted Row", "Kéo người dưới bàn"),
        ("Table Edge Row", "Kéo mép bàn"),
    ):
        assert is_home_improvised_exercise(name_vi=name_vi, name_en=name_en)
        assert not is_home_denied_exercise(
            name_en=name_en,
            name_vi=name_vi,
            location="home",
            no_equipment=True,
        )


def test_bar_or_rings_denies_table_row_bar_inverted_and_backpack_gm():
    denied = (
        ("Pull-up Bar Inverted Row", "Kéo người nằm trên xà"),
        ("Table Inverted Row", "Kéo người dưới bàn"),
        ("Backpack Good Morning", "Cúi người ôm balo"),
        ("Ring Support Hold", "Giữ chống thẳng vòng treo"),
        ("Assisted Ring Dip", "Dip vòng có trợ"),
    )
    for slugs in (["pull-up-bar"], ["gymnastic-rings"], ["pull-up-bar", "gymnastic-rings"]):
        for name_en, name_vi in denied:
            assert is_home_denied_exercise(
                name_en=name_en,
                name_vi=name_vi,
                location="home",
                no_equipment=False,
                user_slugs=slugs,
            )
    assert not is_home_denied_exercise(
        name_en="Backpack Good Morning",
        name_vi="Cúi người ôm balo",
        location="home",
        no_equipment=True,
    )
    assert not is_home_denied_exercise(
        name_en="Ring Hold",
        name_vi="Giữ vòng treo",
        location="home",
        no_equipment=False,
        user_slugs=["gymnastic-rings"],
    )
    assert not is_home_denied_exercise(
        name_en="Ring Dip",
        name_vi="Dip vòng treo",
        location="home",
        no_equipment=False,
        user_slugs=["gymnastic-rings"],
        experience_level=1,
    )


def test_barbell_row_still_denied_at_home_no_equip():
    assert is_home_denied_exercise(
        name_en="Barbell Row",
        name_vi="Chèo tạ đòn",
        location="home",
        no_equipment=True,
    )


def test_home_score_penalizes_improvised_when_user_has_dumbbell():
    kw = dict(
        pattern="h_pull",
        muscle_slug="back",
        difficulty=2,
        movement_role="compound",
        venue="home",
        preferred_patterns=patterns_for_split("pull"),
        muscle_hints=muscle_hints_for_split("pull"),
        focus_slugs=None,
        allowed_diff=frozenset({1, 2, 3}),
        experience_level=2,
        block_role="resistance",
        block_key="resistance",
        location="home",
        user_slugs=["dumbbell"],
    )
    towel = score_candidate(
        equipment_slugs=set(),
        name_en="Towel Seated Row",
        name_vi="Kéo khăn ngồi",
        **kw,
    )
    db_row = score_candidate(
        equipment_slugs={"dumbbell"},
        name_en="Dumbbell Row",
        name_vi="Chèo tạ đơn",
        **kw,
    )
    assert db_row > towel


def test_classify_band1_legs_and_band2_back():
    assert (
        classify_home_implement(
            name_en="Band Row",
            name_vi="Chèo dây",
            equipment_slugs=["resistance-band"],
        )
        == "resistance-band-2"
    )
    assert (
        classify_home_implement(
            name_en="Band Squat",
            name_vi="Squat dây vòng",
            equipment_slugs=["resistance-band"],
        )
        == "resistance-band-2"
    )
    assert (
        classify_home_implement(
            name_en="Dumbbell Bench Press",
            equipment_slugs=["dumbbell"],
        )
        == "dumbbell"
    )
    assert (
        classify_home_implement(
            name_en="Band Curl",
            name_vi="Cuốn tay với dây",
            equipment_slugs=["resistance-band"],
        )
        is None
    )


def test_coverage_does_not_put_band_curl_on_push():
    push = PlanDayIn(day_number=1, split_role="push", exercises=[_ex(1), _ex(2)])
    meta = {
        1: {
            "name_en": "Push-up",
            "movement_role": "compound",
            "movement_pattern": "h_push",
            "muscle_slug": "chest",
        },
        2: {
            "name_en": "Band Chest Fly",
            "name_vi": "Ép ngực dây",
            "movement_role": "isolation",
            "movement_pattern": "other",
            "muscle_slug": "chest",
            "equipment_slugs": ["resistance-band"],
        },
        50: {
            "name_en": "Band Curl",
            "name_vi": "Cuốn tay với dây",
            "movement_role": "isolation",
            "movement_pattern": "other",
            "muscle_slug": "biceps",
            "equipment_slugs": ["resistance-band"],
        },
        10: {
            "name_en": "Band Row",
            "name_vi": "Chèo dây",
            "movement_role": "isolation",
            "muscle_slug": "back",
            "equipment_slugs": ["resistance-band"],
        },
    }
    out = apply_home_implement_coverage(
        [push],
        user_slugs=["resistance-band-2"],
        meta_by_id=meta,
        pools_by_day={1: [{"id": 50, **meta[50]}, {"id": 10, **meta[10]}]},
        location="home",
        no_equipment=False,
    )
    ids = [ex.exercise_id for ex in out[0].exercises]
    assert 50 not in ids
    assert 1 in ids


def test_coverage_pull_gets_band_row_legs_get_band_squat():
    pull = PlanDayIn(day_number=1, split_role="pull", exercises=[_ex(1), _ex(2)])
    legs = PlanDayIn(day_number=2, split_role="legs", exercises=[_ex(3), _ex(4)])
    meta = {
        1: {
            "name_en": "Dumbbell Bench Press",
            "movement_role": "compound",
            "movement_pattern": "h_push",
            "equipment_slugs": ["dumbbell"],
        },
        2: {
            "name_en": "Dumbbell Curl",
            "movement_role": "isolation",
            "movement_pattern": "other",
            "equipment_slugs": ["dumbbell"],
        },
        3: {
            "name_en": "Dumbbell Squat",
            "movement_role": "compound",
            "movement_pattern": "squat",
            "equipment_slugs": ["dumbbell"],
        },
        4: {
            "name_en": "Dumbbell Lunge",
            "movement_role": "isolation",
            "movement_pattern": "other",
            "equipment_slugs": ["dumbbell"],
        },
        10: {
            "name_en": "Band Row",
            "name_vi": "Chèo dây",
            "movement_role": "isolation",
            "equipment_slugs": ["resistance-band"],
        },
        20: {
            "name_en": "Band Squat",
            "name_vi": "Squat dây",
            "movement_role": "isolation",
            "equipment_slugs": ["resistance-band"],
        },
    }
    pools = {
        1: [
            {"id": 1, **meta[1]},
            {"id": 2, **meta[2]},
            {"id": 10, **meta[10]},
        ],
        2: [
            {"id": 3, **meta[3]},
            {"id": 4, **meta[4]},
            {"id": 20, **meta[20]},
        ],
    }
    out = apply_home_implement_coverage(
        [pull, legs],
        user_slugs=["dumbbell", "resistance-band-1", "resistance-band-2"],
        meta_by_id=meta,
        pools_by_day=pools,
        location="home",
        no_equipment=False,
    )
    pull_ids = [ex.exercise_id for ex in out[0].exercises]
    legs_ids = [ex.exercise_id for ex in out[1].exercises]
    assert 10 in pull_ids
    assert 1 in pull_ids
    assert 20 in legs_ids
    assert 3 in legs_ids


def test_home_score_boosts_band_when_user_has_band():
    kw = dict(
        pattern="h_pull",
        muscle_slug="back",
        difficulty=2,
        movement_role="isolation",
        venue="home",
        preferred_patterns=patterns_for_split("pull"),
        muscle_hints=muscle_hints_for_split("pull"),
        focus_slugs=None,
        allowed_diff=frozenset({1, 2}),
        experience_level=2,
        block_role="resistance",
        block_key="resistance",
        location="home",
    )
    band = score_candidate(
        equipment_slugs={"resistance-band"},
        name_en="Band Row",
        name_vi="Chèo dây",
        **kw,
    )
    db = score_candidate(
        equipment_slugs={"dumbbell"},
        name_en="Dumbbell Curl",
        name_vi="Cuốn tạ đơn",
        **kw,
    )
    assert band > db


def test_no_equip_conditioning_prefers_easy_zone2():
    kw = dict(
        pattern="other",
        muscle_slug="conditioning",
        difficulty=1,
        movement_role="conditioning",
        venue="home",
        equipment_slugs=set(),
        preferred_patterns=frozenset(),
        muscle_hints=frozenset(),
        focus_slugs=None,
        allowed_diff=frozenset({1, 2}),
        experience_level=1,
        block_role="conditioning",
        block_key="conditioning",
        location="home",
        goal="maintain",
        no_equipment=True,
        prefer_easy_cardio=True,
    )
    burpee = score_candidate(name_en="Burpee", name_vi="Burpee", **kw)
    climber = score_candidate(
        name_en="Mountain Climber", name_vi="Leo núi tại chỗ", **kw
    )
    jacks = score_candidate(name_en="Jumping Jack", name_vi="Nhảy jacks", **kw)
    walk = score_candidate(name_en="Walk", name_vi="Đi bộ", **kw)
    assert walk > burpee
    assert walk > climber
    assert walk > jacks


def test_hiit_cardio_name_helper_excludes_jump_rope():
    assert is_hiit_cardio_name(name_en="Burpee", name_vi="Burpee")
    assert is_hiit_cardio_name(name_en="Mountain Climber", name_vi="Leo núi tại chỗ")
    assert is_hiit_cardio_name(name_en="Jumping Jack", name_vi="Nhảy jacks")
    assert is_hiit_cardio_name(name_en="High Knees", name_vi="Gối cao")
    assert not is_hiit_cardio_name(name_en="Jump Rope", name_vi="Nhảy dây")
    assert is_jump_rope_name(name_en="Jump Rope", name_vi="Nhảy dây")
    assert not is_hiit_cardio_name(name_en="Walk", name_vi="Đi bộ")


def test_jump_rope_selected_beats_walk_on_conditioning():
    kw = dict(
        pattern="other",
        muscle_slug="conditioning",
        difficulty=1,
        movement_role="conditioning",
        venue="home",
        equipment_slugs={"jump-rope"},
        preferred_patterns=frozenset(),
        muscle_hints=frozenset(),
        focus_slugs=None,
        allowed_diff=frozenset({1, 2}),
        experience_level=1,
        block_role="conditioning",
        block_key="conditioning",
        location="home",
        goal="maintain",
        prefer_easy_cardio=True,
        user_slugs=["jump-rope"],
    )
    rope = score_candidate(
        name_en="Jump Rope", name_vi="Nhảy dây", **kw
    )
    walk = score_candidate(
        name_en="Walk",
        name_vi="Đi bộ",
        equipment_slugs=set(),
        **{k: v for k, v in kw.items() if k != "equipment_slugs"},
    )
    burpee = score_candidate(
        name_en="Burpee",
        name_vi="Burpee",
        equipment_slugs=set(),
        **{k: v for k, v in kw.items() if k != "equipment_slugs"},
    )
    assert rope > walk
    assert rope > burpee


def test_no_equip_policy_cardio_on_short_sessions():
    cap = resolve_capacity(2, None)
    home = resolve_session_policy(
        cap,
        goal="maintain",
        session_minutes=45,
        no_equipment=True,
        location="home",
    )
    gym = resolve_session_policy(
        cap, goal="maintain", session_minutes=45, location="gym"
    )
    assert home.cardio_on_lift_days is True
    assert gym.cardio_on_lift_days is False


def test_l1_home_denies_unassisted_pullup_and_dip():
    assert is_home_denied_exercise(
        name_en="Pull-Up",
        name_vi="Hít xà",
        location="home",
        no_equipment=False,
        user_slugs=["pull-up-bar"],
        experience_level=1,
        fitness_baseline={"pullups_max": 0},
    )
    assert is_home_denied_exercise(
        name_en="Bar Dip",
        name_vi="Dip xà kép",
        location="home",
        no_equipment=False,
        user_slugs=["parallel-bars"],
        experience_level=1,
    )
    assert not is_home_denied_exercise(
        name_en="Pull-Up",
        name_vi="Hít xà",
        location="home",
        no_equipment=False,
        user_slugs=["pull-up-bar"],
        experience_level=2,
    )
    assert not is_home_denied_exercise(
        name_en="Band-Assisted Pull-Up",
        name_vi="Hít xà trợ lực",
        location="home",
        no_equipment=False,
        user_slugs=["pull-up-bar", "resistance-band-2"],
        experience_level=1,
    )
    assert not is_home_denied_exercise(
        name_en="Inverted Row",
        name_vi="Chèo người nằm",
        location="home",
        no_equipment=False,
        user_slugs=["pull-up-bar"],
        experience_level=1,
    )


def test_coverage_jump_rope_swaps_conditioning():
    day = PlanDayIn(
        day_number=1,
        split_role="push",
        exercises=[
            _ex(1),
            PlanExerciseIn(exercise_id=2, section="cardio"),
        ],
    )
    meta = {
        1: {
            "name_en": "Push-Up",
            "movement_role": "resistance",
            "movement_pattern": "h_push",
        },
        2: {
            "name_en": "Walk",
            "name_vi": "Đi bộ",
            "movement_role": "conditioning",
        },
        30: {
            "name_en": "Jump Rope",
            "name_vi": "Nhảy dây",
            "movement_role": "conditioning",
            "equipment_slugs": ["jump-rope"],
        },
    }
    out = apply_home_implement_coverage(
        [day],
        user_slugs=["jump-rope"],
        meta_by_id=meta,
        pools_by_day={1: [{"id": 30, **meta[30]}]},
        location="home",
        no_equipment=False,
    )
    ids = [ex.exercise_id for ex in out[0].exercises]
    assert 30 in ids
    assert 2 not in ids


def test_coverage_l1_does_not_swap_in_raw_pullup():
    pull = PlanDayIn(day_number=1, split_role="pull", exercises=[_ex(1), _ex(2)])
    meta = {
        1: {
            "name_en": "Band Row",
            "name_vi": "Chèo dây",
            "movement_role": "compound",
            "movement_pattern": "h_pull",
            "muscle_slug": "back",
            "equipment_slugs": ["resistance-band"],
        },
        2: {
            "name_en": "Band Curl",
            "movement_role": "isolation",
            "movement_pattern": "other",
            "muscle_slug": "biceps",
            "equipment_slugs": ["resistance-band"],
        },
        9: {
            "name_en": "Pull-Up",
            "name_vi": "Hít xà",
            "movement_role": "compound",
            "movement_pattern": "v_pull",
            "muscle_slug": "back",
            "equipment_slugs": ["pull-up-bar"],
        },
    }
    out = apply_home_implement_coverage(
        [pull],
        user_slugs=["pull-up-bar", "resistance-band-2"],
        meta_by_id=meta,
        pools_by_day={1: [{"id": 9, **meta[9]}]},
        location="home",
        no_equipment=False,
        experience_level=1,
        fitness_baseline={"pullups_max": 0},
    )
    ids = [ex.exercise_id for ex in out[0].exercises]
    assert 9 not in ids
    assert 1 in ids


def test_rings_only_allows_ring_row_and_pullup_when_strong():
    rings = ["gymnastic-rings"]
    common = dict(
        location="home",
        no_equipment=False,
        user_slugs=rings,
        exercise_slugs=rings,
        experience_level=2,
    )
    assert not is_home_denied_exercise(
        name_vi="Chèo vòng treo",
        name_en="Ring Row",
        **common,
    )
    assert not is_home_denied_exercise(
        name_vi="Hít xà vòng treo",
        name_en="Ring Pull-Up",
        fitness_baseline={"pullups_max": 5},
        **common,
    )


def test_rings_weak_pullups_deny_pullup_allow_row():
    rings = ["gymnastic-rings"]
    common = dict(
        location="home",
        no_equipment=False,
        user_slugs=rings,
        exercise_slugs=rings,
        experience_level=2,
    )
    assert not is_home_denied_exercise(
        name_vi="Chèo vòng treo",
        name_en="Ring Row",
        fitness_baseline={"pullups_max": 2},
        **common,
    )
    assert is_home_denied_exercise(
        name_vi="Hít xà vòng treo",
        name_en="Ring Pull-Up",
        fitness_baseline={"pullups_max": 2},
        **common,
    )
    assert is_home_denied_exercise(
        name_vi="Hít xà vòng treo",
        name_en="Ring Pull-Up",
        fitness_baseline={"pullups_max": 0},
        **common,
    )
    # Missing pullups_max → do not assume weak.
    assert not is_home_denied_exercise(
        name_vi="Hít xà vòng treo",
        name_en="Ring Pull-Up",
        fitness_baseline={},
        **common,
    )


def test_rings_l1_denies_pullup_allows_row():
    rings = ["gymnastic-rings"]
    common = dict(
        location="home",
        no_equipment=False,
        user_slugs=rings,
        exercise_slugs=rings,
        experience_level=1,
        fitness_baseline={"pullups_max": 10},
    )
    assert not is_home_denied_exercise(
        name_vi="Hít xà vòng treo",
        name_en="Ring Pull-Up",
        **common,
    )
    assert not is_home_denied_exercise(
        name_vi="Chèo vòng treo",
        name_en="Ring Row",
        **common,
    )
    assert is_home_denied_exercise(
        name_vi="Hít xà vòng treo",
        name_en="Ring Pull-Up",
        location="home",
        no_equipment=False,
        user_slugs=rings,
        exercise_slugs=rings,
        experience_level=1,
        fitness_baseline={"pullups_max": 0},
    )
    assert not is_home_denied_exercise(
        name_vi="Hít xà vòng treo",
        name_en="Ring Pull-Up",
        location="home",
        no_equipment=False,
        user_slugs=rings,
        exercise_slugs=rings,
        experience_level=1,
    )


def test_rings_do_not_unlock_bare_bar_pullup_or_bb_row():
    assert is_home_denied_exercise(
        name_vi="Hít xà",
        name_en="Pull-Up",
        location="home",
        no_equipment=False,
        user_slugs=["gymnastic-rings"],
        experience_level=2,
        exercise_slugs=[],
    )
    assert is_home_denied_exercise(
        name_vi="Chèo tạ đòn",
        name_en="Barbell Row",
        location="home",
        no_equipment=False,
        user_slugs=["gymnastic-rings"],
        experience_level=2,
        exercise_slugs=["barbell"],
    )
    assert is_home_denied_exercise(
        name_vi="Chèo vòng treo",
        name_en="Ring Row",
        location="home",
        no_equipment=False,
        user_slugs=[],
        experience_level=2,
        exercise_slugs=["gymnastic-rings"],
    )


def test_classify_and_prefer_rings_on_pull_day():
    assert (
        classify_home_implement(
            name_vi="Hít xà vòng treo",
            name_en="Ring Pull-Up",
            equipment_slugs=["gymnastic-rings"],
        )
        == "gymnastic-rings"
    )
    assert (
        _preferred_implement_for_day(
            "pull", {"gymnastic-rings", "resistance-band-2"}
        )
        == "gymnastic-rings"
    )
    assert _preferred_implement_for_day("pull", {"resistance-band-2"}) == "resistance-band-2"


def test_must_include_pullup_at_five_with_rings():
    from app.services.workout_generation.skill_gate import must_include_pullup

    rings = ["gymnastic-rings"]
    assert must_include_pullup({"pullups_max": 5}, rings)
    assert not must_include_pullup({"pullups_max": 4}, rings)
    assert not must_include_pullup({"pullups_max": 8}, ["resistance-band-2"])
    assert must_include_pullup({}, rings)
    assert not must_include_pullup({"pullups_max": None}, rings)


def test_repair_pull_day_swaps_in_ring_pullup_when_test_ge_5():
    from app.schemas.plans import PlanDayIn, PlanExerciseIn
    from app.services.workout_generation.coverage import repair_plan_day_require_pullup

    day = PlanDayIn(
        day_number=1,
        split_role="pull",
        exercises=[
            PlanExerciseIn(exercise_id=1, section="main", sets=3, reps="8"),
        ],
    )
    meta = {
        1: {
            "name_vi": "Chèo vòng treo",
            "name_en": "Ring Row",
            "movement_role": "compound",
            "movement_pattern": "h_pull",
        },
        2: {
            "name_vi": "Hít xà vòng treo",
            "name_en": "Ring Pull-Up",
            "movement_role": "compound",
            "movement_pattern": "v_pull",
        },
    }
    candidates = [{"id": 2, **meta[2]}]
    assert repair_plan_day_require_pullup(
        day,
        candidates=candidates,
        meta_by_id=meta,
        fitness_baseline={"pullups_max": 5},
        equipment_slugs=["gymnastic-rings"],
    )
    assert day.exercises[0].exercise_id == 2
    weak = PlanDayIn(
        day_number=1,
        split_role="pull",
        exercises=[PlanExerciseIn(exercise_id=1, section="main", sets=3, reps="8")],
    )
    assert not repair_plan_day_require_pullup(
        weak,
        candidates=candidates,
        meta_by_id=meta,
        fitness_baseline={"pullups_max": 2},
        equipment_slugs=["gymnastic-rings"],
    )


def test_repair_full_body_day_also_requires_pullup():
    from app.schemas.plans import PlanDayIn, PlanExerciseIn
    from app.services.workout_generation.coverage import repair_plan_day_require_pullup

    day = PlanDayIn(
        day_number=1,
        split_role="fb_a",
        exercises=[
            PlanExerciseIn(exercise_id=1, section="main", sets=3, reps="8"),
        ],
    )
    meta = {
        1: {
            "name_vi": "Chèo vòng treo",
            "name_en": "Ring Row",
            "movement_role": "compound",
            "movement_pattern": "h_pull",
        },
        2: {
            "name_vi": "Hít xà vòng treo",
            "name_en": "Ring Pull-Up",
            "movement_role": "compound",
            "movement_pattern": "v_pull",
        },
    }
    assert repair_plan_day_require_pullup(
        day,
        candidates=[{"id": 2, **meta[2]}],
        meta_by_id=meta,
        fitness_baseline={"pullups_max": 6},
        equipment_slugs=["gymnastic-rings"],
    )
    assert day.exercises[0].exercise_id == 2
