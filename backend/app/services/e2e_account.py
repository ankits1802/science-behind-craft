from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.roles import RESEARCHER
from app.services import two_factor
from app.services.password_accounts import PasswordAccount, upsert_password_account

__all__ = [
    "E2E_ACCOUNT_EMAIL",
    "E2E_ACCOUNT_NAME",
    "E2E_ACCOUNT_NOTE",
    "E2E_ACCOUNT_ROLE",
    "provision_e2e_account",
]

E2E_ACCOUNT_EMAIL = "e2e-researcher@kalavigyan.example"
E2E_ACCOUNT_NAME = "KalaVigyan E2E Researcher"
E2E_ACCOUNT_ROLE = RESEARCHER
E2E_ACCOUNT_NOTE = "Signs in for the E2E production workflow (decision 0029)."


async def provision_e2e_account(
    session: AsyncSession, password: str, *, email: str = E2E_ACCOUNT_EMAIL, now: datetime | None = None
) -> PasswordAccount:
    moment = now or datetime.now(UTC)
    account = await upsert_password_account(
        session, email=email, name=E2E_ACCOUNT_NAME, role=E2E_ACCOUNT_ROLE, password=password, now=moment
    )
    user = account.user
    user.emailVerifiedAt = user.emailVerifiedAt or moment
    for column, value in two_factor.OFF_VALUES.items():
        setattr(user, column, value)
    account.roster.fullName = E2E_ACCOUNT_NAME
    account.roster.notes = E2E_ACCOUNT_NOTE
    return account
