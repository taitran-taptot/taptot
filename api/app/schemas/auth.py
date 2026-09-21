from pydantic import BaseModel, EmailStr, Field, field_validator


def _password_has_letter_and_digit(value: str) -> str:
    if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
        raise ValueError("Mật khẩu phải có ít nhất một chữ cái và một chữ số")
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return _password_has_letter_and_digit(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class ConfirmPasswordRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return _password_has_letter_and_digit(v)


class UpdateMeRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return _password_has_letter_and_digit(v)


class VerifyEmailRequest(BaseModel):
    token: str


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str
    redirect_uri: str | None = None


class UserResponse(BaseModel):
    id: str
    email: str | None
    display_name: str | None
    role: str
    email_verified: bool


class MessageResponse(BaseModel):
    message: str


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: str | None = None
    reset_url: str | None = None


class VerifyEmailResponse(BaseModel):
    message: str
    verification_token: str | None = None
    verification_url: str | None = None


class OAuthAuthorizeResponse(BaseModel):
    provider: str
    authorization_url: str
    state: str


class LogoutAllResponse(BaseModel):
    message: str
    revoked_sessions: int
