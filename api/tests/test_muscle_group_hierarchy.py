"""Tests for muscle group hierarchy filter expansion."""

import pytest
from sqlalchemy import create_engine, text

from app.core.migrations import ensure_muscle_groups_hierarchy
from app.services.search_service import expand_muscle_group_ids


@pytest.fixture()
def hierarchy_db():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE muscle_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                CREATE TABLE exercises (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name_vi TEXT NOT NULL,
                    muscle_group_id INTEGER NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1
                )
                """
            )
        )
    ensure_muscle_groups_hierarchy(engine)
    return engine


def test_expand_parent_includes_children(hierarchy_db):
    from sqlalchemy.orm import Session

    db = Session(bind=hierarchy_db)
    try:
        chest = db.execute(text("SELECT id FROM muscle_groups WHERE slug = 'chest'")).scalar()
        upper = db.execute(text("SELECT id FROM muscle_groups WHERE slug = 'chest-upper'")).scalar()
        expanded = expand_muscle_group_ids(db, [int(chest)])
        assert int(upper) in expanded
    finally:
        db.close()


def test_filter_only_parents_seeded(hierarchy_db):
    with hierarchy_db.begin() as conn:
        row = conn.execute(
            text("SELECT is_filter_only FROM muscle_groups WHERE slug = 'chest'")
        ).scalar()
        assert int(row) == 1
