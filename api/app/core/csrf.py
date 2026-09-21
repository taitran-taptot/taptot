"""Reject cross-site mutating requests that carry session cookies."""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from urllib.parse import urlparse

from app.core.auth_cookies import ACCESS_COOKIE, ADMIN_COOKIE, REFRESH_COOKIE
from app.core.config import get_settings

_SAFE = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def _allowed_origins() -> set[str]:
    settings = get_settings()
    origins = {o.rstrip("/") for o in settings.cors_origin_list}
    if settings.frontend_url:
        origins.add(settings.frontend_url.rstrip("/"))
    return origins


def _origin_host_allowed(value: str) -> bool:
    raw = (value or "").strip()
    if not raw:
        return False
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else raw.rstrip("/")
    if origin in _allowed_origins():
        return True
    settings = get_settings()
    if (settings.app_env or "").lower() in {"development", "dev", "local"}:
        host = (parsed.hostname or "").lower()
        return host in {"localhost", "127.0.0.1"}
    return False


class CsrfOriginMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method.upper() in _SAFE:
            return await call_next(request)
        cookies = request.cookies
        if not (cookies.get(ACCESS_COOKIE) or cookies.get(REFRESH_COOKIE) or cookies.get(ADMIN_COOKIE)):
            return await call_next(request)
        origin = request.headers.get("origin") or ""
        referer = request.headers.get("referer") or ""
        if origin:
            if not _origin_host_allowed(origin):
                return JSONResponse({"detail": "CSRF origin bị từ chối", "code": "csrf"}, status_code=403)
            return await call_next(request)
        if referer and not _origin_host_allowed(referer):
            return JSONResponse({"detail": "CSRF origin bị từ chối", "code": "csrf"}, status_code=403)
        return await call_next(request)
