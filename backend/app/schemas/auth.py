from typing import Literal

from pydantic import EmailStr, Field, model_validator

from app.core.security import MAX_PASSWORD_LENGTH
from app.schemas.common import APIModel

OidcProviderName = Literal["MICROSOFT", "YAHOO"]


class OidcCodeFields(APIModel):
    oidcProvider: OidcProviderName | None = None
    oidcCode: str | None = Field(default=None, min_length=1, max_length=4096)
    oidcCodeVerifier: str | None = Field(
        default=None, min_length=43, max_length=128, pattern=r"^[A-Za-z0-9\-._~]+$"
    )
    oidcRedirectUri: str | None = Field(default=None, min_length=1, max_length=2048)
    oidcNonce: str | None = Field(default=None, min_length=16, max_length=200)

    @property
    def has_oidc_code(self) -> bool:
        return bool(
            self.oidcProvider
            and self.oidcCode
            and self.oidcCodeVerifier
            and self.oidcRedirectUri
            and self.oidcNonce
        )

    @model_validator(mode="after")
    def _whole_oidc_code(self) -> OidcCodeFields:
        oidc_fields = (
            self.oidcProvider,
            self.oidcCode,
            self.oidcCodeVerifier,
            self.oidcRedirectUri,
            self.oidcNonce,
        )
        if any(oidc_fields) and not self.has_oidc_code:
            raise ValueError("A Microsoft or Yahoo code needs all five oidc fields")
        return self


class LoginRequest(OidcCodeFields):
    email: str | None = Field(default=None, max_length=320)
    password: str | None = Field(default=None, min_length=1, max_length=MAX_PASSWORD_LENGTH)
    googleIdToken: str | None = Field(default=None, max_length=8192)
    googleNonce: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _one_mode(self) -> LoginRequest:
        modes = (bool(self.email and self.password), bool(self.googleIdToken), self.has_oidc_code)
        if modes.count(True) != 1:
            raise ValueError(
                "Provide exactly one of email/password, a Google ID token, or a Microsoft or Yahoo code"
            )
        return self


class OidcNonceRequest(APIModel):
    provider: OidcProviderName


class SignUpRequest(APIModel):
    email: EmailStr = Field(max_length=320)
    name: str = Field(min_length=1, max_length=160)
    affiliation: str | None = Field(default=None, max_length=300)
    requestedRole: Literal["STUDENT", "ARTISAN", "RESEARCHER", "PROFESSOR"] = "STUDENT"
    profileUrl: str | None = Field(default=None, max_length=500, pattern=r"^https?://\S+$")
    note: str | None = Field(default=None, max_length=1000)
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


class ChangePasswordRequest(OidcCodeFields):
    currentPassword: str = Field(default="", max_length=MAX_PASSWORD_LENGTH)
    newPassword: str = Field(min_length=10, max_length=MAX_PASSWORD_LENGTH)
    twoFactorCode: str | None = Field(default=None, max_length=64)
    googleIdToken: str | None = Field(default=None, max_length=8192)

    @model_validator(mode="after")
    def _one_proof(self) -> ChangePasswordRequest:
        if self.googleIdToken and self.has_oidc_code:
            raise ValueError("Confirm with a Google ID token or a Microsoft or Yahoo code, not both")
        return self


class ForgotPasswordRequest(APIModel):
    email: EmailStr = Field(max_length=320)


class TwoFactorCodeRequest(APIModel):
    code: str = Field(min_length=1, max_length=64)


class TwoFactorVerifyRequest(TwoFactorCodeRequest):
    challenge_token: str = Field(min_length=1, max_length=2048)


class ConsentRequest(APIModel):
    kind: Literal["PRIVACY_NOTICE", "VOICE_NOTICE"]
    noticeVersion: str = Field(min_length=1, max_length=40)
