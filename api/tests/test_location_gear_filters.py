"""Venue + gear filters for home/gym shortlist and exercise alternatives."""

from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.schemas.plans import PlanWizardInputsOut
from app.services.search_service import SearchService
from app.services.session_blocks import BlockSpec
from app.services.workout_generation.shortlist import (
    build_shortlist,
    exercise_passes_location_gear,
    location_from_venue,
    normalize_location_gear,
)


def test_normalize_home_empty_list_is_bodyweight():
    loc, no_eq, raw = normalize_location_gear("home", no_equipment=False, equipment_slugs=[])
    assert loc == "home"
    assert no_eq is True
    assert raw == []


def test_normalize_home_with_gear_keeps_list():
    loc, no_eq, raw = normalize_location_gear(
        "home", no_equipment=False, equipment_slugs=["dumbbell"]
    )
    assert loc == "home"
    assert no_eq is False
    assert raw == ["dumbbell"]


def test_location_from_venue():
    assert location_from_venue("home") == "home"
    assert location_from_venue("gym") == "gym"
    assert location_from_venue("both") is None
    assert location_from_venue(None) is None


def test_passes_home_dumbbell_rejects_gym_and_extra_machines():
    assert exercise_passes_location_gear(
        venue="home",
        equipment_slugs={"dumbbell"},
        location="home",
        user_slugs=["dumbbell"],
    )
    assert not exercise_passes_location_gear(
        venue="gym",
        equipment_slugs={"dumbbell"},
        location="home",
        user_slugs=["dumbbell"],
    )
    assert not exercise_passes_location_gear(
        venue="home",
        equipment_slugs={"chest-press-machine"},
        location="home",
        user_slugs=["dumbbell"],
    )
    assert not exercise_passes_location_gear(
        venue=None,
        equipment_slugs=set(),
        location="home",
        user_slugs=["dumbbell"],
    )


def test_passes_no_equipment_rejects_linked_gear():
    assert exercise_passes_location_gear(
        venue="home",
        equipment_slugs=set(),
        location="home",
        no_equipment=True,
    )
    assert not exercise_passes_location_gear(
        venue="home",
        equipment_slugs={"dumbbell"},
        location="home",
        no_equipment=True,
    )


def test_passes_gym_rejects_home_venue():
    assert exercise_passes_location_gear(
        venue="gym",
        equipment_slugs={"barbell"},
        location="gym",
    )
    assert not exercise_passes_location_gear(
        venue="home",
        equipment_slugs=set(),
        location="gym",
    )


def test_wizard_inputs_schema_exposes_location_gear():
    out = PlanWizardInputsOut.model_validate(
        {
            "location": "home",
            "no_equipment": False,
            "equipment_list": ["dumbbell"],
        }
    )
    assert out.location == "home"
    assert out.no_equipment is False
    assert out.equipment_list == ["dumbbell"]


def _catalog_engine():
    engine = create_engine("sqlite:///:memory:")
    now = datetime.now().isoformat()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE muscle_groups (
                    id INTEGER PRIMARY KEY,
                    slug TEXT NOT NULL UNIQUE,
                    name_vi TEXT NOT NULL,
                    name_en TEXT,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    parent_id INTEGER,
                    is_filter_only INTEGER NOT NULL DEFAULT 0
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE equipment (
                    id INTEGER PRIMARY KEY,
                    slug TEXT NOT NULL UNIQUE,
                    name_vi TEXT NOT NULL,
                    name_en TEXT,
                    category TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    image_url TEXT,
                    image_source TEXT,
                    image_attribution TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE exercises (
                    id INTEGER PRIMARY KEY,
                    name_vi TEXT NOT NULL,
                    name_en TEXT,
                    muscle_group_id INTEGER NOT NULL,
                    exercise_type TEXT NOT NULL DEFAULT 'main',
                    movement_role TEXT,
                    movement_pattern TEXT,
                    venue TEXT,
                    difficulty INTEGER NOT NULL DEFAULT 2,
                    difficulty_label TEXT,
                    notes_vi TEXT,
                    secondary_muscles TEXT NOT NULL DEFAULT '[]',
                    instruction_vi TEXT,
                    instruction_steps_vi TEXT,
                    common_mistakes_vi TEXT,
                    tips_vi TEXT,
                    gif_url TEXT,
                    image_url TEXT,
                    video_url TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE exercise_equipment (
                    exercise_id INTEGER NOT NULL,
                    equipment_id INTEGER NOT NULL,
                    PRIMARY KEY (exercise_id, equipment_id)
                )
                """
            )
        )
        conn.execute(
            text(
                "INSERT INTO muscle_groups (id, slug, name_vi, name_en, parent_id) VALUES "
                "(1, 'chest', 'Ngực', 'Chest', NULL),"
                "(2, 'chest-upper', 'Ngực trên', 'Upper chest', 1),"
                "(3, 'chest-mid', 'Ngực giữa', 'Mid chest', 1)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO equipment (id, slug, name_vi) VALUES "
                "(1, 'dumbbell', 'Tạ đơn'),"
                "(2, 'chest-press-machine', 'Máy đẩy ngực')"
            )
        )

        def insert_ex(eid, name, mg, venue, role="compound", pattern="h_push", diff=2):
            conn.execute(
                text(
                    "INSERT INTO exercises "
                    "(id,name_vi,muscle_group_id,exercise_type,movement_role,movement_pattern,"
                    "venue,difficulty,is_active,created_at,updated_at) "
                    "VALUES (:id,:n,:mg,'main',:r,:p,:v,:d,1,:c,:u)"
                ),
                {
                    "id": eid,
                    "n": name,
                    "mg": mg,
                    "r": role,
                    "p": pattern,
                    "v": venue,
                    "d": diff,
                    "c": now,
                    "u": now,
                },
            )

        # 1 home + dumbbell (chest-upper)
        insert_ex(1, "Đẩy tạ đơn nhà", 2, "home")
        # 2 gym + machine (chest-upper)
        insert_ex(2, "Máy đẩy ngực gym", 2, "gym")
        # 3 gym + dumbbell (chest-upper)
        insert_ex(3, "Đẩy tạ đơn gym", 2, "gym")
        # 4 home + machine (chest-upper) — extra gear
        insert_ex(4, "Máy đẩy ngực nhà", 2, "home")
        # 5 home bodyweight (chest-upper)
        insert_ex(5, "Chống đẩy nhà", 2, "home")
        # 6 null venue bodyweight
        insert_ex(6, "Bài venue rỗng", 2, None)
        # 7 both + dumbbell (chest-upper)
        insert_ex(7, "Đẩy tạ đơn cả hai", 2, "both")
        # 8 home + dumbbell (chest-mid) — other leaf
        insert_ex(8, "Ép giữa nhà", 3, "home")
        # 9 home bodyweight (chest-mid)
        insert_ex(9, "Chống đẩy giữa", 3, "home")
        # 10 source gym chest-upper for gym swap tests
        insert_ex(10, "Ghế đẩy gym", 2, "gym")

        conn.execute(
            text(
                "INSERT INTO exercise_equipment (exercise_id, equipment_id) VALUES "
                "(1, 1), (2, 2), (3, 1), (4, 2), (7, 1), (8, 1), (10, 1)"
            )
        )
    return engine


def _compound_block() -> BlockSpec:
    return BlockSpec(
        block_key="compound",
        label_vi="Chính",
        plan_section="main",
        movement_role="compound",
        count_min=1,
        count_max=4,
        duration_min_minutes=None,
        duration_max_minutes=None,
        is_optional=False,
        sort_order=1,
    )


def _shortlist(db: Session, **kwargs):
    kw = dict(
        block=_compound_block(),
        split_role="push",
        experience_level=1,
        equipment_slugs=["dumbbell"],
        no_equipment=False,
        ai_suggest_equipment=False,
        location="home",
    )
    kw.update(kwargs)
    return build_shortlist(db, **kw)


def test_shortlist_home_dumbbell_excludes_gym_and_extra_machines():
    engine = _catalog_engine()
    db = sessionmaker(bind=engine)()
    try:
        ids = {it.id for it in _shortlist(db)}
        assert 1 in ids
        assert 5 in ids
        assert 7 in ids
        assert 2 not in ids
        assert 3 not in ids
        assert 4 not in ids
        assert 6 not in ids
    finally:
        db.close()


def test_shortlist_home_no_equipment_excludes_linked_gear():
    engine = _catalog_engine()
    db = sessionmaker(bind=engine)()
    try:
        ids = {it.id for it in _shortlist(db, equipment_slugs=[], no_equipment=True)}
        assert 5 in ids
        assert 1 not in ids
        assert 4 not in ids
        assert 6 not in ids
        assert 2 not in ids
    finally:
        db.close()


def test_shortlist_home_empty_list_same_as_no_equipment():
    engine = _catalog_engine()
    db = sessionmaker(bind=engine)()
    try:
        ids = {it.id for it in _shortlist(db, equipment_slugs=[], no_equipment=False)}
        assert 5 in ids
        assert 1 not in ids
    finally:
        db.close()


def test_alternatives_keep_leaf_muscle_and_home_venue():
    engine = _catalog_engine()
    db = sessionmaker(bind=engine)()
    try:
        items = SearchService(db).exercise_alternatives(
            1,
            limit=8,
            location="home",
            no_equipment=False,
            equipment=["dumbbell"],
        )
        ids = {i["id"] for i in items}
        slugs = {i["body_part"] for i in items}
        venues = {i["venue"] for i in items}
        assert 8 not in ids
        assert slugs <= {"chest-upper"}
        assert "gym" not in venues
        assert 2 not in ids
        assert 3 not in ids
        assert 5 in ids or 7 in ids
    finally:
        db.close()


def test_alternatives_gym_excludes_home_venue():
    engine = _catalog_engine()
    db = sessionmaker(bind=engine)()
    try:
        items = SearchService(db).exercise_alternatives(
            10,
            limit=8,
            location="gym",
            no_equipment=False,
            equipment=["dumbbell"],
        )
        ids = {i["id"] for i in items}
        venues = {i["venue"] for i in items}
        assert "home" not in venues
        assert 1 not in ids
        assert 5 not in ids
        assert 3 in ids
    finally:
        db.close()
