"""Session quality: mobility match, timed cardio, hamstrings, warmup rest, fill."""

from app.schemas.plans import PlanDayIn, PlanExerciseIn
from app.services.session_blocks import get_master_session_recipe
from app.services.workout_generation.muscle_quotas import repair_muscle_quotas
from app.services.workout_generation.session_duration import (
    _block_counts,
    _pick_fill_action,
    parse_reps_minutes,
    top_up_session_minutes,
)
from app.services.workout_generation.session_templates import slots_for_session
from app.services.workout_generation.shortlist import ShortlistItem
from app.services.workout_generation.split_map import mobility_match_rank
from app.services.workout_rest import timed_block_prescription


def test_gym_75_warmup_is_one_stretch():
    blocks = get_master_session_recipe(
        location="gym",
        session_minutes=75,
        split_role="push",
        experience_level=2,
    )
    by_key = {b.block_key: b for b in blocks}
    gen = by_key["general_warmup"]
    assert "dynamic_mobility" not in by_key
    assert gen.count_max == 1
    assert (gen.duration_min_minutes or 0) <= 5


def test_gym_45_cooldown_two_drills():
    blocks = get_master_session_recipe(
        location="gym",
        session_minutes=45,
        split_role="legs",
        experience_level=2,
    )
    cool = next(b for b in blocks if b.block_key == "cooldown")
    assert cool.count_max == 2
    assert (cool.duration_min_minutes or 0) <= 5


def test_home_30_conditioning_is_timed_minutes():
    blocks = get_master_session_recipe(
        location="home",
        session_minutes=30,
        split_role="legs",
        experience_level=2,
    )
    cond = next(b for b in blocks if b.block_key == "conditioning")
    assert cond.plan_section == "cardio"
    assert cond.movement_role == "conditioning"
    assert (cond.duration_min_minutes or 0) >= 5
    sets, reps, rest, _notes = timed_block_prescription(
        block_key=cond.block_key,
        plan_section=cond.plan_section,
        movement_role=cond.movement_role,
        duration_min=cond.duration_min_minutes,
        duration_max=cond.duration_max_minutes,
    )
    assert sets == 1
    assert rest == 0
    assert parse_reps_minutes(reps) == cond.duration_min_minutes


def test_home_30_warmup_is_one_stretch():
    blocks = get_master_session_recipe(
        location="home",
        session_minutes=30,
        split_role="push",
        experience_level=2,
    )
    wu = next(b for b in blocks if b.block_key == "general_warmup")
    assert wu.count_max == 1
    assert (wu.duration_min_minutes or 0) <= 5


def test_legs_30_gym_ham_iso_before_calf():
    slots = slots_for_session("legs", compound_n=1, accessory_n=3, location="gym")
    iso_keys = [s.key for s in slots if s.block == "accessory"]
    assert iso_keys[0] == "ham_iso"
    assert iso_keys[-1] == "calf_iso"
    assert "leg_extra_iso" not in iso_keys
    assert "leg_finisher_iso" not in iso_keys
    extra = next(s for s in slots_for_session("legs", compound_n=2, accessory_n=5, location="gym") if s.key == "leg_extra_iso")
    assert extra.avoid and any("calf" in a for a in extra.avoid)


def test_home_legs_repair_swaps_in_ham_curl():
    blocks = [
        {
            "block_key": "resistance",
            "pick": True,
            "count_max": 2,
            "shortlist": [
                {
                    "id": 1,
                    "movement_pattern": "squat",
                    "movement_role": "resistance",
                    "muscle": "quads",
                },
                {
                    "id": 2,
                    "movement_pattern": "other",
                    "movement_role": "resistance",
                    "muscle": "calves",
                },
                {
                    "id": 3,
                    "movement_pattern": "other",
                    "movement_role": "resistance",
                    "muscle": "hamstrings",
                    "name_vi": "Leg curl",
                },
            ],
        }
    ]
    out = repair_muscle_quotas(
        blocks, {"resistance": [1, 2]}, split_role="legs"
    )
    assert 3 in out["resistance"]


def test_cooldown_rank_prefers_trained_stretch():
    ham = mobility_match_rank(
        muscle_slug="hamstrings",
        name_vi="Giãn hamstring",
        split_role="push",
        cooldown=True,
        trained_slugs=frozenset({"chest"}),
    )
    chest = mobility_match_rank(
        muscle_slug="chest",
        name_vi="Giãn ngực",
        split_role="push",
        cooldown=True,
        trained_slugs=frozenset({"chest"}),
    )
    assert chest < ham


def test_block_counts_isolation_is_not_core():
    day = PlanDayIn(
        day_number=1,
        exercises=[
            PlanExerciseIn(
                exercise_id=1, sets=3, reps="12", rest_seconds=90, section="main"
            ),
            PlanExerciseIn(
                exercise_id=2, sets=3, reps="15", rest_seconds=60, section="main"
            ),
        ],
    )
    meta = {
        1: ShortlistItem(
            id=1,
            name_vi="Fly",
            movement_role="isolation",
            movement_pattern="other",
            muscle_slug="chest",
            difficulty=2,
        ),
        2: ShortlistItem(
            id=2,
            name_vi="Crunch",
            movement_role="isolation",
            movement_pattern="core",
            muscle_slug="core",
            difficulty=2,
        ),
    }
    counts = _block_counts(day, meta)
    assert counts.get("accessory") == 1
    assert counts.get("core") == 1


def test_top_up_does_not_inflate_warmup_or_conditioning_sets():
    day = PlanDayIn(
        day_number=1,
        exercises=[
            PlanExerciseIn(
                exercise_id=1, sets=1, reps="5 phút", rest_seconds=30, section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=2, sets=3, reps="12", rest_seconds=90, section="main"
            ),
            PlanExerciseIn(
                exercise_id=3, sets=1, reps="5 phút", rest_seconds=0, section="cardio"
            ),
        ],
    )
    meta = {
        1: {"movement_role": "mobility", "muscle_slug": "shoulders"},
        2: {"movement_role": "isolation", "muscle_slug": "chest"},
        3: {"movement_role": "conditioning", "muscle_slug": "cardio"},
    }
    out = top_up_session_minutes([day], session_minutes=40, meta_by_id=meta)[0]
    wu = next(e for e in out.exercises if e.section == "warmup")
    card = next(e for e in out.exercises if e.section == "cardio")
    iso = next(e for e in out.exercises if e.section == "main")
    assert wu.reps == "5 phút"
    assert card.sets == 1
    assert iso.sets >= 3


def test_pick_fill_does_not_pad_warmup():
    exercises = [
        PlanExerciseIn(
            exercise_id=1, sets=1, reps="3 phút", rest_seconds=30, section="warmup"
        ),
        PlanExerciseIn(
            exercise_id=2, sets=4, reps="12", rest_seconds=90, section="main"
        ),
    ]
    meta = {
        1: ShortlistItem(
            id=1,
            name_vi="Xoay vai",
            movement_role="mobility",
            movement_pattern="other",
            muscle_slug="shoulders",
            difficulty=1,
        ),
        2: ShortlistItem(
            id=2,
            name_vi="Fly",
            movement_role="isolation",
            movement_pattern="other",
            muscle_slug="chest",
            difficulty=2,
        ),
    }
    changed = _pick_fill_action(exercises, meta, gap=10)
    assert exercises[0].reps == "3 phút"
    if changed:
        assert exercises[1].sets >= 4


def test_gym_core_recipe_is_single_longer_cardio():
    blocks = get_master_session_recipe(
        location="gym", session_minutes=60, split_role="core"
    )
    cardio = [b for b in blocks if b.block_key in {"cardio", "conditioning"}]
    assert len(cardio) == 1
    assert cardio[0].count_max == 1
    assert (cardio[0].duration_min_minutes or 0) >= 20


def test_warmup_second_slot_is_lighter_first_main():
    from app.services.workout_generation.assemble import inject_main_primer_warmup

    day = PlanDayIn(
        day_number=1,
        exercises=[
            PlanExerciseIn(
                exercise_id=10, sets=1, reps="3 phút", rest_seconds=30, section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=11, sets=1, reps="2 phút", rest_seconds=30, section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=20, sets=3, reps="6-10", rest_seconds=180, section="main"
            ),
            PlanExerciseIn(
                exercise_id=21, sets=3, reps="10", rest_seconds=90, section="main"
            ),
        ],
    )
    out = inject_main_primer_warmup(day)
    warmup = [ex for ex in out.exercises if ex.section == "warmup"]
    mains = [ex for ex in out.exercises if ex.section == "main"]
    assert len(warmup) == 3
    assert warmup[0].exercise_id == 10
    assert warmup[1].exercise_id == 11
    assert warmup[-1].exercise_id == mains[0].exercise_id == 20
    assert warmup[-1].sets == 2
    assert warmup[-1].reps == "4"
    assert warmup[-1].rest_seconds == 45
    assert "chậm" in (warmup[-1].notes_vi or "") or "cham" in (warmup[-1].notes_vi or "").lower()
    assert mains[0].sets == 3
    assert mains[0].reps == "6-10"


def test_free_home_primer_is_one_set_on_short_sessions():
    from app.services.workout_generation.assemble import inject_main_primer_warmup

    day = PlanDayIn(
        day_number=1,
        exercises=[
            PlanExerciseIn(
                exercise_id=10, sets=1, reps="30 giây", rest_seconds=30, section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=20, sets=2, reps="8-12", rest_seconds=45, section="main"
            ),
        ],
    )
    out = inject_main_primer_warmup(
        day, free_home=True, session_minutes=30, home_session=True
    )
    primer = [ex for ex in out.exercises if ex.section == "warmup"][-1]
    assert primer.exercise_id == 20
    assert primer.sets == 1

    long_day = PlanDayIn(
        day_number=1,
        exercises=[
            PlanExerciseIn(
                exercise_id=10, sets=2, reps="30 giây", rest_seconds=30, section="warmup"
            ),
            PlanExerciseIn(
                exercise_id=20, sets=3, reps="8-12", rest_seconds=60, section="main"
            ),
        ],
    )
    long_out = inject_main_primer_warmup(
        long_day, free_home=True, session_minutes=75, home_session=True
    )
    long_primer = [ex for ex in long_out.exercises if ex.section == "warmup"][-1]
    assert long_primer.sets == 2
