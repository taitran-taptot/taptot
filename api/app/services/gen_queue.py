"""In-process cap on simultaneous workout generations.

One uvicorn worker shares this gate. Waiters block on the request thread, so the
builder overlay stays up until a slot opens or the wait expires. A full queue
does not open a database session and does not reserve a redeem code.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import TooManyRequestsError

MSG_GEN_QUEUE = "Đang có quá nhiều người tạo lịch. Hãy đợi 5 phút rồi thử lại."

_lock = threading.Condition()
_active = 0


def reset_for_tests() -> None:
    global _active
    with _lock:
        _active = 0
        _lock.notify_all()


def active_count() -> int:
    with _lock:
        return _active


def acquire_or_raise() -> None:
    settings = get_settings()
    limit = max(1, int(settings.gen_max_concurrent))
    wait_seconds = max(0.0, float(settings.gen_queue_wait_seconds))
    deadline = time.monotonic() + wait_seconds
    with _lock:
        global _active
        while _active >= limit:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TooManyRequestsError(MSG_GEN_QUEUE, code="gen_queue_timeout")
            _lock.wait(remaining)
        _active += 1


def release() -> None:
    global _active
    with _lock:
        if _active > 0:
            _active -= 1
        _lock.notify(1)


def generation_slot() -> Generator[None, None, None]:
    """Block until a generation slot is free. Database work starts only after this yields."""
    acquire_or_raise()
    try:
        yield
    finally:
        release()


def get_db_for_generate(_slot: None = Depends(generation_slot)) -> Generator[Session, None, None]:
    """Open the request session only after a generation slot is held."""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
