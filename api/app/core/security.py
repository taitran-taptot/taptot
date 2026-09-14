import hashlib
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import bcrypt
from jose import jwt

from app.core.config import get_settings

settings = get_settings()


class Role(str, Enum):
    USER = "user"
    TRAINER = "trainer"
    ADMIN = "admin"


def hash_password(password: str) -> str:
    # bcrypt only uses the first 72 bytes
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str, role: str, extra: dict[str, Any] | None = None) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "role": role, "type": "access", "exp": expire}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: str) -> str:
    import secrets

    expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": subject,
        "type": "refresh",
        "exp": expire,
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_oauth_state(provider: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=10)
    payload = {"type": "oauth_state", "provider": provider, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def verify_oauth_state(state: str, provider: str) -> None:
    payload = decode_token(state)
    if payload.get("type") != "oauth_state" or payload.get("provider") != provider:
        raise ValueError("Invalid OAuth state")


def generate_opaque_token() -> str:
    import secrets

    return secrets.token_urlsafe(32)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
