from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.exceptions import BadRequestError
from app.core.migrations.ensures import ensure_pushup_challenge_entries
from app.models.base import Base
from app.services.pushup_challenge import (
    discount_percent_for_reps,
    finish_session,
    start_session,
    verify_ticket,
)


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_finish_rejects_too_many_reps_for_elapsed():
    db = _db()
    started = datetime(2026, 1, 1, tzinfo=UTC)
    sid = start_session(db, now=started)["session_id"]
    try:
        finish_session(db, session_id=sid, reps=20, now=started + timedelta(seconds=1))
        raise AssertionError("expected BadRequestError")
    except BadRequestError:
        pass


def test_discount_bands():
    assert discount_percent_for_reps(0) == 5
    assert discount_percent_for_reps(20) == 5
    assert discount_percent_for_reps(21) == 10
    assert discount_percent_for_reps(50) == 10
    assert discount_percent_for_reps(51) == 15


def test_finish_issues_ticket_and_verify():
    db = _db()
    started = datetime(2026, 1, 1, tzinfo=UTC)
    sid = start_session(db, now=started)["session_id"]
    finished = finish_session(db, session_id=sid, reps=8, now=started + timedelta(seconds=20))
    assert finished["percent"] == 5
    assert finished["ticket"]
    assert verify_ticket(db, finished["ticket"])["valid"] is True
    assert verify_ticket(db, "not-a-real-ticket-value-here")["valid"] is False


def test_verify_rejects_forged_ticket():
    db = _db()
    assert verify_ticket(db, "a" * 40)["valid"] is False


def test_ensure_drops_entries_table():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE pushup_challenge_entries (id INTEGER PRIMARY KEY)"))
    ensure_pushup_challenge_entries(engine)
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='pushup_challenge_entries'")
        ).fetchone()
    assert row is None
