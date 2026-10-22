"""Five concurrent workout generations; the sixth waits, then times out."""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

import pytest
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import AppException, TooManyRequestsError
from app.services import gen_queue
from app.services.gen_queue import (
    MSG_GEN_QUEUE,
    acquire_or_raise,
    active_count,
    generation_slot,
    get_db_for_generate,
    release,
)


@pytest.fixture(autouse=True)
def _reset_gate(monkeypatch: pytest.MonkeyPatch):
    gen_queue.reset_for_tests()
    monkeypatch.setattr(get_settings(), "gen_max_concurrent", 5)
    monkeypatch.setattr(get_settings(), "gen_queue_wait_seconds", 2)
    yield
    gen_queue.reset_for_tests()


def test_removed_openai_gate_settings_are_gone():
    fields = Settings.model_fields
    assert "ai_max_concurrent" not in fields
    assert "ai_gate_wait_seconds" not in fields
    assert "ai_retry_attempts" not in fields
    assert "ai_retry_base_seconds" not in fields
    assert fields["gen_max_concurrent"].default == 5
    assert fields["gen_queue_wait_seconds"].default == 60


def test_sixth_waits_until_a_slot_frees():
    ready = threading.Barrier(6)
    release_holders = threading.Event()
    sixth_is_waiting = threading.Event()

    def hold() -> None:
        acquire_or_raise()
        try:
            ready.wait(timeout=2)
            release_holders.wait(timeout=2)
        finally:
            release()

    threads = [threading.Thread(target=hold, daemon=True) for _ in range(5)]
    for thread in threads:
        thread.start()
    deadline = time.monotonic() + 2
    while active_count() < 5 and time.monotonic() < deadline:
        time.sleep(0.01)
    assert active_count() == 5

    waited: dict[str, float] = {}

    def sixth() -> None:
        ready.wait(timeout=2)
        sixth_is_waiting.set()
        started = time.monotonic()
        acquire_or_raise()
        waited["seconds"] = time.monotonic() - started
        release()

    waiter = threading.Thread(target=sixth, daemon=True)
    waiter.start()
    assert sixth_is_waiting.wait(timeout=2)
    time.sleep(0.2)
    assert "seconds" not in waited
    release_holders.set()
    waiter.join(timeout=2)
    for thread in threads:
        thread.join(timeout=2)
    assert waited["seconds"] >= 0.15
    assert active_count() == 0


def test_wait_over_one_minute_budget_raises_without_taking_a_slot(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(get_settings(), "gen_max_concurrent", 1)
    monkeypatch.setattr(get_settings(), "gen_queue_wait_seconds", 0.05)
    acquire_or_raise()
    try:
        started = time.monotonic()
        with pytest.raises(TooManyRequestsError) as exc:
            acquire_or_raise()
        assert exc.value.status_code == 429
        assert exc.value.code == "gen_queue_timeout"
        assert exc.value.message == MSG_GEN_QUEUE
        assert time.monotonic() - started < 1
        assert active_count() == 1
    finally:
        release()
    assert active_count() == 0


def test_slot_released_when_generation_fails():
    slot = generation_slot()
    next(slot)
    assert active_count() == 1
    with pytest.raises(RuntimeError, match="gen failed"):
        slot.throw(RuntimeError("gen failed"))
    assert active_count() == 0
    acquire_or_raise()
    release()


def test_one_request_holds_a_single_slot(monkeypatch: pytest.MonkeyPatch):
    db = MagicMock()
    monkeypatch.setattr("app.core.database.SessionLocal", lambda: db)
    seen: dict[str, object] = {}
    app = FastAPI()

    @app.post("/gen")
    def _gen(
        first: Session = Depends(get_db_for_generate),
        second: Session = Depends(get_db_for_generate),
    ) -> dict[str, bool]:
        seen["active"] = active_count()
        seen["same"] = first is second
        return {"ok": True}

    response = TestClient(app).post("/gen")
    assert response.status_code == 200
    assert seen["active"] == 1
    assert seen["same"] is True
    assert active_count() == 0
    db.close.assert_called_once()


def test_full_queue_does_not_open_db_or_generate(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(get_settings(), "gen_max_concurrent", 1)
    monkeypatch.setattr(get_settings(), "gen_queue_wait_seconds", 0)
    opened = {"n": 0}

    def fail_if_opened() -> MagicMock:
        opened["n"] += 1
        raise AssertionError("database opened while the queue was full")

    monkeypatch.setattr("app.core.database.SessionLocal", fail_if_opened)
    acquire_or_raise()
    try:
        app = FastAPI()

        @app.exception_handler(AppException)
        async def _app_error(_request, exc: AppException) -> JSONResponse:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.message, "code": exc.code},
            )

        @app.post("/gen")
        def _gen(_db: Session = Depends(get_db_for_generate)) -> dict[str, bool]:
            raise AssertionError("must not generate")

        response = TestClient(app).post("/gen")
    finally:
        release()

    assert response.status_code == 429
    assert response.json()["detail"] == MSG_GEN_QUEUE
    assert opened["n"] == 0
    assert active_count() == 0
