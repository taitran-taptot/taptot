import logging

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.auth_cookies import (
    clear_admin_cookie,
    clear_auth_cookies,
    read_refresh_token,
    set_admin_cookie,
    set_auth_cookies,
)
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import verify_password
from app.models.entities import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ConfirmPasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])
settings = get_settings()


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        email_verified=user.email_verified_at is not None,
    )


def _attach_session(response: Response, access: str, refresh: str) -> None:
    set_auth_cookies(response, access, refresh)


@router.post("/register", response_model=UserResponse, status_code=201)
def register(
    payload: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> UserResponse:
    del payload, response, db
    raise ForbiddenError("Đăng ký công khai đã đóng. Liên hệ quản trị để tạo tài khoản HLV.")


@router.post("/login", response_model=UserResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> UserResponse:
    service = AuthService(db)
    access, refresh = service.login(payload.email, payload.password)
    user = service.db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise UnauthorizedError("Invalid email or password")
    _attach_session(response, access, refresh)
    return _user_response(user)


@router.post("/refresh", response_model=UserResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> UserResponse:
    token = read_refresh_token(request)
    if not token:
        raise UnauthorizedError("Invalid refresh token")
    service = AuthService(db)
    access, refresh = service.refresh(token)
    from jose import JWTError

    from app.core.security import decode_token

    try:
        sub = decode_token(access).get("sub")
    except JWTError as exc:
        raise UnauthorizedError("Invalid refresh token") from exc
    user = db.get(User, sub) if sub else None
    if not user:
        raise UnauthorizedError("User not found")
    _attach_session(response, access, refresh)
    return _user_response(user)


@router.post("/logout", response_model=MessageResponse)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> MessageResponse:
    token = read_refresh_token(request)
    if token:
        AuthService(db).logout(token)
    clear_auth_cookies(response)
    return MessageResponse(message="Logged out successfully")


@router.post("/confirm-password", response_model=MessageResponse)
def confirm_password(
    payload: ConfirmPasswordRequest,
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    db_user = db.get(User, user.id)
    if (
        not db_user
        or not db_user.password_hash
        or not verify_password(payload.password, db_user.password_hash)
    ):
        raise UnauthorizedError("Mật khẩu không đúng")
    if user.role.value != "admin":
        from app.core.exceptions import ForbiddenError

        raise ForbiddenError("Admin access required")
    set_admin_cookie(response, user.id, user.role.value)
    return MessageResponse(message="Đã xác nhận quyền quản trị")


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> UserResponse:
    db_user = db.get(User, user.id)
    if not db_user:
        raise UnauthorizedError()
    return _user_response(db_user)


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    AuthService(db).change_password(user.id, payload.current_password, payload.new_password)
    clear_auth_cookies(response)
    return MessageResponse(message="Password changed. Please log in again.")


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> ForgotPasswordResponse:
    service = AuthService(db)
    token = service.forgot_password(payload.email)
    reset_url = None
    if token and settings.debug and settings.email_provider.lower() == "console":
        reset_url = service.build_reset_url(token)
        logger.info("[dev] password reset url: %s", reset_url)
    return ForgotPasswordResponse(
        message="If the email exists, a password reset link has been sent.",
        reset_url=reset_url,
    )


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> MessageResponse:
    AuthService(db).reset_password(payload.token, payload.new_password)
    return MessageResponse(message="Password reset successfully. Please log in.")


@router.post("/verify-email", response_model=UserResponse)
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)) -> UserResponse:
    return _user_response(AuthService(db).verify_email(payload.token))

