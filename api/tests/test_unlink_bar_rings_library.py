"""Kho bài tập: inverted row / assisted pull-ups must not sit under xà or vòng."""

from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.migrations.ensures import ensure_unlink_bar_rings_library_mismatches
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
                    created_by INTEGER,
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
                "(1, 'back', 'Lưng', 'Back')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO equipment (id, slug, name_vi, name_en, category) VALUES "
                "(1, 'pull-up-bar', 'Xà đơn', 'Pull-up bar', 'Body Weight'),"
                "(2, 'gymnastic-rings', 'Vòng treo', 'Rings', 'Body Weight'),"
                "(3, 'resistance-band-2', 'Dây kháng lực', 'Band', 'Phụ kiện tập luyện'),"
                "(4, 'lat-pulldown', 'Máy kéo xô', 'Lat pulldown', 'Máy tập')"
            )
        )

        def insert_ex(eid, name_en, name_vi):
            conn.execute(
                text(
                    "INSERT INTO exercises "
                    "(id,name_vi,name_en,muscle_group_id,exercise_type,venue,difficulty,"
                    "is_active,created_at,updated_at) "
                    "VALUES (:id,:vi,:en,1,'main','home',2,1,:c,:u)"
                ),
                {
                    "id": eid,
                    "vi": name_vi,
                    "en": name_en,
                    "c": now,
                    "u": now,
                },
            )

        insert_ex(1, "Pull-up Bar Inverted Row", "Kéo người nằm trên xà")
        insert_ex(2, "Machine Assisted Pull Up", "Hít xà trợ lực máy")
        insert_ex(3, "Band Assisted Pull-Up", "Hít xà trợ lực dây")
        insert_ex(4, "Pull Ups", "Hít xà")
        insert_ex(5, "Ring Row", "Chèo vòng treo")
        insert_ex(6, "Wide-Grip Pull-Up", "Hít xà tay rộng")
        insert_ex(7, "Neutral-Grip Pull-Up", "Hít xà nắm dọc")
        conn.execute(
            text(
                "INSERT INTO exercise_equipment (exercise_id, equipment_id) VALUES "
                "(1, 1), (1, 2), (2, 1), (2, 4), (3, 1), (3, 3), (4, 1), (5, 2), "
                "(6, 1), (6, 2), (7, 1)"
            )
        )
    return engine


def test_unlink_drops_bar_and_rings_but_keeps_other_gear():
    engine = _engine()
    ensure_unlink_bar_rings_library_mismatches(engine)
    with engine.begin() as conn:
        links = {
            (int(r[0]), str(r[1]))
            for r in conn.execute(
                text(
                    """
                    SELECT ee.exercise_id, eq.slug
                    FROM exercise_equipment ee
                    JOIN equipment eq ON eq.id = ee.equipment_id
                    """
                )
            ).fetchall()
        }
    assert (1, "pull-up-bar") not in links
    assert (1, "gymnastic-rings") not in links
    assert (2, "pull-up-bar") not in links
    assert (3, "pull-up-bar") not in links
    assert (2, "lat-pulldown") in links
    assert (3, "resistance-band-2") in links
    assert (4, "pull-up-bar") in links
    assert (5, "gymnastic-rings") in links
    assert (6, "pull-up-bar") not in links
    assert (6, "gymnastic-rings") not in links
    assert (7, "pull-up-bar") not in links


def test_library_filter_hides_unlinked_rows():
    engine = _engine()
    ensure_unlink_bar_rings_library_mismatches(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        page = PaginationParams(page=1, page_size=50)
        bar, _ = SearchService(db).search_exercises(page, equipment="pull-up-bar")
        rings, _ = SearchService(db).search_exercises(page, equipment="gymnastic-rings")
        bar_names = {item["name_en"] for item in bar}
        ring_names = {item["name_en"] for item in rings}
        denied = {
            "Pull-up Bar Inverted Row",
            "Machine Assisted Pull Up",
            "Band Assisted Pull-Up",
            "Wide-Grip Pull-Up",
            "Neutral-Grip Pull-Up",
        }
        assert denied.isdisjoint(bar_names)
        assert denied.isdisjoint(ring_names)
        assert "Pull Ups" in bar_names
        assert "Ring Row" in ring_names
    finally:
        db.close()
