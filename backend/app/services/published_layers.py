from __future__ import annotations

from datetime import datetime
from types import MappingProxyType
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.models import EnvDataset, MapLayerProposal, User
from app.models.datasets import LAYER_STATUSES
from app.research.page_revalidation import PageOwners
from app.research.review_labels import cut_label
from app.research.staged_reviews import REMOVE, StagedDecision

from . import audit
from .published_kinds import NO_ITEM, Carried, PublishedKind, PublishedLine, PublishedQuery, PublishedRef

__all__ = ["LAYER_REMOVED", "PUBLISHED_LAYERS"]

LAYER_REMOVED = "layer.removed"
_, APPROVED, REJECTED = LAYER_STATUSES
REMOVED = (
    "Removed: the layer is no longer fit to ship, kept private with its file, record and reason. Where an "
    "engineer has already drawn it from tools/maplayers, it leaves the maps when the engineer takes it out."
)


def _approved() -> Select[Any]:
    return (
        select(MapLayerProposal, EnvDataset.title, EnvDataset.code)
        .join(EnvDataset, EnvDataset.id == MapLayerProposal.datasetId)
        .where(MapLayerProposal.status == APPROVED)
    )


def _named(title: str, code: str) -> str:
    return cut_label(f"Map layer: {title} ({code})")


async def _name(session: AsyncSession, ref: PublishedRef) -> str | None:
    found = (await session.execute(_approved().where(MapLayerProposal.id == ref.id))).first()
    return None if found is None else _named(found[1], found[2])


async def _remove(session: AsyncSession, decision: StagedDecision, reviewer: User, now: datetime) -> Carried:
    row = await session.scalar(
        select(MapLayerProposal)
        .where(MapLayerProposal.id == decision.id, MapLayerProposal.status == APPROVED)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise InvalidInput(NO_ITEM.format(kind="map layer", id=decision.id))
    row.status, row.reviewedById, row.reviewedAt, row.reviewNote = REJECTED, reviewer.id, now, decision.reason
    await audit.record(
        session,
        action=LAYER_REMOVED,
        actor=reviewer,
        target_type="MapLayerProposal",
        target_id=row.id,
        detail={"from": APPROVED, "dataset": str(row.datasetId), "reason": decision.reason},
    )
    await session.flush()
    return Carried(REMOVED, PageOwners())


async def _listed(session: AsyncSession, query: PublishedQuery) -> list[PublishedLine]:
    rows = await session.execute(
        _approved()
        .order_by(MapLayerProposal.reviewedAt, MapLayerProposal.id)
        .offset(query.offset)
        .limit(query.limit)
    )
    return [PublishedLine(row.id, _named(title, code)) for row, title, code in rows.tuples().all()]


PUBLISHED_LAYERS = PublishedKind(
    noun="map layer", name=_name, actions=MappingProxyType({REMOVE: _remove}), listed=_listed
)
