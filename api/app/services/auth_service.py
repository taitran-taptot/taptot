import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ConflictError, UnauthorizedError
from app.core.security import (
    Role,
    create_access_token,
    create_oauth_state,
    create_refresh_token,
    decode_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    verify_oauth_state,
    verify_password,
)
from app.services.email_service import EmailService
from app.models.entities import (
    AuthSession,
    EmailVerificationToken,
    OAuthAccount,
    PasswordResetToken,
    User,
    UserProfile,
)

settings = get_settings()
SUPPORTED_OAUTH_PROVIDERS = frozenset({"google", "facebook"})


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def register(
        self,
        email: str,
        password: str,
        display_name: str,
    ) -> tuple[User, str, str]:
        if self.db.query(User).filter(User.email == email).first():
            raise ConflictError("Không thể tạo tài khoản với thông tin đã cung cấp")

        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            email=email,
            password_hash=hash_password(password),
            display_name=display_name,
            role=Role.USER.value,
            created_at=datetime.now(UTC),
        )
        profile = UserProfile(user_id=user_id, experience_level="beginner", updated_at=datetime.now(UTC))
        self.db.add(user)
        self.db.add(profile)
        self.db.commit()

        verify_token = self._create_email_verification_token(user)
        if user.email:
            EmailService().send_verification(user.email, self.build_verify_url(verify_token))
        return user, *self.issue_tokens(user), verify_token

    def login(self, email: str, password: str) -> tuple[str, str]:
        user = self.db.query(User).filter(User.email == email).first()
        if not user or not user.password_hash or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")
        return self.issue_tokens(user)

    def refresh(self, refresh_token: str) -> tuple[str, str]:
        try:
            token_payload = decode_token(refresh_token)
        except JWTError as exc:
            raise UnauthorizedError("Invalid refresh token") from exc

        if token_payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid token type")

        token_hash = hash_token(refresh_token)
        session = (
            self.db.query(AuthSession)
            .filter(
                AuthSession.token_hash == token_hash,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > datetime.now(UTC),
            )
            .first()
        )
        if not session:
            raise UnauthorizedError("Refresh token revoked or expired")

        user = self.db.get(User, token_payload.get("sub"))
        if not user:
            raise UnauthorizedError("User not found")

        session.revoked_at = datetime.now(UTC)
        self.db.commit()
        return self.issue_tokens(user)

    def logout(self, refresh_token: str) -> None:
        token_hash = hash_token(refresh_token)
        session = (
            self.db.query(AuthSession)
            .filter(AuthSession.token_hash == token_hash, AuthSession.revoked_at.is_(None))
            .first()
        )
        if session:
            session.revoked_at = datetime.now(UTC)
            self.db.commit()

    def logout_all(self, user_id: str) -> int:
        sessions = (
            self.db.query(AuthSession)
            .filter(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .all()
        )
        now = datetime.now(UTC)
        for session in sessions:
            session.revoked_at = now
        self.db.commit()
        return len(sessions)

    def change_password(self, user_id: str, current_password: str, new_password: str) -> None:
        user = self.db.get(User, user_id)
        if not user or not user.password_hash or not verify_password(current_password, user.password_hash):
            raise UnauthorizedError("Current password is incorrect")
        user.password_hash = hash_password(new_password)
        self.logout_all(user_id)
        self.db.commit()

    def update_profile(
        self,
        user_id: str,
        *,
        display_name: str | None = None,
        email: str | None = None,
    ) -> User:
        user = self.db.get(User, user_id)
        if not user:
            raise UnauthorizedError()

        if display_name is not None:
            user.display_name = display_name

        if email is not None and email != user.email:
            if self.db.query(User).filter(User.email == email, User.id != user_id).first():
                raise ConflictError("Email already in use")
            user.email = email
            user.email_verified_at = None

        self.db.commit()
        self.db.refresh(user)
        return user

    def forgot_password(self, email: str) -> str | None:
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return None
        token = self._create_password_reset_token(user)
        EmailService().send_password_reset(email, self.build_reset_url(token))
        return token

    def reset_password(self, token: str, new_password: str) -> None:
        record = self._get_valid_token(PasswordResetToken, token)
        user = self.db.get(User, record.user_id)
        if not user:
            raise BadRequestError("Invalid reset token")

        user.password_hash = hash_password(new_password)
        record.used_at = datetime.now(UTC)
        self.logout_all(user.id)
        self.db.commit()

    def verify_email(self, token: str) -> User:
        record = self._get_valid_token(EmailVerificationToken, token)
        user = self.db.get(User, record.user_id)
        if not user:
            raise BadRequestError("Invalid verification token")

        user.email_verified_at = datetime.now(UTC)
        record.used_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(user)
        return user

    def resend_verification(self, user_id: str) -> str:
        user = self.db.get(User, user_id)
        if not user:
            raise UnauthorizedError()
        if user.email_verified_at:
            raise BadRequestError("Email already verified")
        token = self._create_email_verification_token(user)
        if user.email:
            EmailService().send_verification(user.email, self.build_verify_url(token))
        return token

    def get_oauth_authorize_url(self, provider: str, redirect_uri: str | None = None) -> dict[str, str]:
        if provider not in SUPPORTED_OAUTH_PROVIDERS:
            raise BadRequestError(f"Unsupported provider: {provider}")

        redirect = self._resolve_oauth_redirect(provider, redirect_uri)
        state = create_oauth_state(provider)
        if provider == "google":
            if not settings.google_client_id:
                raise BadRequestError("Google OAuth is not configured")
            params = {
                "client_id": settings.google_client_id,
                "redirect_uri": redirect,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "access_type": "offline",
                "prompt": "consent",
            }
            url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
        else:
            if not settings.facebook_client_id:
                raise BadRequestError("Facebook OAuth is not configured")
            params = {
                "client_id": settings.facebook_client_id,
                "redirect_uri": redirect,
                "state": state,
                "scope": "email,public_profile",
                "response_type": "code",
            }
            url = "https://www.facebook.com/v18.0/dialog/oauth?" + urlencode(params)

        return {"provider": provider, "authorization_url": url, "state": state}

    def oauth_callback(
        self,
        provider: str,
        code: str,
        state: str,
        redirect_uri: str | None = None,
    ) -> tuple[User, str, str]:
        if provider not in SUPPORTED_OAUTH_PROVIDERS:
            raise BadRequestError(f"Unsupported provider: {provider}")

        try:
            verify_oauth_state(state, provider)
        except (JWTError, ValueError) as exc:
            raise BadRequestError("Invalid OAuth state") from exc

        profile = self._fetch_oauth_profile(provider, code, redirect_uri)
        oauth_account = (
            self.db.query(OAuthAccount)
            .filter(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == profile["provider_user_id"],
            )
            .first()
        )

        if oauth_account:
            user = self.db.get(User, oauth_account.user_id)
            if not user:
                raise BadRequestError("Linked user not found")
        else:
            user = self._find_or_create_oauth_user(profile, provider)
            self.db.add(
                OAuthAccount(
                    user_id=user.id,
                    provider=provider,
                    provider_user_id=profile["provider_user_id"],
                    email=profile.get("email"),
                    created_at=datetime.now(UTC),
                )
            )
            self.db.commit()

        if profile.get("email") and not user.email_verified_at:
            user.email_verified_at = datetime.now(UTC)
            self.db.commit()

        return user, *self.issue_tokens(user)

    def issue_tokens(self, user: User) -> tuple[str, str]:
        access = create_access_token(user.id, user.role)
        refresh = create_refresh_token(user.id)
        session = AuthSession(
            user_id=user.id,
            token_hash=hash_token(refresh),
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
            created_at=datetime.now(UTC),
        )
        self.db.add(session)
        self.db.commit()
        return access, refresh

    def _create_password_reset_token(self, user: User) -> str:
        raw = generate_opaque_token()
        self._invalidate_tokens(PasswordResetToken, user.id)
        self.db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_token(raw),
                expires_at=datetime.now(UTC) + timedelta(hours=settings.password_reset_expire_hours),
                created_at=datetime.now(UTC),
            )
        )
        self.db.commit()
        return raw

    def _create_email_verification_token(self, user: User) -> str:
        raw = generate_opaque_token()
        self._invalidate_tokens(EmailVerificationToken, user.id)
        self.db.add(
            EmailVerificationToken(
                user_id=user.id,
                token_hash=hash_token(raw),
                expires_at=datetime.now(UTC) + timedelta(hours=settings.email_verify_expire_hours),
                created_at=datetime.now(UTC),
            )
        )
        self.db.commit()
        return raw

    def _invalidate_tokens(self, model: type, user_id: str) -> None:
        now = datetime.now(UTC)
        records = self.db.query(model).filter(model.user_id == user_id, model.used_at.is_(None)).all()
        for record in records:
            record.used_at = now

    def _get_valid_token(self, model: type, raw_token: str) -> Any:
        token_hash = hash_token(raw_token)
        record = (
            self.db.query(model)
            .filter(
                model.token_hash == token_hash,
                model.used_at.is_(None),
                model.expires_at > datetime.now(UTC),
            )
            .first()
        )
        if not record:
            raise BadRequestError("Invalid or expired token")
        return record

    def _find_or_create_oauth_user(self, profile: dict[str, Any], provider: str) -> User:
        email = profile.get("email")
        if email:
            existing = self.db.query(User).filter(User.email == email).first()
            if existing:
                # Do not auto-link OAuth to an existing password account.
                raise BadRequestError(
                    "Email này đã có tài khoản. Đăng nhập bằng mật khẩu rồi liên kết OAuth "
                    "trong cài đặt, hoặc dùng email khác."
                )

        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            email=email,
            password_hash=None,
            display_name=profile.get("name") or email or f"{provider}_user",
            role=Role.USER.value,
            created_at=datetime.now(UTC),
            email_verified_at=datetime.now(UTC) if email else None,
        )
        user_profile = UserProfile(user_id=user_id, experience_level="beginner", updated_at=datetime.now(UTC))
        self.db.add(user)
        self.db.add(user_profile)
        self.db.commit()
        return user

    def _resolve_oauth_redirect(self, provider: str, redirect_uri: str | None) -> str:
        allowed = {
            "google": settings.google_redirect_uri,
            "facebook": settings.facebook_redirect_uri,
        }
        configured = (allowed.get(provider) or "").rstrip("/")
        if not configured:
            raise BadRequestError(f"{provider.title()} OAuth redirect URI is not configured")
        if redirect_uri is None or not redirect_uri.strip():
            return configured
        candidate = redirect_uri.strip().rstrip("/")
        if candidate != configured and redirect_uri.strip() != allowed.get(provider):
            raise BadRequestError("Invalid OAuth redirect_uri")
        return allowed[provider]

    def _fetch_oauth_profile(
        self, provider: str, code: str, redirect_uri: str | None
    ) -> dict[str, Any]:
        if provider == "google":
            return self._fetch_google_profile(code, redirect_uri)
        return self._fetch_facebook_profile(code, redirect_uri)

    def _fetch_google_profile(self, code: str, redirect_uri: str | None) -> dict[str, Any]:
        if not settings.google_client_id or not settings.google_client_secret:
            raise BadRequestError("Google OAuth is not configured")

        redirect = self._resolve_oauth_redirect("google", redirect_uri)
        with httpx.Client(timeout=15) as client:
            token_resp = client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": redirect,
                    "grant_type": "authorization_code",
                },
            )
            if token_resp.status_code != 200:
                raise BadRequestError("Failed to exchange Google authorization code")
            access_token = token_resp.json().get("access_token")
            user_resp = client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if user_resp.status_code != 200:
                raise BadRequestError("Failed to fetch Google user profile")
            data = user_resp.json()

        return {
            "provider_user_id": data["id"],
            "email": data.get("email"),
            "name": data.get("name"),
        }

    def _fetch_facebook_profile(self, code: str, redirect_uri: str | None) -> dict[str, Any]:
        if not settings.facebook_client_id or not settings.facebook_client_secret:
            raise BadRequestError("Facebook OAuth is not configured")

        redirect = self._resolve_oauth_redirect("facebook", redirect_uri)
        with httpx.Client(timeout=15) as client:
            token_resp = client.get(
                "https://graph.facebook.com/v18.0/oauth/access_token",
                params={
                    "client_id": settings.facebook_client_id,
                    "client_secret": settings.facebook_client_secret,
                    "redirect_uri": redirect,
                    "code": code,
                },
            )
            if token_resp.status_code != 200:
                raise BadRequestError("Failed to exchange Facebook authorization code")
            access_token = token_resp.json().get("access_token")
            user_resp = client.get(
                "https://graph.facebook.com/me",
                params={"fields": "id,name,email", "access_token": access_token},
            )
            if user_resp.status_code != 200:
                raise BadRequestError("Failed to fetch Facebook user profile")
            data = user_resp.json()

        return {
            "provider_user_id": data["id"],
            "email": data.get("email"),
            "name": data.get("name"),
        }

    def build_reset_url(self, token: str) -> str:
        return f"{settings.frontend_url.rstrip('/')}/dat-lai-mat-khau?token={token}"

    def build_verify_url(self, token: str) -> str:
        return f"{settings.frontend_url.rstrip('/')}/xac-thuc-email?token={token}"
