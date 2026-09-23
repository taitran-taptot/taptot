"""Home-with-gear implement coverage + no-equip ULU / BW + HIIT."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import BadRequestError
from app.schemas.plans import PlanDayIn, PlanExerciseIn
from app.services.session_blocks import BlockSpec, get_master_session_recipe
from app.services.workout_generation.assemble import assemble_day
from app.services.workout_generation.home_implements import (
    apply_home_implement_coverage,
    classify_home_implement,
    _preferred_implement_for_day,
)
from app.services.workout_generation.session_policy import resolve_session_policy
from app.services.workout_generation.session_templates import slots_for_session
from app.services.workout_generation.shortlist import (
    ShortlistItem,
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
        == "resistance-band-1"
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


def test_home_no_equip_45_recipe_is_three_resistance_plus_conditioning():
    blocks = get_master_session_recipe(
        location="home",
        session_minutes=45,
        split_role="upper",
        no_equipment=True,
    )
    by = {b.block_key: b for b in blocks}
    assert by["resistance"].count_max == 3
    assert by["conditioning"].count_max == 2
    short = get_master_session_recipe(
        location="home",
        session_minutes=30,
        split_role="upper",
        no_equipment=True,
    )
    by_s = {b.block_key: b for b in short}
    assert by_s["resistance"].count_max == 2
    assert by_s["conditioning"].count_max == 2


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


def test_upper_no_equip_slots_skip_gym_pulls():
    bw = slots_for_session(
        "upper", compound_n=2, accessory_n=1, location="home", no_equipment=True
    )
    keys = [s.key for s in bw]
    assert "v_pull" not in keys
    assert "h_pull" not in keys
    assert "h_press" in keys
    gym = slots_for_session(
        "upper", compound_n=2, accessory_n=1, location="gym", no_equipment=False
    )
    gym_keys = [s.key for s in gym]
    assert "v_pull" in gym_keys or "h_pull" in gym_keys


def test_pull_no_equip_slots_are_back_core_bw():
    bw = slots_for_session(
        "pull", compound_n=2, accessory_n=2, location="home", no_equipment=True
    )
    keys = [s.key for s in bw]
    assert "v_pull" not in keys
    assert "h_pull" not in keys
    assert "back_bw" in keys
    gym = slots_for_session(
        "pull", compound_n=2, accessory_n=1, location="home", no_equipment=False
    )
    assert "v_pull" in [s.key for s in gym]


def test_no_equip_back_slots_accept_table_and_backpack_rows():
    from app.services.workout_generation.session_templates import candidate_matches_slot

    pull = slots_for_session(
        "pull", compound_n=2, accessory_n=1, location="home", no_equipment=True
    )
    back = next(s for s in pull if s.key == "back_bw")
    assert "v_pull" in back.patterns
    assert "h_pull" in back.patterns
    table = {
        "id": 827,
        "movement_pattern": "v_pull",
        "movement_role": "compound",
        "muscle": "back-middle",
        "name_en": "Table Inverted Row",
        "name_vi": "Kéo người dưới bàn",
        "_block": "resistance",
    }
    backpack = {
        "id": 823,
        "movement_pattern": "h_pull",
        "movement_role": "compound",
        "muscle": "back-middle",
        "name_en": "Bent-Over Backpack Row",
        "name_vi": "Chèo ba lô cúi người",
        "_block": "resistance",
    }
    one_arm = {
        "id": 824,
        "movement_pattern": "h_pull",
        "movement_role": "compound",
        "muscle": "back-middle",
        "name_en": "One-Arm Backpack Row",
        "name_vi": "Chèo ba lô một tay",
        "_block": "resistance",
    }
    assert candidate_matches_slot(back, table)
    assert candidate_matches_slot(back, backpack)
    assert candidate_matches_slot(back, one_arm)


def test_l1_home_denies_unassisted_pullup_and_dip():
    assert is_home_denied_exercise(
        name_en="Pull-Up",
        name_vi="Hít xà",
        location="home",
        no_equipment=False,
        user_slugs=["pull-up-bar"],
        experience_level=1,
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
    )
    ids = [ex.exercise_id for ex in out[0].exercises]
    assert 9 not in ids
    assert 1 in ids


def _block(key: str, *, n: int, section: str, role: str, optional: bool = False) -> BlockSpec:
    return BlockSpec(
        block_key=key,
        label_vi=key,
        plan_section=section,
        movement_role=role,
        count_min=n,
        count_max=n,
        duration_min_minutes=None,
        duration_max_minutes=None,
        is_optional=optional,
        sort_order=20,
    )


def test_assemble_home_bw_fills_empty_resistance_instead_of_openai_error():
    recipe = [
        _block("resistance", n=2, section="main", role="resistance"),
        _block("conditioning", n=1, section="cardio", role="conditioning"),
    ]
    shortlists = {
        "resistance": [
            ShortlistItem(
                id=1,
                name_vi="Chống đẩy",
                movement_role="resistance",
                movement_pattern="h_push",
                muscle_slug="chest",
                difficulty=1,
                name_en="Push-up",
            ),
            ShortlistItem(
                id=2,
                name_vi="Squat không tạ",
                movement_role="resistance",
                movement_pattern="squat",
                muscle_slug="quads",
                difficulty=1,
                name_en="Bodyweight Squat",
            ),
        ],
        "conditioning": [
            ShortlistItem(
                id=10,
                name_vi="Burpee",
                movement_role="conditioning",
                movement_pattern="other",
                muscle_slug="conditioning",
                difficulty=1,
                name_en="Burpee",
            ),
        ],
    }
    frame = SimpleNamespace(split_role="upper", label_vi="Upper", notes_vi=None)

    def _identity_fill(day, **_kwargs):
        return day

    with patch(
        "app.services.workout_generation.assemble._recipe_for_day",
        return_value=recipe,
    ), patch(
        "app.services.workout_generation.assemble.get_prescription",
        return_value=None,
    ), patch(
        "app.services.workout_generation.assemble.fill_session_to_target",
        side_effect=_identity_fill,
    ):
        day = assemble_day(
            MagicMock(),
            frame_day=frame,
            day_number=1,
            experience_level=2,
            session_minutes=45,
            equipment_slugs=[],
            no_equipment=True,
            ai_suggest_equipment=False,
            picks_by_block={},
            location="home",
            split_role="upper",
            strict_openai_picks=True,
            precomputed_shortlists=shortlists,
        )
    main_ids = [ex.exercise_id for ex in day.exercises if (ex.section or "main") == "main"]
    assert 1 in main_ids and 2 in main_ids


def test_assemble_home_bw_raises_clear_error_when_pool_empty():
    recipe = [_block("resistance", n=2, section="main", role="resistance")]
    frame = SimpleNamespace(split_role="upper", label_vi="Upper", notes_vi=None)
    with patch(
        "app.services.workout_generation.assemble._recipe_for_day",
        return_value=recipe,
    ), pytest.raises(BadRequestError, match="bodyweight") as exc:
        assemble_day(
            MagicMock(),
            frame_day=frame,
            day_number=1,
            experience_level=2,
            session_minutes=45,
            equipment_slugs=[],
            no_equipment=True,
            ai_suggest_equipment=False,
            picks_by_block={},
            location="home",
            split_role="upper",
            strict_openai_picks=True,
            precomputed_shortlists={"resistance": []},
        )
    assert "OpenAI" not in exc.value.message


def test_home_improvised_catalog_has_thirteen_new_rows():
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "scripts" / "data"))
    from home_improvised_catalog import HOME_IMPROVISED_CATALOG  # noqa: WPS433

    assert len(HOME_IMPROVISED_CATALOG) == 13


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
