from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

__all__ = ["SHARED_TOGETHER", "SHARE_TOKEN_CHARS", "SharedByLink", "shared_together"]

SHARE_TOKEN_CHARS = 64
SHARED_TOGETHER = '("shareToken" IS NULL) = ("sharedAt" IS NULL)'


class SharedByLink:
    shareToken: Mapped[str | None] = mapped_column(String(SHARE_TOKEN_CHARS), unique=True)
    sharedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


def shared_together() -> CheckConstraint:
    return CheckConstraint(SHARED_TOGETHER, name="shared")
