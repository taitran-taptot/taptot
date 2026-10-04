"""Daily IP/device caps for free generation modes (familiarization / free_home)."""

from __future__ import annotations

import logging
import re
import threading
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, TooManyRequestsError

logger = logging.getLogger(__name__)

MSG_DEVICE_INVALID = "Không nhận diện được thiết bị. Vui lòng tải lại trang rồi thử lại."
MSG_DEVICE_DAILY = (
    "Bạn đã tạo đủ lịch nhập môn trên thiết bị này hôm nay. "
    "Mai hãy quay lại, hoặc dùng mã TAPTOT / chương trình đầy đủ để tạo thêm."
)
MSG_IP_DAILY = (
    "Mạng này đã tạo quá nhiều lịch nhập môn hôm nay. "
    "Mai hãy thử lại, hoặc dùng mã TAPTOT để mở chương trình đầy đủ."
)

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)
_VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

_lock = threading.Lock()
_memory: dict[str, int] = {}
_redis: Any | None = None
_redis_failed = False


def _today_key() -> str:
    return datetime.now(_VN_TZ).strftime("%Y%m%d")


def _seconds_until_vn_midnight() -> int:
    now = datetime.now(_VN_TZ)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(60, int((tomorrow - now).total_seconds()))


def normalize_device_id(raw: str | None) -> str:
    value = (raw or "").strip()
    if not _UUID_RE.match(value):
        raise BadRequestError(MSG_DEVICE_INVALID, code="device_id_invalid")
    return value.lower()


def _get_redis():
    global _redis, _redis_failed
    if _redis_failed:
        return None
    if _redis is not None:
        return _redis
    settings = get_settings()
    url = (settings.redis_url or "").strip()
    if not url:
        return None
    try:
        import redis

        client = redis.from_url(url, decode_responses=True)
        client.ping()
        _redis = client
        return _redis
    except Exception as exc:
        logger.warning("fam_gen_cap Redis unavailable, using memory: %s", exc)
        _redis_failed = True
        return None


def _current_count(key: str) -> int:
    client = _get_redis()
    if client is not None:
        try:
            raw = client.get(key)
            return int(raw or 0)
        except Exception as exc:
            logger.warning("fam_gen_cap redis get failed: %s", exc)
    with _lock:
        return int(_memory.get(key, 0))


def _incr(key: str) -> int:
    client = _get_redis()
    ttl = _seconds_until_vn_midnight()
    if client is not None:
        try:
            count = int(client.incr(key))
            if count == 1 or int(client.ttl(key) or -1) < 0:
                client.expire(key, ttl)
            return count
        except Exception as exc:
            logger.warning("fam_gen_cap redis incr failed: %s", exc)
    with _lock:
        count = int(_memory.get(key, 0)) + 1
        _memory[key] = count
        return count


def reset_memory_for_tests() -> None:
    """Clear in-process counters (tests only)."""
    global _redis, _redis_failed
    with _lock:
        _memory.clear()
    _redis = None
    _redis_failed = False


def check_or_raise(*, ip: str, device_id: str) -> None:
    settings = get_settings()
    if not settings.fam_gen_daily_cap_enabled:
        return
    day = _today_key()
    device = normalize_device_id(device_id)
    ip_key = f"fam:gen:ip:{(ip or 'unknown')[:64]}:{day}"
    dev_key = f"fam:gen:dev:{device}:{day}"

    if _current_count(dev_key) >= max(1, int(settings.fam_gen_daily_device_limit)):
        raise TooManyRequestsError(MSG_DEVICE_DAILY, code="fam_gen_device_daily")
    if _current_count(ip_key) >= max(1, int(settings.fam_gen_daily_ip_limit)):
        raise TooManyRequestsError(MSG_IP_DAILY, code="fam_gen_ip_daily")


def record_success(*, ip: str, device_id: str) -> None:
    settings = get_settings()
    if not settings.fam_gen_daily_cap_enabled:
        return
    day = _today_key()
    device = normalize_device_id(device_id)
    _incr(f"fam:gen:ip:{(ip or 'unknown')[:64]}:{day}")
    _incr(f"fam:gen:dev:{device}:{day}")
