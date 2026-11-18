from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Answer, LessonPack

from . import audit

__all__ = [
    "SHARES_WITHDRAWN",
    "WithdrawnShares",
    "withdraw_lesson_shares",
    "withdraw_shares",
]

SHARES_WITHDRAWN = "shares.withdrawn"


@dataclass(frozen=True, slots=True)
class WithdrawnShares:
    answers: int
    lessons: int

    def audit_detail(self, cause: str) -> dict[str, Any]:
        return {"cause": cause, "answers": self.answers, "lessons": self.lessons}

    @property
    def total(self) -> int:
        return self.answers + self.lessons


async def withdraw_shares(
    session: AsyncSession, owner_id: uuid.UUID, *, actor: Any, cause: str
) -> WithdrawnShares:
    withdrawn = WithdrawnShares(
        answers=await _withdraw(session, Answer, owner_id),
        lessons=await _withdraw(session, LessonPack, owner_id),
    )
    await _record(session, owner_id, withdrawn, actor=actor, cause=cause)
    return withdrawn


async def withdraw_lesson_shares(
    session: AsyncSession, owner_id: uuid.UUID, *, actor: Any, cause: str
) -> WithdrawnShares:
    withdrawn = WithdrawnShares(answers=0, lessons=await _withdraw(session, LessonPack, owner_id))
    await _record(session, owner_id, withdrawn, actor=actor, cause=cause)
    return withdrawn


async def _withdraw(session: AsyncSession, table: Any, owner_id: uuid.UUID) -> int:
    found = await session.execute(
        update(table)
        .where(table.userId == owner_id, table.shareToken.is_not(None))
        .values(shareToken=None, sharedAt=None)
        .returning(table.id)
        .execution_options(synchronize_session=False)
    )
    return len(found.all())


async def _record(
    session: AsyncSession, owner_id: uuid.UUID, withdrawn: WithdrawnShares, *, actor: Any, cause: str
) -> None:
    if withdrawn.total == 0:
        return
    await audit.record(
        session,
        action=SHARES_WITHDRAWN,
        actor=actor,
        target_type="User",
        target_id=owner_id,
        detail=withdrawn.audit_detail(cause),
    )
