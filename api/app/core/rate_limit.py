import logging
import time
from collections import defaultdict, deque

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import get_settings
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)

_AUTH_SUFFIXES = (
    "/auth/login",
    "/auth/register",
    "/auth/forgot-password",
    "/auth/reset-password",
    "/auth/oauth",
)


def classify_rate_limit(path: str, method: str = "GET") -> tuple[str, int]:
    """Return (bucket_prefix, max_requests) for this path."""
    settings = get_settings()
    method = (method or "GET").upper()
    normalized = path.rstrip("/") or "/"
    if any(normalized.endswith(p) or p in normalized for p in _AUTH_SUFFIXES):
        return "auth", 20
    if method == "POST" and normalized.endswith("/ai/generate-workout-schedule"):
        return "ai-gen", max(1, int(settings.ai_generate_rate_limit))
    if method == "POST" and normalized.endswith("/ai/chat"):
        return "ai-chat", max(1, int(settings.ai_chat_rate_limit))
    if method == "POST" and normalized.endswith("/plans"):
        return "plan-create", max(1, int(settings.public_plan_create_rate_limit))
    return "ip", settings.rate_limit_requests


def client_ip(request: Request, *, trust_forwarded: bool | None = None) -> str:
    settings = get_settings()
    if trust_forwarded is None:
        trust_forwarded = bool(settings.rate_limit_trust_x_forwarded_for)
    if trust_forwarded:
        forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
        if forwarded:
            return forwarded[:64]
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        settings = get_settings()
        self.max_requests = settings.rate_limit_requests
        self.window = settings.rate_limit_window_seconds
        self.redis_url = settings.redis_url
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._redis = None
        if self.redis_url:
            try:
                import redis

                self._redis = redis.from_url(self.redis_url, decode_responses=True)
                self._redis.ping()
                logger.info("Rate limiter using Redis")
            except Exception as exc:
                logger.warning("Redis unavailable, using in-memory rate limit: %s", exc)
                self._redis = None

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path.startswith(("/health", "/docs", "/openapi.json", "/redoc")):
            return await call_next(request)

        bucket, max_req = classify_rate_limit(request.url.path, request.method)
        ip = client_ip(request)
        remaining = self._check_limit(f"{bucket}:{ip}", max_req, self.window)
        if remaining < 0:
            raise AppException("Rate limit exceeded", status_code=429)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(max_req)
        response.headers["X-RateLimit-Remaining"] = str(max(remaining, 0))
        return response

    def _check_limit(self, client_ip: str, max_requests: int | None = None, window: int | None = None) -> int:
        limit = max_requests if max_requests is not None else self.max_requests
        win = window if window is not None else self.window
        if self._redis:
            key = f"rl:{client_ip}"
            count = int(self._redis.incr(key))
            ttl = int(self._redis.ttl(key) or -1)
            if ttl < 0:
                self._redis.expire(key, win)
            return limit - count

        now = time.time()
        hits = self._hits[client_ip]
        while hits and hits[0] <= now - win:
            hits.popleft()
        if len(hits) >= limit:
            return -1
        hits.append(now)
        return limit - len(hits)
