from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import ColumnElement, delete, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OAuthClient, OAuthGrant

__all__ = [
    "ABANDONED_CLIENTS_PER_NIGHT",
    "ABANDONED_CLIENT_AGE",
    "ClientsReport",
    "abandoned_client_count",
    "remove_abandoned_clients",
]

ABANDONED_CLIENT_AGE = timedelta(days=30)
ABANDONED_CLIENTS_PER_NIGHT = 1000


@dataclass
class ClientsReport:
    removed: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {"abandonedRemoved": self.removed}


async def abandoned_client_count(session: AsyncSession, *, now: datetime) -> int:
    counted = await session.scalar(select(func.count(OAuthClient.id)).where(*_abandoned(now)))
    return int(counted or 0)


async def remove_abandoned_clients(session: AsyncSession, *, now: datetime) -> ClientsReport:
    oldest = (
        select(OAuthClient.id)
        .where(*_abandoned(now))
        .order_by(OAuthClient.createdAt, OAuthClient.id)
        .limit(ABANDONED_CLIENTS_PER_NIGHT)
    )
    removed = await session.scalars(
        delete(OAuthClient)
        .where(OAuthClient.id.in_(oldest.scalar_subquery()), *_abandoned(now))
        .returning(OAuthClient.id)
    )
    report = ClientsReport(removed=len(removed.all()))
    await session.commit()
    return report


def _abandoned(now: datetime) -> list[ColumnElement[bool]]:
    return [
        OAuthClient.createdAt < now - ABANDONED_CLIENT_AGE,
        ~exists().where(OAuthGrant.clientId == OAuthClient.id),
    ]
