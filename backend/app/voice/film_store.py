from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Answer
from app.research.explainer import Explainer
from app.services.explainer_payload import stored_explainer
from app.services.simulation_hiding import with_hidden_marks

__all__ = ["SqlFilmStore"]


class SqlFilmStore:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def explainer(self, answer_id: uuid.UUID, user_id: uuid.UUID) -> Explainer | None:
        async with self._sessions() as session:
            payload = await session.scalar(
                select(Answer.payload).where(Answer.id == answer_id, Answer.userId == user_id)
            )
            explainer = stored_explainer(answer_id, payload)
            if explainer is None:
                return None
            return await with_hidden_marks(session, explainer)
