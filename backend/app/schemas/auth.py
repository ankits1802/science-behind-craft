from typing import Literal

from pydantic import EmailStr, Field, model_validator

from app.core.security import MAX_PASSWORD_LENGTH
from app.schemas.common import APIModel


class LoginRequest(APIModel):
    email: str | None = Field(default=None, max_length=320)
    password: str | None = Field(default=None, min_length=1, max_length=MAX_PASSWORD_LENGTH)
    googleIdToken: str | None = Field(default=None, max_length=8192)

    @model_validator(mode="after")
    def _one_mode(self) -> LoginRequest:
        password_login = bool(self.email and self.password)
        google_login = bool(self.googleIdToken)
        if password_login == google_login:
            raise ValueError("Provide exactly one of email/password or a Google ID token")
        return self


class SignUpRequest(APIModel):
    email: EmailStr = Field(max_length=320)
    name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=10, max_length=MAX_PASSWORD_LENGTH)
    affiliation: str | None = Field(default=None, max_length=300)
    ageAttested: bool = False
    privacyNoticeVersion: str = Field(min_length=1, max_length=40)
    turnstileToken: str | None = Field(default=None, max_length=4096)


class GoogleLinkRequest(APIModel):
    googleIdToken: str = Field(min_length=1, max_length=8192)
    password: str | None = Field(default=None, max_length=MAX_PASSWORD_LENGTH)
    twoFactorCode: str | None = Field(default=None, max_length=64)


class IssuePasswordLinkRequest(APIModel):
    userId: str = Field(min_length=1, max_length=64)
    delivery: Literal["COPY_LINK", "EMAIL"] = "COPY_LINK"


class PasswordLinkCheckRequest(APIModel):
    token: str | None = None


class SetPasswordRequest(APIModel):
    token: str = Field(min_length=1, max_length=1024)
    password: str = Field(min_length=10, max_length=MAX_PASSWORD_LENGTH)


class ChangePasswordRequest(APIModel):
    currentPassword: str = Field(default="", max_length=MAX_PASSWORD_LENGTH)
    newPassword: str = Field(min_length=10, max_length=MAX_PASSWORD_LENGTH)
    twoFactorCode: str | None = Field(default=None, max_length=64)


class ForgotPasswordRequest(APIModel):
    email: EmailStr = Field(max_length=320)


class TwoFactorCodeRequest(APIModel):
    code: str = Field(min_length=1, max_length=64)


class TwoFactorVerifyRequest(TwoFactorCodeRequest):
    challenge_token: str = Field(min_length=1, max_length=2048)


class ConsentRequest(APIModel):
    kind: Literal["PRIVACY_NOTICE", "VOICE_NOTICE"]
    noticeVersion: str = Field(min_length=1, max_length=40)
