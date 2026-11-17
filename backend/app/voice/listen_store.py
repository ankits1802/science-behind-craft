from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Answer, User
from app.providers.quota import LedgerEntry, record_units, remaining_today, used_today
from app.research.explainer import Explainer
from app.services.answer_store import EXPLAINER_PAYLOAD_KEY

from .listen import ListenHold
from .seconds import VOICE_SECONDS

__all__ = ["SqlListenStore", "stored_explainer"]

logger = logging.getLogger(__name__)


class SqlListenStore:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def explainer(self, answer_id: uuid.UUID, user_id: uuid.UUID) -> Explainer | None:
        async with self._sessions() as session:
            payload = await session.scalar(
                select(Answer.payload).where(Answer.id == answer_id, Answer.userId == user_id)
            )
        return stored_explainer(answer_id, payload)

    async def hold(self, entry: LedgerEntry, now: datetime) -> ListenHold:
        if entry.user_id is None:
            return ListenHold(held=0, remaining_after=0, refused=True)
        async with self._sessions() as session:
            role = await session.scalar(select(User.role).where(User.id == entry.user_id).with_for_update())
            if role is None:
                return ListenHold(held=0, remaining_after=0, refused=True)
            used = await used_today(session, user_id=entry.user_id, resource=VOICE_SECONDS, now=now)
            remaining = remaining_today(role, VOICE_SECONDS, used)
            if remaining is not None and remaining < entry.units:
                return ListenHold(held=0, remaining_after=remaining, refused=True)
            await record_units(session, entry)
            await session.commit()
        after = None if remaining is None else remaining - entry.units
        return ListenHold(held=entry.units, remaining_after=after)

    async def record(self, entry: LedgerEntry) -> None:
        async with self._sessions() as session:
            await record_units(session, entry)
            await session.commit()


def stored_explainer(answer_id: uuid.UUID, payload: dict[str, Any] | None) -> Explainer | None:
    document = payload.get(EXPLAINER_PAYLOAD_KEY) if isinstance(payload, dict) else None
    if document is None:
        return None
    try:
        explainer = Explainer.model_validate(document)
    except ValidationError as error:
        logger.error("answer %s keeps an explainer that is off its contract: %s", answer_id, error)
        return None
    if explainer.answer_id != answer_id:
        logger.error("answer %s keeps the explainer of answer %s", answer_id, explainer.answer_id)
        return None
    return explainer
