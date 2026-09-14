"""Tests for session block templates seed + get_session_recipe."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.migrations import ensure_session_block_templates
from app.services.session_block_template_seed import BLOCK_KEYS, SESSION_BLOCK_SEED
from app.services.session_blocks import get_master_session_recipe, get_session_recipe


def test_seed_has_eight_blocks_per_level():
    assert len(SESSION_BLOCK_SEED) == 24
    by_level: dict[int, set[str]] = {}
    for row in SESSION_BLOCK_SEED:
        by_level.setdefault(row[0], set()).add(row[2])
    assert set(by_level) == {1, 2, 3}
    for level, keys in by_level.items():
        assert keys == set(BLOCK_KEYS), level


def test_l1_compound_count_max_is_one():
    compound = [r for r in SESSION_BLOCK_SEED if r[0] == 1 and r[2] == "compound"][0]
    assert compound[6] == 1 and compound[7] == 1


def test_ensure_and_recipe_sqlite(tmp_path):
    db = tmp_path / "sbt.db"
    engine = create_engine(f"sqlite:///{db}")
    ensure_session_block_templates(engine)

    with engine.connect() as conn:
        n = conn.execute(text("SELECT COUNT(*) FROM session_block_templates")).scalar()
        assert int(n) == 24
        ensure_session_block_templates(engine)
        n2 = conn.execute(text("SELECT COUNT(*) FROM session_block_templates")).scalar()
        assert int(n2) == 24

    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        short = get_session_recipe(session, 1, 45)
        keys = [b.block_key for b in short]
        assert keys == list(BLOCK_KEYS[:-2]) + ["cooldown"]  # no cardio under 60
        assert "cardio" not in keys
        assert short[0].sort_order < short[-1].sort_order

        compound = next(b for b in short if b.block_key == "compound")
        assert compound.count_max == 1
        assert compound.plan_section == "main"
        assert compound.movement_role == "compound"

        long = get_session_recipe(session, 2, 60)
        assert any(b.block_key == "cardio" for b in long)
        assert [b.block_key for b in long] == list(BLOCK_KEYS)

        forced = get_session_recipe(session, 1, 30, include_cardio=True)
        assert any(b.block_key == "cardio" for b in forced)

        blocked = get_session_recipe(session, 3, 90, include_cardio=False)
        assert all(b.block_key != "cardio" for b in blocked)

        # Duration scaled up for longer sessions
        base = next(b for b in short if b.block_key == "general_warmup")
        scaled = next(
            b for b in get_session_recipe(session, 1, 70, include_cardio=False) if b.block_key == "general_warmup"
        )
        assert scaled.duration_min_minutes is not None
        assert base.duration_min_minutes is not None
        assert scaled.duration_min_minutes >= base.duration_min_minutes
    finally:
        session.close()


def test_master_recipe_l1_90_has_cardio_and_full_slots():
    blocks = get_master_session_recipe(
        location="gym",
        session_minutes=90,
        split_role="upper",
        experience_level=1,
        cardio_on_lift_days=True,
    )
    keys = [b.block_key for b in blocks]
    assert "cardio" in keys
    by_key = {b.block_key: b for b in blocks}
    assert by_key["compound"].count_max == 3
    assert by_key["accessory"].count_max == 2


def test_long_cardio_core_scales_one_cardio_to_session_length():
    for minutes, expected_cardio in ((75, 49), (90, 60)):
        blocks = get_master_session_recipe(
            location="gym",
            session_minutes=minutes,
            split_role="core",
            experience_level=1,
        )
        cardio = [b for b in blocks if b.block_key == "cardio"]
        core = [b for b in blocks if b.block_key == "core"]
        assert len(cardio) == 1
        assert cardio[0].duration_min_minutes == expected_cardio
        assert len(core) == 1 and core[0].count_max == 2


def test_master_recipe_l1_gain_skips_lift_cardio():
    blocks = get_master_session_recipe(
        location="gym",
        session_minutes=75,
        split_role="upper",
        experience_level=1,
        cardio_on_lift_days=False,
    )
    keys = [b.block_key for b in blocks]
    assert "cardio" not in keys
    by_key = {b.block_key: b for b in blocks}
    assert by_key["compound"].count_max == 3
    assert by_key["accessory"].count_max == 2
    blocks = get_master_session_recipe(location="gym", session_minutes=60, split_role="push")
    by_key = {b.block_key: b for b in blocks}
    assert by_key["compound"].count_max == 2
    assert by_key["accessory"].count_max == 3
    assert by_key["cardio"].count_max == 1


def test_master_recipe_home_60():
    blocks = get_master_session_recipe(location="home", session_minutes=60, split_role="upper")
    by_key = {b.block_key: b for b in blocks}
    assert by_key["resistance"].count_max == 4
    assert by_key["conditioning"].count_max == 1


def test_master_recipe_home_90_one_conditioning():
    blocks = get_master_session_recipe(location="home", session_minutes=90, split_role="legs")
    by_key = {b.block_key: b for b in blocks}
    assert by_key["resistance"].count_max == 6
    assert by_key["conditioning"].count_max == 1
    assert (by_key["conditioning"].duration_min_minutes or 0) >= 20


def test_home_no_equip_75_90_uses_master_resistance_and_zone2():
    for minutes, n_res, _cond_min in ((75, 5, 15), (90, 6, 20)):
        blocks = get_master_session_recipe(
            location="home",
            session_minutes=minutes,
            split_role="upper",
            no_equipment=True,
        )
        by = {b.block_key: b for b in blocks}
        assert by["resistance"].count_max == n_res
        assert by["conditioning"].count_max == 2
        assert (by["conditioning"].duration_min_minutes or 0) >= 5


def test_home_liss_does_not_stack_on_conditioning():
    blocks = get_master_session_recipe(
        location="home",
        session_minutes=60,
        split_role="upper",
        liss_finisher=True,
    )
    cardioish = [b for b in blocks if b.block_key in {"cardio", "conditioning"}]
    assert len(cardioish) == 1
    assert cardioish[0].block_key == "conditioning"


def test_master_recipe_l1_fb_90_caps_isolation():
    blocks = get_master_session_recipe(
        location="gym",
        session_minutes=90,
        split_role="fb",
        experience_level=1,
        cardio_on_lift_days=True,
    )
    by_key = {b.block_key: b for b in blocks}
    assert by_key["compound"].count_max == 4
    assert by_key["accessory"].count_max == 2


def test_master_recipe_core_day_no_compound():
    blocks = get_master_session_recipe(location="gym", session_minutes=60, split_role="core")
    keys = {b.block_key for b in blocks}
    assert "compound" not in keys
    cardio_blocks = [b for b in blocks if b.block_key in {"cardio", "conditioning"}]
    assert len(cardio_blocks) == 1
    assert cardio_blocks[0].count_max == 1
    assert (cardio_blocks[0].duration_min_minutes or 0) >= 20


def test_master_recipe_core_day_home_single_conditioning():
    blocks = get_master_session_recipe(location="home", session_minutes=45, split_role="core")
    cardio_blocks = [b for b in blocks if b.block_key in {"cardio", "conditioning"}]
    assert len(cardio_blocks) == 1
    assert cardio_blocks[0].count_max == 1
    assert (cardio_blocks[0].duration_min_minutes or 0) >= 12


def test_master_recipe_liss_finisher_45_does_not_cut_compounds():
    base = get_master_session_recipe(
        location="gym",
        session_minutes=45,
        split_role="upper",
        experience_level=1,
        cardio_on_lift_days=False,
    )
    with_liss = get_master_session_recipe(
        location="gym",
        session_minutes=45,
        split_role="upper",
        experience_level=1,
        cardio_on_lift_days=False,
        liss_finisher=True,
    )
    assert "cardio" not in {b.block_key for b in base}
    cardio = next(b for b in with_liss if b.block_key == "cardio")
    assert cardio.duration_min_minutes == 8
    assert cardio.duration_max_minutes == 10
    by_key = {b.block_key: b for b in with_liss}
    base_by = {b.block_key: b for b in base}
    assert by_key["compound"].count_max == base_by["compound"].count_max
    assert by_key["accessory"].count_max == base_by["accessory"].count_max
    keys = [b.block_key for b in with_liss]
    assert keys.index("cardio") < keys.index("cooldown")


def test_master_recipe_l3_lift_has_core_finisher():
    blocks = get_master_session_recipe(
        location="gym",
        session_minutes=45,
        split_role="push",
        experience_level=3,
        cardio_on_lift_days=False,
    )
    keys = [b.block_key for b in blocks]
    assert "core" in keys
    assert keys.index("accessory") < keys.index("core")
    assert keys.index("core") < keys.index("cooldown")
    l2 = get_master_session_recipe(
        location="gym",
        session_minutes=45,
        split_role="push",
        experience_level=2,
        cardio_on_lift_days=False,
    )
    assert "core" not in {b.block_key for b in l2}


def test_cooldown_prefers_stretch_in_region():
    from app.services.workout_generation.openai_picker import deterministic_picks

    blocks = [
        {
            "block_key": "compound",
            "pick": True,
            "count_max": 1,
            "is_optional": False,
            "shortlist": [
                {"id": 1, "movement_pattern": "h_push", "movement_role": "compound", "muscle": "chest"},
            ],
        },
        {
            "block_key": "accessory",
            "pick": True,
            "count_max": 1,
            "is_optional": False,
            "shortlist": [
                {"id": 10, "movement_pattern": "h_push", "movement_role": "isolation", "muscle": "triceps"},
            ],
        },
        {
            "block_key": "general_warmup",
            "pick": True,
            "count_max": 1,
            "is_optional": False,
            "shortlist": [
                {"id": 50, "name_vi": "Xoay hông", "muscle": "glutes", "movement_role": "mobility"},
                {"id": 51, "name_vi": "Xoay vai", "muscle": "shoulders", "movement_role": "mobility"},
            ],
        },
        {
            "block_key": "cooldown",
            "pick": True,
            "count_max": 1,
            "is_optional": False,
            "shortlist": [
                {"id": 60, "name_vi": "Xoay cổ chân", "muscle": "calves", "movement_role": "mobility"},
                {"id": 61, "name_vi": "Giãn ngực tại khung cửa", "muscle": "stretch", "movement_role": "mobility"},
            ],
        },
    ]
    picks = deterministic_picks(blocks, split_role="push")
    assert picks["general_warmup"] == [51]
    assert picks["cooldown"] == [61]
