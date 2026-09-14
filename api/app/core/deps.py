from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import Role, decode_token
from app.models.entities import User


@dataclass
class CurrentUser:
    id: str
    role: Role
    email: str | None = None


def get_current_user_optional(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> CurrentUser | None:
    """Guest when no Authorization header. Invalid/expired Bearer → 401 (do not silently guest)."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise UnauthorizedError("Invalid access token")
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
    return CurrentUser(id=str(user.id), role=Role(user.role), email=user.email)


def get_current_user(user: CurrentUser | None = Depends(get_current_user_optional)) -> CurrentUser:
    if not user:
        raise UnauthorizedError()
    return user


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role != Role.ADMIN:
        raise ForbiddenError("Admin access required")
    return user


def require_trainer(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role not in {Role.TRAINER, Role.ADMIN}:
        raise ForbiddenError("Trainer access required")
    return user
