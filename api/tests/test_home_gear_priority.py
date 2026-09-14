"""Home + equipment: gear-first pools, bodyweight only when gear would repeat."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from app.schemas.plans import PlanDayIn, PlanExerciseIn
from app.services.session_blocks import BlockSpec
from app.services.workout_generation.home_gear_priority import (
    HOME_GEAR_MIN_POOL,
    TIER_BODYWEIGHT,
    TIER_GEAR,
    TIER_OTHER,
    enforce_home_gear_variety,
    gear_share,
    gear_tier,
    home_gear_active,
    min_gear_pool,
    sort_gear_first,
    tier_slot_pool,
    user_gear_set,
)
from app.services.workout_generation.repair import repair_block_picks
from app.services.workout_generation.session_templates import (
    ExerciseSlot,
    fill_strength_slots,
    pools_for_slots,
    prompt_pool_row,
    slots_to_prompt,
)
from app.services.workout_generation.shortlist import ShortlistItem, shortlist_to_prompt_dicts


def _item(
    eid: int,
    name: str,
    *,
    pattern: str = "h_push",
    muscle: str = "chest",
    role: str = "resistance",
    eq: tuple[str, ...] = (),
    name_en: str | None = None,
) -> ShortlistItem:
    return ShortlistItem(
        id=eid,
        name_vi=name,
        movement_role=role,
        movement_pattern=pattern,
        muscle_slug=muscle,
        difficulty=2,
        name_en=name_en,
        equipment_slugs=frozenset(eq),
    )


def _row(eid: int, name: str, *, pattern="h_push", muscle="chest", eq=()) -> dict:
    d = {
        "id": eid,
        "name_vi": name,
        "movement_role": "resistance",
        "pattern": pattern,
        "muscle": muscle,
    }
    if eq:
        d["equipment_slugs"] = list(eq)
    return d


# --- tiers / activation -----------------------------------------------------


def test_home_gear_active_only_for_home_with_gear():
    assert home_gear_active("home", no_equipment=False, equipment_slugs=["dumbbell"])
    assert not home_gear_active("home", no_equipment=True, equipment_slugs=["dumbbell"])
    assert not home_gear_active("home", no_equipment=False, equipment_slugs=[])
    assert not home_gear_active("gym", no_equipment=False, equipment_slugs=["dumbbell"])


def test_gear_tier_uses_band_aliases():
    user = user_gear_set(["resistance-band"])
    assert gear_tier(["resistance-band-2"], user) == TIER_GEAR
    assert gear_tier([], user) == TIER_BODYWEIGHT
    assert gear_tier(["kettlebell"], user) == TIER_OTHER


def test_min_gear_pool_scales_with_role_count_and_variants():
    assert min_gear_pool(1, 1) == HOME_GEAR_MIN_POOL  # PPL
    assert min_gear_pool(3, 1) == 4  # FB x3
    assert min_gear_pool(2, 3) == 7  # Upper x2, challenge 3 phases


# --- pool tiering -----------------------------------------------------------


def test_tier_slot_pool_drops_bodyweight_when_gear_is_enough():
    user = user_gear_set(["dumbbell"])
    pool = [_row(i, f"DB press {i}", eq=("dumbbell",)) for i in range(1, 14)] + [
        _row(100 + i, f"Chống đẩy {i}") for i in range(6)
    ]
    rows, meta = tier_slot_pool(pool, user_expanded=user, need=4)
    assert [r["id"] for r in rows] == list(range(1, 14))
    assert all(r.get("_gear") for r in rows)
    assert meta == {"gear_n": 13, "bw_n": 6, "bw_kept": 0, "need": 4}


def test_tier_slot_pool_tops_up_with_bodyweight_gear_first():
    user = user_gear_set(["resistance-band"])
    pool = [
        _row(50, "Chống đẩy gối"),
        _row(51, "Chống đẩy"),
        _row(1, "Band squat", eq=("resistance-band-1",)),
        _row(52, "Squat không tạ"),
    ]
    rows, meta = tier_slot_pool(pool, user_expanded=user, need=3)
    assert [r["id"] for r in rows] == [1, 50, 51]
    assert meta["gear_n"] == 1 and meta["bw_kept"] == 2


def test_tier_slot_pool_bw_key_orders_fallback():
    user = user_gear_set(["pull-up-bar"])
    pool = [_row(10, "Plank"), _row(11, "Chống đẩy"), _row(12, "Crunch")]
    rows, _ = tier_slot_pool(
        pool,
        user_expanded=user,
        need=2,
        bw_key=lambda r: 0 if "chống đẩy" in r["name_vi"].lower() else 1,
    )
    assert [r["id"] for r in rows] == [11, 10]


def test_tier_slot_pool_excludes_other_gear():
    user = user_gear_set(["dumbbell"])
    pool = [_row(1, "KB swing", eq=("kettlebell",)), _row(2, "Chống đẩy")]
    rows, meta = tier_slot_pool(pool, user_expanded=user, need=3)
    assert [r["id"] for r in rows] == [2]
    assert meta["gear_n"] == 0


def test_sort_gear_first_is_stable():
    user = user_gear_set(["dumbbell"])
    items = [_item(1, "BW a"), _item(2, "DB a", eq=("dumbbell",)), _item(3, "BW b"), _item(4, "DB b", eq=("dumbbell",))]
    assert [it.id for it in sort_gear_first(items, user)] == [2, 4, 1, 3]


# --- prompt rows ------------------------------------------------------------


def test_prompt_rows_mark_bw_only_and_strip_internal_keys():
    row = {"id": 1, "name_vi": "Chống đẩy", "_gear": 0, "equipment_slugs": []}
    out = prompt_pool_row(row, mark_bw=True)
    assert out == {"id": 1, "name_vi": "Chống đẩy", "bw": 1}
    gear = prompt_pool_row({"id": 2, "name_vi": "DB", "equipment_slugs": ["dumbbell"], "_gear": 1}, mark_bw=True)
    assert gear == {"id": 2, "name_vi": "DB"}
    # Gym / no-equipment: no flag at all.
    assert "bw" not in prompt_pool_row(row, mark_bw=False)

    dicts = shortlist_to_prompt_dicts([_item(1, "BW"), _item(2, "DB", eq=("dumbbell",))], mark_bw=True)
    assert dicts[0].get("bw") == 1 and "bw" not in dicts[1]
    assert "equipment_slugs" not in dicts[1]


def test_pools_for_slots_carry_equipment_and_slots_to_prompt_strips_it():
    slot = ExerciseSlot(
        key="h_press",
        block="resistance",
        roles=frozenset({"compound", "resistance"}),
        patterns=("h_push",),
        muscles=frozenset({"chest"}),
    )
    pools = pools_for_slots(
        [_item(1, "Chống đẩy"), _item(2, "DB bench", eq=("dumbbell",))], [slot], split_role="push"
    )
    by_id = {r["id"]: r for r in pools["h_press"]}
    assert by_id[2]["equipment_slugs"] == ["dumbbell"]
    assert "equipment_slugs" not in by_id[1]
    spec = slots_to_prompt([slot], pools, mark_bw=True)[0]
    prompt_by_id = {r["id"]: r for r in spec["pool"]}
    assert prompt_by_id[1]["bw"] == 1
    assert "bw" not in prompt_by_id[2] and "equipment_slugs" not in prompt_by_id[2]


# --- catalog gaps that blocked gear from reaching the pools ----------------


def test_dumbbell_bench_press_is_not_avoided_in_chest_compound_slot():
    from app.services.workout_generation.session_templates import (
        _push_compounds,
        candidate_matches_slot,
    )

    h_press = next(s for s in _push_compounds("resistance") if s.key == "h_press")
    db_press = {
        "id": 63,
        "name_vi": "Ép ngực tạ đơn",
        "name_en": "Dumbbell Bench Press",
        "movement_role": "compound",
        "movement_pattern": "h_push",
        "muscle": "chest-mid",
    }
    pec_deck = {
        "id": 99,
        "name_vi": "Ép ngực máy",
        "name_en": "Pec Deck",
        "movement_role": "compound",
        "movement_pattern": "h_push",
        "muscle": "chest-mid",
    }
    decline = dict(db_press, id=628, name_vi="Ép ngực dốc xuống tạ đơn", name_en="Decline Dumbbell Press")
    assert candidate_matches_slot(h_press, db_press, split_role="push")
    assert not candidate_matches_slot(h_press, pec_deck, split_role="push")
    assert not candidate_matches_slot(h_press, decline, split_role="push")


def test_dumbbell_row_allowed_at_home_only_with_dumbbell():
    from app.services.workout_generation.shortlist import (
        exercise_passes_location_gear,
        is_home_denied_exercise,
    )

    common = dict(name_vi="Chèo tạ đơn một tay", name_en="Dumbbell Single Arm Row", location="home", no_equipment=False)
    assert not is_home_denied_exercise(**common, user_slugs=["dumbbell"], exercise_slugs=["dumbbell"])
    assert is_home_denied_exercise(**common, user_slugs=["resistance-band"], exercise_slugs=["dumbbell"])
    assert is_home_denied_exercise(**common, user_slugs=[], exercise_slugs=["dumbbell"])
    # Cable / barbell / inverted rows stay denied even for a dumbbell owner.
    assert is_home_denied_exercise(
        name_vi="Chèo tạ đòn", name_en="Barbell Row", location="home", no_equipment=False,
        user_slugs=["dumbbell"], exercise_slugs=["barbell"],
    )
    assert is_home_denied_exercise(
        name_vi="Chèo người nằm", name_en="Inverted Row", location="home", no_equipment=False,
        user_slugs=["dumbbell"], exercise_slugs=[],
    )
    assert exercise_passes_location_gear(
        venue="both", equipment_slugs=["dumbbell"], name_vi="Chèo tạ đơn một tay",
        name_en="Dumbbell Single Arm Row", location="home", user_slugs=["dumbbell"],
    )


# --- deterministic fill / repair ------------------------------------------


def test_fill_strength_slots_prefers_gear_flag_over_bw():
    slot = ExerciseSlot(
        key="h_press",
        block="resistance",
        roles=frozenset({"compound", "resistance"}),
        patterns=("h_push",),
        muscles=frozenset({"chest"}),
    )
    # Bodyweight row has the lower id (would win the id%7 tie-break) but is marked bw.
    pool = [
        {"id": 1, "name_vi": "Chống đẩy", "movement_role": "resistance", "movement_pattern": "h_push", "muscle": "chest", "bw": 1},
        {"id": 2, "name_vi": "DB bench", "movement_role": "resistance", "movement_pattern": "h_push", "muscle": "chest", "_gear": 1},
    ]
    out = fill_strength_slots("push", [slot], pool)
    assert out["resistance"] == [2]


def test_repair_block_picks_fills_gear_first_when_user_gear_given():
    block = BlockSpec(
        block_key="resistance",
        label_vi="resistance",
        plan_section="main",
        movement_role="resistance",
        count_min=2,
        count_max=2,
        duration_min_minutes=None,
        duration_max_minutes=None,
        is_optional=False,
        sort_order=1,
    )
    shortlist = [_item(1, "BW a"), _item(2, "BW b"), _item(3, "DB a", eq=("dumbbell",)), _item(4, "DB b", eq=("dumbbell",))]
    plain = repair_block_picks(block=block, picked_ids=[], shortlist=shortlist, used_ids=set())
    assert plain == [1, 2]
    geared = repair_block_picks(
        block=block, picked_ids=[], shortlist=shortlist, used_ids=set(), user_gear=user_gear_set(["dumbbell"])
    )
    assert geared == [3, 4]


# --- collect_day_shortlists_for_prompt wiring -------------------------------


def _block(key: str, n: int, *, section: str, role: str, optional: bool = False) -> BlockSpec:
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


def test_collect_day_shortlists_tiers_home_gear_pools():
    from app.services.workout_generation import assemble

    recipe = [_block("resistance", 3, section="main", role="resistance")]
    catalog = [
        _item(1, "Chống đẩy", name_en="Push-up"),
        _item(2, "Chống đẩy gối", name_en="Knee push-up"),
        _item(3, "DB bench press", eq=("dumbbell",)),
        _item(4, "DB incline press", eq=("dumbbell",)),
        _item(5, "DB floor press", eq=("dumbbell",)),
        _item(6, "DB OHP", pattern="v_push", muscle="shoulders", eq=("dumbbell",)),
        _item(7, "Pike push-up", pattern="v_push", muscle="shoulders"),
        _item(8, "DB lateral raise", pattern="other", muscle="shoulders", role="isolation", eq=("dumbbell",)),
        _item(9, "DB fly", pattern="h_push", muscle="chest", role="isolation", eq=("dumbbell",)),
        _item(10, "DB triceps ext", pattern="other", muscle="triceps", role="isolation", eq=("dumbbell",)),
    ]
    shortlists = {"resistance": list(catalog)}
    frame = SimpleNamespace(split_role="push", day_index=0)
    out_slots: list[dict] = []
    out_short: dict = {}
    gear_meta: dict = {}
    with patch.object(assemble, "_recipe_for_day", return_value=recipe), patch.object(
        assemble, "_build_day_shortlists", return_value=dict(shortlists)
    ), patch.object(assemble, "query_filtered_exercises", return_value=list(catalog)):
        assemble.collect_day_shortlists_for_prompt(
            None,
            frame_day=frame,
            experience_level=2,
            session_minutes=45,
            equipment_slugs=["dumbbell"],
            no_equipment=False,
            ai_suggest_equipment=False,
            location="home",
            split_role="push",
            out_shortlists=out_short,
            out_slots=out_slots,
            week_role_count=1,
            pick_variants=1,
            out_gear_meta=gear_meta,
        )
    by_key = {s["key"]: s for s in out_slots}
    h_press = by_key["h_press"]["pool"]
    # 3 dumbbell presses >= need 3 → push-ups are cut from the prompt pool.
    assert {r["id"] for r in h_press} == {3, 4, 5}
    assert all("bw" not in r and "equipment_slugs" not in r for r in h_press)
    assert gear_meta["h_press"]["bw_kept"] == 0
    # Every prompt pool: gear rows precede any bw rows.
    for spec in out_slots:
        flags = [bool(r.get("bw")) for r in spec["pool"]]
        assert flags == sorted(flags), spec["key"]
    # Bodyweight rows stay available downstream (repair / variety) with their equipment info.
    merged = {it.id: it for it in out_short["resistance"]}
    assert merged[3].equipment_slugs == frozenset({"dumbbell"})
    assert 1 in merged and merged[1].equipment_slugs == frozenset()


def test_collect_day_shortlists_keeps_bw_when_gear_is_thin():
    from app.services.workout_generation import assemble

    recipe = [_block("resistance", 2, section="main", role="resistance")]
    catalog = [
        _item(1, "Chống đẩy", name_en="Push-up"),
        _item(2, "Chống đẩy gối", name_en="Knee push-up"),
        _item(3, "Pike push-up", pattern="v_push", muscle="shoulders"),
        _item(4, "Band chest press", eq=("resistance-band-2",)),
        _item(5, "Band OHP", pattern="v_push", muscle="shoulders", eq=("resistance-band-2",)),
        _item(6, "Band triceps", pattern="other", muscle="triceps", role="isolation", eq=("resistance-band-2",)),
    ]
    frame = SimpleNamespace(split_role="push", day_index=0)
    out_slots: list[dict] = []
    gear_meta: dict = {}
    with patch.object(assemble, "_recipe_for_day", return_value=recipe), patch.object(
        assemble, "_build_day_shortlists", return_value={"resistance": list(catalog)}
    ), patch.object(assemble, "query_filtered_exercises", return_value=list(catalog)):
        assemble.collect_day_shortlists_for_prompt(
            None,
            frame_day=frame,
            experience_level=2,
            session_minutes=45,
            equipment_slugs=["resistance-band-1", "resistance-band-2"],
            no_equipment=False,
            ai_suggest_equipment=False,
            location="home",
            split_role="push",
            out_slots=out_slots,
            week_role_count=1,
            out_gear_meta=gear_meta,
        )
    h_press = {s["key"]: s for s in out_slots}["h_press"]["pool"]
    ids = [r["id"] for r in h_press]
    assert ids[0] == 4  # band row first
    assert len(ids) == 3  # topped up to need=3 with push-ups
    assert all(r.get("bw") == 1 for r in h_press[1:])
    assert gear_meta["h_press"] == {"gear_n": 1, "bw_n": 2, "bw_kept": 2, "need": 3}


# --- week-level variety -----------------------------------------------------


def _day(n: int, role: str, ids: list[int]) -> PlanDayIn:
    return PlanDayIn(
        day_number=n,
        split_role=role,
        exercises=[PlanExerciseIn(exercise_id=i, section="main", sort_order=k + 1) for k, i in enumerate(ids)],
    )


def _meta(name: str, *, pattern="squat", muscle="quads", role="resistance", eq=()) -> dict:
    return {
        "name_vi": name,
        "name_en": None,
        "movement_role": role,
        "movement_pattern": pattern,
        "muscle_slug": muscle,
        "equipment_slugs": list(eq),
    }


def test_variety_replaces_third_repeat_with_gear_then_bodyweight():
    meta = {
        1: _meta("Goblet squat", eq=("dumbbell",)),
        2: _meta("DB front squat", eq=("dumbbell",)),
        3: _meta("Squat không tạ"),
        4: _meta("Pistol squat"),
        9: _meta("DB row", pattern="h_pull", muscle="back", eq=("dumbbell",)),
    }
    pool = [
        _item(1, "Goblet squat", pattern="squat", muscle="quads", eq=("dumbbell",)),
        _item(2, "DB front squat", pattern="squat", muscle="quads", eq=("dumbbell",)),
        _item(3, "Squat không tạ", pattern="squat", muscle="quads"),
        _item(4, "Pistol squat", pattern="squat", muscle="quads"),
    ]
    pools = {1: pool, 2: pool, 3: pool, 4: pool}
    days = [_day(1, "fb_a", [1, 9]), _day(2, "fb_b", [1, 9]), _day(3, "fb_a", [1, 9]), _day(4, "fb_b", [1, 9])]
    insight = enforce_home_gear_variety(
        days, pools_by_day=pools, meta_by_id=meta, user_slugs=["dumbbell"], experience_level=2
    )
    picked = [d.exercises[0].exercise_id for d in days]
    # Cap 2 per week: day 3 → unused dumbbell squat (2); day 4 → gear exhausted → bodyweight (3).
    assert picked == [1, 1, 2, 3]
    assert [r["to"] for r in insight["replaced"]] == [2, 3]
    assert [r["bw"] for r in insight["replaced"]] == [False, True]
    assert insight["gear_share"] == round(7 / 8, 3)
    # DB row repeated 4x but has no alternative in pools → reported, left in place.
    assert {r["exercise_id"] for r in insight["unchanged_no_alternative"]} == {9}


def test_variety_caps_lift_stem_and_respects_l1_bar_skills():
    meta = {
        1: _meta("Lunge tạ đơn", eq=("dumbbell",)),
        2: _meta("Reverse lunge tạ đơn", eq=("dumbbell",)),
        3: _meta("Bulgarian split squat", eq=("dumbbell",)),
        4: _meta("Goblet squat", eq=("dumbbell",)),
        20: _meta("Hít xà", pattern="v_pull", muscle="back", eq=("pull-up-bar",)),
        21: _meta("Scapular pull", pattern="v_pull", muscle="back", eq=("pull-up-bar",)),
        22: _meta("Superman", pattern="v_pull", muscle="back"),
    }
    pool = [
        _item(1, "Lunge tạ đơn", pattern="squat", muscle="quads", eq=("dumbbell",)),
        _item(2, "Reverse lunge tạ đơn", pattern="squat", muscle="quads", eq=("dumbbell",)),
        _item(3, "Bulgarian split squat", pattern="squat", muscle="quads", eq=("dumbbell",)),
        _item(4, "Goblet squat", pattern="squat", muscle="quads", eq=("dumbbell",)),
        _item(20, "Hít xà", pattern="v_pull", muscle="back", eq=("pull-up-bar",), name_en="Pull-up"),
        _item(21, "Scapular pull", pattern="v_pull", muscle="back", eq=("pull-up-bar",)),
        _item(22, "Superman", pattern="v_pull", muscle="back"),
    ]
    pools = {i: pool for i in range(1, 5)}
    # Three different lunge ids = stem "lunge" x3 already → 4th lunge-family lift must change.
    days = [_day(1, "fb_a", [1, 21]), _day(2, "fb_b", [2, 21]), _day(3, "fb_a", [3, 21]), _day(4, "fb_b", [1, 21])]
    insight = enforce_home_gear_variety(
        days,
        pools_by_day=pools,
        meta_by_id=meta,
        user_slugs=["dumbbell", "pull-up-bar"],
        experience_level=1,
    )
    assert days[3].exercises[0].exercise_id == 4  # goblet squat (stem-free, gear)
    # Scapular pull repeated 4x: L1 must not receive raw pull-up (20); bodyweight Superman is fine.
    back_ids = [d.exercises[1].exercise_id for d in days]
    assert back_ids[:2] == [21, 21]
    assert 20 not in back_ids
    assert back_ids[2] == 22
    assert any(r["reason"] == "repeat_stem" for r in insight["replaced"])


def test_variety_noop_outside_home_gear():
    meta = {1: _meta("Goblet squat", eq=("dumbbell",))}
    pool = [_item(2, "DB front squat", pattern="squat", muscle="quads", eq=("dumbbell",))]
    days = [_day(i, "fb_a", [1]) for i in range(1, 4)]
    for kwargs in (
        {"location": "gym", "no_equipment": False, "user_slugs": ["dumbbell"]},
        {"location": "home", "no_equipment": True, "user_slugs": []},
    ):
        insight = enforce_home_gear_variety(
            days, pools_by_day={i: pool for i in range(1, 4)}, meta_by_id=meta, **kwargs
        )
        assert insight["replaced"] == []
        assert [d.exercises[0].exercise_id for d in days] == [1, 1, 1]


def test_gear_share_ignores_non_main_and_unknown():
    meta = {
        1: _meta("DB press", eq=("dumbbell",)),
        2: _meta("Chống đẩy"),
        3: _meta("Đi bộ", role="cardio"),
        4: {"name_vi": "unknown", "movement_role": "resistance"},
    }
    day = PlanDayIn(
        day_number=1,
        split_role="push",
        exercises=[
            PlanExerciseIn(exercise_id=1, section="main"),
            PlanExerciseIn(exercise_id=2, section="main"),
            PlanExerciseIn(exercise_id=3, section="cardio"),
            PlanExerciseIn(exercise_id=4, section="main"),
        ],
    )
    assert gear_share([day], meta_by_id=meta, user_expanded=user_gear_set(["dumbbell"])) == 0.5
