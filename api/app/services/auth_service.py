import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, UnauthorizedError
from app.core.security import (
    Role,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    is_account_role,
    verify_password,
)
from app.services.email_service import EmailService
from app.models.entities import (
    CollaboratorPromo,
    AuthSession,
    EmailVerificationToken,
    PasswordResetToken,
    User,
    UserProfile,
)

settings = get_settings()


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def login(self, email: str, password: str) -> tuple[str, str]:
        user = self.db.query(User).filter(User.email == email).first()
        if not user or not user.password_hash or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")
        self._assert_staff_login(user)
        return self.issue_tokens(user)

    def create_staff(
        self,
        email: str,
        password: str,
        display_name: str,
        role: str = Role.HLV.value,
    ) -> User:
        if role != Role.HLV.value:
            raise BadRequestError("Chỉ có thể tạo tài khoản HLV")
        if self.db.query(User).filter(User.email == email).first():
            raise ConflictError("Email đã được dùng")

        user_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        user = User(
            id=user_id,
            email=email,
            password_hash=hash_password(password),
            display_name=display_name,
            role=Role.HLV.value,
            created_at=now,
            email_verified_at=now,
        )
        profile = UserProfile(user_id=user_id, experience_level="beginner", updated_at=now)
        self.db.add(user)
        self.db.add(profile)
        self.db.commit()
        return user

    def create_collaborator(
        self,
        email: str,
        password: str,
        display_name: str,
        discount_percent: int = 10,
    ) -> tuple[User, CollaboratorPromo]:
        if discount_percent < 0 or discount_percent > 100:
            raise BadRequestError("Mức giảm phải từ 0 đến 100")
        if self.db.query(User).filter(User.email == email).first():
            raise ConflictError("Email đã được dùng")

        user_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        user = User(
            id=user_id,
            email=email,
            password_hash=hash_password(password),
            display_name=display_name,
            role=Role.CTV.value,
            created_at=now,
            email_verified_at=now,
        )
        profile = UserProfile(user_id=user_id, experience_level="beginner", updated_at=now)
        promo = CollaboratorPromo(
            user_id=user_id,
            code=None,
            discount_percent=discount_percent,
            created_at=now,
        )
        self.db.add(user)
        self.db.add(profile)
        self.db.flush()
        self.db.add(promo)
        self.db.commit()
        self.db.refresh(user)
        self.db.refresh(promo)
        return user, promo

    def _assert_staff_login(self, user: User) -> None:
        if not is_account_role(user.role):
            raise ForbiddenError("Chỉ HLV, cộng tác viên và Admin được đăng nhập.")

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
        self._assert_staff_login(user)

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

    def forgot_password(self, email: str) -> str | None:
        user = self.db.query(User).filter(User.email == email).first()
        if not user or not is_account_role(user.role):
            return None
        token = self._create_password_reset_token(user)
        EmailService().send_password_reset(email, self.build_reset_url(token))
        return token

    def reset_password(self, token: str, new_password: str) -> None:
        record = self._get_valid_token(PasswordResetToken, token)
        user = self.db.get(User, record.user_id)
        if not user or not is_account_role(user.role):
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

    def build_reset_url(self, token: str) -> str:
        return f"{settings.frontend_url.rstrip('/')}/dat-lai-mat-khau?token={token}"

    def build_verify_url(self, token: str) -> str:
        return f"{settings.frontend_url.rstrip('/')}/xac-thuc-email?token={token}"
