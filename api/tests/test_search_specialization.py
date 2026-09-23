"""Public kho-bài-tập specialization tabs (gym / calisthenic / bands / sport / martial)."""

from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.migrations.ensures import (
    SPEC_LIBRARY_REACTIVATE_NAMES,
    ensure_reactivate_spec_library_exercises,
)
from app.core.pagination import PaginationParams
from app.services.search_service import SearchService


def _engine():
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
                    sort_order INTEGER NOT NULL DEFAULT 0
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
                "INSERT INTO muscle_groups (id, slug, name_vi, name_en) VALUES "
                "(1, 'chest', 'Ngực', 'Chest')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO equipment (id, slug, name_vi, name_en, category) VALUES "
                "(1, 'gymnastic-rings', 'Vòng treo', 'Rings', 'Body Weight'),"
                "(2, 'resistance-band-1', 'Dây kháng lực', 'Band', 'Phụ kiện tập luyện'),"
                "(3, 'barbell', 'Tạ đòn', 'Barbell', 'Tạ tự do'),"
                "(4, 'functional-trainer', 'Máy cáp', 'Cable', 'Máy tập')"
            )
        )

        def insert_ex(eid, name_en, name_vi, *, venue, etype="main", active=1):
            conn.execute(
                text(
                    "INSERT INTO exercises "
                    "(id,name_vi,name_en,muscle_group_id,exercise_type,venue,difficulty,"
                    "is_active,created_at,updated_at) "
                    "VALUES (:id,:vi,:en,1,:t,:v,2,:a,:c,:u)"
                ),
                {
                    "id": eid,
                    "vi": name_vi,
                    "en": name_en,
                    "t": etype,
                    "v": venue,
                    "a": active,
                    "c": now,
                    "u": now,
                },
            )

        insert_ex(1, "Ring Dip", "Dip vòng treo", venue="home")
        insert_ex(2, "Band Curl", "Cuốn dây", venue="both")
        insert_ex(3, "Freestyle Swim", "Bơi sải", venue="both", etype="cardio")
        insert_ex(4, "Shadow Boxing", "Đấm bóng tưởng tượng", venue="both", etype="cardio")
        insert_ex(5, "Push-up", "Chống đẩy", venue="home")
        insert_ex(6, "Barbell Bench", "Đẩy ngực tạ đòn", venue="gym")
        insert_ex(7, "Ski Erg", "Máy Ski Erg", venue="gym", etype="cardio")
        insert_ex(8, "Hiking", "Đi bộ đường dài", venue="both", etype="cardio")
        insert_ex(9, "Inactive Swim", "Bơi ngửa", venue="both", etype="cardio", active=0)
        conn.execute(
            text(
                "UPDATE exercises SET name_en = 'Backstroke Swim' WHERE id = 9"
            )
        )
        insert_ex(10, "Sled Push", "Đẩy xe trượt", venue="gym")
        conn.execute(
            text(
                "INSERT INTO exercise_equipment (exercise_id, equipment_id) VALUES "
                "(1, 1), (2, 2), (6, 3), (7, 4)"
            )
        )
    return engine


def _search(db, spec: str | None):
    items, _total = SearchService(db).search_exercises(
        PaginationParams(page=1, page_size=50),
        specialization=spec,
    )
    return {i["name_en"] for i in items}


def test_spec_gym_excludes_home_only():
    db = sessionmaker(bind=_engine())()
    try:
        names = _search(db, "gym")
        assert "Barbell Bench" in names
        assert "Band Curl" in names
        assert "Push-up" not in names
        assert "Ring Dip" not in names
    finally:
        db.close()


def test_spec_calisthenic_rings_and_unlinked_strength():
    db = sessionmaker(bind=_engine())()
    try:
        names = _search(db, "calisthenic")
        assert "Ring Dip" in names
        assert "Push-up" in names
        assert "Freestyle Swim" not in names
        assert "Shadow Boxing" not in names
        assert "Band Curl" not in names
        assert "Barbell Bench" not in names
        assert "Sled Push" not in names
    finally:
        db.close()


def test_spec_other_is_bands():
    db = sessionmaker(bind=_engine())()
    try:
        names = _search(db, "other")
        assert names == {"Band Curl"}
    finally:
        db.close()


def test_spec_sport_swim_hike_not_gym_machine_or_boxing():
    db = sessionmaker(bind=_engine())()
    try:
        names = _search(db, "sport")
        assert "Freestyle Swim" in names
        assert "Hiking" in names
        assert "Ski Erg" not in names
        assert "Shadow Boxing" not in names
        assert "Push-up" not in names
    finally:
        db.close()


def test_spec_martial_boxing():
    db = sessionmaker(bind=_engine())()
    try:
        names = _search(db, "martial")
        assert names == {"Shadow Boxing"}
    finally:
        db.close()


def test_reactivate_allowlist_enables_inactive_swim():
    engine = _engine()
    db = sessionmaker(bind=engine)()
    try:
        assert "Backstroke Swim" not in _search(db, "sport")
        ensure_reactivate_spec_library_exercises(engine)
        db.expire_all()
        assert "Backstroke Swim" in _search(db, "sport")
        assert set(SPEC_LIBRARY_REACTIVATE_NAMES)
    finally:
        db.close()
