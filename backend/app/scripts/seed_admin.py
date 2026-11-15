import asyncio
import getpass
import sys
from datetime import UTC, datetime

from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.db import dispose_engine, session_scope
from app.core.security import hash_password
from app.models import AccessRoster, User

MIN_LENGTH = 12


async def seed(password: str) -> str:
    settings = get_settings()
    email = settings.master_admin_email.strip().lower()
    now = datetime.now(UTC)
    async with session_scope() as session:
        user = (
            await session.execute(select(User).where(func.lower(User.email) == email))
        ).scalar_one_or_none()
        if user is None:
            user = User(email=email, name=settings.master_admin_name, role="MASTER_ADMIN")
            session.add(user)
            outcome = "created"
        else:
            outcome = "updated"
            user.tokenVersion += 1
        user.role = "MASTER_ADMIN"
        user.passwordHash = hash_password(password)
        user.passwordSetAt = now
        user.mustChangePassword = False
        user.deletedAt = None
        row = (
            await session.execute(select(AccessRoster).where(AccessRoster.email == email))
        ).scalar_one_or_none()
        if row is None:
            session.add(AccessRoster(email=email, status="ACTIVE", admitRole="MASTER_ADMIN", joinedAt=now))
        else:
            row.status = "ACTIVE"
            row.admitRole = "MASTER_ADMIN"
    await dispose_engine()
    return outcome


def main() -> int:
    password = sys.stdin.readline().rstrip("\n") if not sys.stdin.isatty() else getpass.getpass("Password: ")
    if len(password) < MIN_LENGTH:
        print(f"The password must be at least {MIN_LENGTH} characters.", file=sys.stderr)
        return 2
    outcome = asyncio.run(seed(password))
    print(f"Master admin account {outcome}. Two-step verification is set up at first sign-in.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
