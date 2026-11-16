import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.services import google_auth, oidc_sign_in
from app.services.oidc_sign_in import CodeGrant, ProvedIdentity

__all__ = [
    "CONFIRM_PROVIDERS",
    "GOOGLE",
    "NONCE_PURPOSE",
    "PROOF_LEEWAY_SECONDS",
    "PROOF_MAX_AGE_SECONDS",
    "ProofRefused",
    "ProviderProof",
    "account_provider",
    "client_id_for",
    "issued_recently",
    "require_fresh_proof",
]

GOOGLE = "GOOGLE"
CONFIRM_PROVIDERS = (GOOGLE, *oidc_sign_in.PROVIDERS)
NONCE_PURPOSE = "FIRST_PASSWORD"
PROOF_MAX_AGE_SECONDS = 300
PROOF_LEEWAY_SECONDS = 60


class ProofRefused(Exception):
    def __init__(self, provider: str, reason: str) -> None:
        super().__init__(reason)
        self.provider = provider
        self.reason = reason


@dataclass(frozen=True)
class ProviderProof:
    google_id_token: str | None = None
    grant: CodeGrant | None = None

    @property
    def provider(self) -> str | None:
        if self.google_id_token:
            return GOOGLE
        return self.grant.provider if self.grant is not None else None


def account_provider(account: User) -> str | None:
    provider = str(account.authProvider or "")
    return provider if provider in CONFIRM_PROVIDERS else None


def client_id_for(provider: str) -> str | None:
    if provider == GOOGLE:
        return google_auth.client_id_if_enabled()
    return oidc_sign_in.client_id_if_enabled(provider)


def issued_recently(issued_at: Any, now: float) -> bool:
    if isinstance(issued_at, bool) or not isinstance(issued_at, int | float):
        return False
    return now - PROOF_MAX_AGE_SECONDS <= issued_at <= now + PROOF_LEEWAY_SECONDS


async def require_fresh_proof(
    session: AsyncSession, account: User, proof: ProviderProof, *, now: float | None = None
) -> str:
    expected = account_provider(account)
    if expected is None:
        raise ProofRefused(proof.provider or "", "no-provider")
    if proof.provider is None:
        raise ProofRefused(expected, "no-proof")
    if proof.provider != expected:
        raise ProofRefused(proof.provider, "another-provider")
    if proof.grant is not None:
        proved = await _prove_with_code(session, account, proof.grant)
    else:
        proved = await _prove_with_google(session, account, proof.google_id_token or "")
    if not issued_recently(proved.issued_at, time.time() if now is None else now):
        raise ProofRefused(expected, "stale")
    if proved.email.strip().lower() != account.email.strip().lower():
        raise ProofRefused(expected, "another-address")
    return expected


async def _prove_with_google(session: AsyncSession, account: User, token: str) -> ProvedIdentity:
    try:
        claims = await google_auth.verify_with_nonce(
            session, token, purpose=NONCE_PURPOSE, user_id=account.id
        )
    except google_auth.GoogleSignInRefused as exc:
        raise ProofRefused(GOOGLE, exc.reason) from exc
    finally:
        await session.commit()
    return ProvedIdentity(
        provider=GOOGLE, email=str(claims["email"]), name=claims.get("name"), issued_at=claims.get("iat")
    )


async def _prove_with_code(session: AsyncSession, account: User, grant: CodeGrant) -> ProvedIdentity:
    try:
        return await oidc_sign_in.prove_once(session, grant, purpose=NONCE_PURPOSE, user_id=account.id)
    except oidc_sign_in.SignInRefused as exc:
        raise ProofRefused(grant.provider, exc.reason) from exc
