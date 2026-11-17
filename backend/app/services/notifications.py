from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification as NotificationRow
from app.research.alerts import (
    ALERTS_SCHEMA_VERSION,
    NOTIFICATIONS_SHOWN_MAX,
    AnswerImproved,
    FacetNews,
    Notification,
    NotificationList,
)

__all__ = [
    "ANSWER_IMPROVED",
    "mark_all_read",
    "mark_read",
    "merged_news",
    "note_improvement",
    "notification_list",
    "unread_improvements",
]

ANSWER_IMPROVED = "ANSWER_IMPROVED"


def merged_news(earlier: AnswerImproved, news: AnswerImproved) -> AnswerImproved:
    if (earlier.explainer_id, earlier.version) != (news.explainer_id, news.version):
        return news
    counts = Counter({entry.facet: entry.new_claims for entry in earlier.news})
    counts.update({entry.facet: entry.new_claims for entry in news.news})
    facets = dict.fromkeys([*(entry.facet for entry in news.news), *(entry.facet for entry in earlier.news)])
    combined = [FacetNews(facet=facet, new_claims=counts[facet]) for facet in facets]
    return AnswerImproved(**{**dict(news), "news": combined})


async def notification_list(session: AsyncSession, user_id: uuid.UUID) -> NotificationList:
    rows = (
        await session.scalars(
            select(NotificationRow)
            .where(NotificationRow.userId == user_id)
            .order_by(NotificationRow.createdAt.desc(), NotificationRow.id)
            .limit(NOTIFICATIONS_SHOWN_MAX)
        )
    ).all()
    unread = await session.scalar(
        select(func.count())
        .select_from(NotificationRow)
        .where(NotificationRow.userId == user_id, NotificationRow.readAt.is_(None))
    )
    return NotificationList(
        schema_version=ALERTS_SCHEMA_VERSION, items=[_notification(row) for row in rows], unread=unread or 0
    )


async def mark_read(session: AsyncSession, user_id: uuid.UUID, notification_id: uuid.UUID) -> bool:
    marked = await session.execute(
        update(NotificationRow)
        .where(NotificationRow.id == notification_id, NotificationRow.userId == user_id)
        .values(readAt=func.coalesce(NotificationRow.readAt, func.now()))
        .returning(NotificationRow.id)
    )
    return marked.first() is not None


async def mark_all_read(session: AsyncSession, user_id: uuid.UUID) -> None:
    await session.execute(
        update(NotificationRow)
        .where(NotificationRow.userId == user_id, NotificationRow.readAt.is_(None))
        .values(readAt=func.now())
    )


async def note_improvement(session: AsyncSession, user_id: uuid.UUID, news: AnswerImproved) -> None:
    unread = (
        await session.scalars(
            select(NotificationRow)
            .where(
                NotificationRow.userId == user_id,
                NotificationRow.explainerId == news.explainer_id,
                NotificationRow.kind == ANSWER_IMPROVED,
                NotificationRow.readAt.is_(None),
            )
            .with_for_update()
        )
    ).one_or_none()
    shown = news
    if unread is not None:
        shown = merged_news(AnswerImproved.model_validate(unread.payload), news)
        await session.delete(unread)
        await session.flush()
    session.add(
        NotificationRow(
            userId=user_id,
            kind=ANSWER_IMPROVED,
            explainerId=news.explainer_id,
            payload=shown.model_dump(mode="json", by_alias=True),
        )
    )
    await session.flush()


async def unread_improvements(
    session: AsyncSession, user_id: uuid.UUID, *, since: datetime, limit: int
) -> Sequence[AnswerImproved]:
    rows = (
        await session.scalars(
            select(NotificationRow.payload)
            .where(
                NotificationRow.userId == user_id,
                NotificationRow.kind == ANSWER_IMPROVED,
                NotificationRow.readAt.is_(None),
                NotificationRow.createdAt >= since,
            )
            .order_by(NotificationRow.createdAt.desc(), NotificationRow.id)
            .limit(limit)
        )
    ).all()
    return [AnswerImproved.model_validate(payload) for payload in rows]


def _notification(row: NotificationRow) -> Notification:
    return Notification(
        id=row.id,
        kind=row.kind,
        created_at=row.createdAt,
        read_at=row.readAt,
        payload=AnswerImproved.model_validate(row.payload),
    )
