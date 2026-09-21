from dataclasses import dataclass
from typing import Annotated

from fastapi import Cookie, Depends, Header, Request
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.auth_cookies import admin_step_up_valid, read_access_token, uses_cookie_session
from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import Role, decode_token
from app.models.entities import User


@dataclass
class CurrentUser:
    id: str
    role: Role
    email: str | None = None


def _role_from_db(value: str | None) -> Role:
    try:
        return Role(value or Role.USER.value)
    except ValueError:
        return Role.USER


def _user_from_access_token(token: str, db: Session) -> CurrentUser:
    try:
        payload = decode_token(token)
    except JWTError as exc:
        raise UnauthorizedError("Invalid or expired access token") from exc
    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid access token")
    user = db.get(User, user_id)
    if not user:
        raise UnauthorizedError("User not found")
    return CurrentUser(id=str(user.id), role=_role_from_db(user.role), email=user.email)


def get_current_user_optional(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    taptot_access: Annotated[str | None, Cookie()] = None,
    db: Session = Depends(get_db),
) -> CurrentUser | None:
    """Guest when no session. Invalid/expired token → 401 (do not silently guest)."""
    token = taptot_access
    if not token:
        token = read_access_token(request, authorization)
    if not token:
        return None
    return _user_from_access_token(token, db)


def get_current_user(user: CurrentUser | None = Depends(get_current_user_optional)) -> CurrentUser:
    if not user:
        raise UnauthorizedError()
    return user


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role != Role.ADMIN:
        raise ForbiddenError("Admin access required")
    return user


def assert_admin_step_up(request: Request, user: CurrentUser, authorization: str | None = None) -> None:
    """Cookie sessions must re-enter password before admin writes. Bearer (tests) skips."""
    if user.role != Role.ADMIN:
        raise ForbiddenError("Admin access required")
    if not uses_cookie_session(request, authorization):
        return
    if not admin_step_up_valid(request, user.id):
        raise ForbiddenError(
            "Nhập lại mật khẩu để thao tác quản trị.",
            code="admin_step_up",
        )


def require_admin_write(
    request: Request,
    user: CurrentUser = Depends(require_admin),
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    assert_admin_step_up(request, user, authorization)
    return user
