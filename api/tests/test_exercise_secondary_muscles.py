"""Tests for exercises.secondary_muscles column + detail serialize."""

from sqlalchemy import create_engine, text

from app.core.migrations import ensure_exercise_secondary_muscles
from app.services.search_service import _as_str_list


def test_as_str_list_normalizes():
    assert _as_str_list(None) == []
    assert _as_str_list([]) == []
    assert _as_str_list([" Vai trước ", "", "Ngực"]) == ["Vai trước", "Ngực"]
    assert _as_str_list('["Tay sau","Vai"]') == ["Tay sau", "Vai"]
    assert _as_str_list("[]") == []


def test_ensure_adds_column_sqlite(tmp_path):
    db = tmp_path / "sec.db"
    engine = create_engine(f"sqlite:///{db}")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE exercises (
                    id INTEGER PRIMARY KEY,
                    name_vi TEXT NOT NULL
                )
                """
            )
        )
    ensure_exercise_secondary_muscles(engine)
    with engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(exercises)")).fetchall()]
        assert "secondary_muscles" in cols
    # Idempotent
    ensure_exercise_secondary_muscles(engine)


def test_serialize_detail_reads_secondary():
    from types import SimpleNamespace

    from app.services.search_service import SearchService

    mg = SimpleNamespace(id=1, slug="chest", name_vi="Ngực", name_en="Chest")
    ex = SimpleNamespace(
        id=1,
        name_vi="Ép ngực",
        name_en="Bench",
        exercise_type="main",
        movement_role="compound",
        movement_pattern="h_push",
        difficulty=2,
        difficulty_label=None,
        notes_vi=None,
        secondary_muscles=["Vai trước", "Tay sau"],
        gif_url=None,
        video_url=None,
        image_url=None,
        instruction_vi=None,
        instruction_steps_vi=None,
        common_mistakes_vi=None,
        tips_vi=None,
    )

    class _FakeSvc(SearchService):
        def __init__(self):
            pass

        def _equipment_names(self, _eid):
            return []

        def _equipment_slugs(self, _eid):
            return []

    svc = _FakeSvc()
    detail = svc._serialize_exercise(ex, mg, detail=True)
    assert detail["secondary_muscles"] == ["Vai trước", "Tay sau"]
    list_item = svc._serialize_exercise(ex, mg, detail=False)
    assert "secondary_muscles" not in list_item


def test_serialize_detail_parses_json_string_secondary():
    from types import SimpleNamespace

    from app.services.search_service import SearchService

    mg = SimpleNamespace(id=1, slug="chest", name_vi="Ngực", name_en=None)
    ex = SimpleNamespace(
        id=1,
        name_vi="Ép ngực",
        name_en="",
        exercise_type="main",
        movement_role=None,
        movement_pattern=None,
        difficulty=2,
        difficulty_label=None,
        notes_vi=None,
        secondary_muscles='["Vai trước"]',
        gif_url=None,
        video_url=None,
        image_url=None,
        instruction_vi=None,
        instruction_steps_vi=None,
        common_mistakes_vi=None,
        tips_vi=None,
    )

    class _FakeSvc(SearchService):
        def __init__(self):
            pass

        def _equipment_names(self, _eid):
            return []

        def _equipment_slugs(self, _eid):
            return []

    detail = _FakeSvc()._serialize_exercise(ex, mg, detail=True)
    assert detail["secondary_muscles"] == ["Vai trước"]
