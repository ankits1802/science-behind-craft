from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, and_, cast, delete, func, literal, select
from sqlalchemy.dialects.postgresql import JSONPATH, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.errors import AppError
from app.models import Answer, SavedItem, User
from app.research.alerts import (
    ALERTS_SCHEMA_VERSION,
    SAVED_EXPLAINERS_MAX,
    SavedExplainer,
    SavedExplainerList,
)
from app.research.explainer import Understood

from .explainer_history import UnknownExplainer, owned_explainer
from .explainer_payload import EXPLAINER_PAYLOAD_KEY

__all__ = [
    "SAVED_FULL_DETAIL",
    "SECTION_FIELDS_PATH",
    "SavedFull",
    "SavedJoin",
    "save_explainer",
    "saved_explainer",
    "saved_explainers",
    "saved_join",
    "unsave_explainer",
]

SAVED_FULL_DETAIL = f"You can keep {SAVED_EXPLAINERS_MAX} saved explainers. Remove one to save this."
SECTION_FIELDS_PATH = "$.explainer.sections[*].discipline"
SAVED_COLUMNS = 5


class SavedFull(AppError):
    pass


@dataclass(frozen=True)
class SavedJoin:
    first: Any
    last: Any

    def select(self, *columns: Any) -> Select[Any]:
        latest = (
            select(func.max(Answer.explainerVersion))
            .where(Answer.explainerId == SavedItem.answerId, Answer.userId == SavedItem.userId)
            .correlate(SavedItem)
            .scalar_subquery()
        )
        fields = func.jsonb_path_query_array(self.last.payload, cast(literal(SECTION_FIELDS_PATH), JSONPATH))
        return (
            select(
                SavedItem,
                self.first.question,
                self.first.payload[EXPLAINER_PAYLOAD_KEY]["understood"],
                self.last.explainerVersion,
                fields,
                *columns,
            )
            .join(
                self.first, and_(self.first.id == SavedItem.answerId, self.first.userId == SavedItem.userId)
            )
            .join(
                self.last,
                and_(
                    self.last.explainerId == SavedItem.answerId,
                    self.last.userId == SavedItem.userId,
                    self.last.explainerVersion == latest,
                ),
            )
        )


def saved_join() -> SavedJoin:
    return SavedJoin(first=aliased(Answer), last=aliased(Answer))


def saved_explainer(row: Any) -> SavedExplainer:
    item, question, understood_json, latest, fields = tuple(row)[:SAVED_COLUMNS]
    understood = Understood.model_validate(understood_json)
    return SavedExplainer(
        explainer_id=item.answerId,
        question=question,
        craft=understood.crafts[0] if understood.crafts else None,
        facets=list(dict.fromkeys(fields)),
        depth=understood.depth,
        language=understood.language,
        latest_version=latest,
        seen_version=item.seenVersion,
        saved_at=item.createdAt,
        checked_at=item.checkedAt,
    )


async def saved_explainers(session: AsyncSession, user_id: uuid.UUID) -> SavedExplainerList:
    joined = saved_join()
    rows = await session.execute(
        joined.select().where(SavedItem.userId == user_id).order_by(SavedItem.createdAt.desc(), SavedItem.id)
    )
    return SavedExplainerList(
        schema_version=ALERTS_SCHEMA_VERSION, items=[saved_explainer(row) for row in rows.all()]
    )


async def save_explainer(
    session: AsyncSession, user_id: uuid.UUID, explainer_id: uuid.UUID
) -> SavedExplainer:
    await session.execute(select(User.id).where(User.id == user_id).with_for_update())
    latest = await session.scalar(
        select(func.max(Answer.explainerVersion)).where(*owned_explainer(explainer_id, user_id))
    )
    if latest is None:
        raise UnknownExplainer(explainer_id)
    others = await session.scalar(
        select(func.count())
        .select_from(SavedItem)
        .where(
            SavedItem.userId == user_id, SavedItem.answerId.is_not(None), SavedItem.answerId != explainer_id
        )
    )
    if (others or 0) >= SAVED_EXPLAINERS_MAX:
        raise SavedFull(f"reader {user_id} keeps {others} saved explainers")
    await session.execute(
        insert(SavedItem)
        .values(userId=user_id, answerId=explainer_id, seenVersion=latest)
        .on_conflict_do_nothing(
            index_elements=["userId", "answerId"], index_where=SavedItem.answerId.is_not(None)
        )
    )
    joined = saved_join()
    row = (
        await session.execute(
            joined.select().where(SavedItem.userId == user_id, SavedItem.answerId == explainer_id)
        )
    ).one()
    return saved_explainer(row)


async def unsave_explainer(session: AsyncSession, user_id: uuid.UUID, explainer_id: uuid.UUID) -> bool:
    removed = await session.execute(
        delete(SavedItem)
        .where(SavedItem.userId == user_id, SavedItem.answerId == explainer_id)
        .returning(SavedItem.id)
    )
    return removed.first() is not None
