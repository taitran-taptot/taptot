"""HttpOnly session cookies. JS must not read access/refresh tokens."""

from datetime import timedelta

from fastapi import Response
from jose import JWTError
from starlette.requests import Request

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.core.security import ADMIN_STEP_UP_MINUTES, create_access_token, decode_token

settings = get_settings()

ACCESS_COOKIE = "taptot_access"
REFRESH_COOKIE = "taptot_refresh"
ADMIN_COOKIE = "taptot_admin"


def _secure() -> bool:
    return (settings.app_env or "").lower() in {"production", "prod"}


def _cookie_base(*, path: str, max_age: int) -> dict:
    return {
        "httponly": True,
        "secure": _secure(),
        "samesite": "lax",
        "path": path,
        "max_age": max_age,
    }


def set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    access_age = int(settings.access_token_expire_minutes * 60)
    refresh_age = int(settings.refresh_token_expire_days * 86400)
    response.set_cookie(ACCESS_COOKIE, access, **_cookie_base(path="/", max_age=access_age))
    response.set_cookie(
        REFRESH_COOKIE,
        refresh,
        **_cookie_base(path="/api/v1/auth", max_age=refresh_age),
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")
    response.delete_cookie(ADMIN_COOKIE, path="/")


def set_admin_cookie(response: Response, user_id: str, role: str) -> None:
    token = create_access_token(
        user_id,
        role,
        extra={"type": "admin_step", "step": "write"},
    )
    max_age = int(timedelta(minutes=ADMIN_STEP_UP_MINUTES).total_seconds())
    response.set_cookie(ADMIN_COOKIE, token, **_cookie_base(path="/", max_age=max_age))


def clear_admin_cookie(response: Response) -> None:
    response.delete_cookie(ADMIN_COOKIE, path="/")


def read_access_token(request: Request, authorization: str | None) -> str | None:
    cookie = request.cookies.get(ACCESS_COOKIE)
    if cookie:
        return cookie
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        if not token:
            raise UnauthorizedError("Invalid or expired access token")
        return token
    return None


def read_refresh_token(request: Request, body_token: str | None = None) -> str | None:
    if body_token and body_token.strip():
        return body_token.strip()
    cookie = request.cookies.get(REFRESH_COOKIE)
    return cookie.strip() if cookie else None


def uses_cookie_session(request: Request, authorization: str | None) -> bool:
    has_bearer = bool(authorization and authorization.startswith("Bearer ") and authorization[7:].strip())
    if has_bearer:
        return False
    return bool(request.cookies.get(ACCESS_COOKIE))


def admin_step_up_valid(request: Request, user_id: str) -> bool:
    raw = request.cookies.get(ADMIN_COOKIE)
    if not raw:
        return False
    try:
        payload = decode_token(raw)
    except JWTError:
        return False
    return (
        payload.get("type") == "admin_step"
        and payload.get("sub") == user_id
        and payload.get("step") == "write"
    )
