from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import asdict, dataclass
from itertools import batched
from typing import Any

import httpx
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.config import Settings
from app.core.errors import AppError
from app.data.craft_master_loader import MERGED, load_master
from app.models import Craft, CraftAlias, CraftCategory, CraftCode, CraftSpelling, CraftSubCategory
from app.services.craft_seed import BATCH, ids_by_slug
from app.services.portal_craft_feed import PORTALS, PortalCraftFeed
from app.services.portal_craft_plan import (
    SOURCES_KEY,
    CraftColumns,
    KnownCategory,
    KnownCraft,
    KnownState,
    KnownSubCategory,
)
from app.services.portal_craft_reconcile import SyncPlan, plan_sync
from app.services.portal_peer import peer_for

__all__ = [
    "FeedFetch",
    "PortalOutcome",
    "SyncCounts",
    "SyncReport",
    "apply_plan",
    "fetch_feeds",
    "load_known",
    "run_sync",
    "sync_feeds",
]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PortalOutcome:
    portal: str
    ok: bool
    crafts: int
    error: str | None = None


@dataclass(frozen=True)
class FeedFetch:
    feeds: tuple[PortalCraftFeed, ...]
    failures: tuple[PortalOutcome, ...]

    @property
    def outcomes(self) -> tuple[PortalOutcome, ...]:
        fetched = {feed.portal: PortalOutcome(feed.portal, True, len(feed.crafts)) for feed in self.feeds}
        fetched.update({failure.portal: failure for failure in self.failures})
        return tuple(fetched[portal] for portal in PORTALS if portal in fetched)


@dataclass(frozen=True)
class SyncCounts:
    categories: int
    sub_categories: int
    codes: int
    spellings: int
    crafts_created: int
    crafts_synced: int
    crafts_merged: int
    crafts_unlisted: int
    aliases: int
    name_conflicts: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SyncReport:
    outcomes: tuple[PortalOutcome, ...]
    counts: SyncCounts | None

    @property
    def ok(self) -> bool:
        return bool(self.outcomes) and all(outcome.ok for outcome in self.outcomes)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "portals": [asdict(outcome) for outcome in self.outcomes],
            "counts": self.counts.as_dict() if self.counts else None,
        }


SessionOpener = Callable[[], AbstractAsyncContextManager[AsyncSession]]


async def run_sync(
    settings: Settings,
    *,
    open_session: SessionOpener,
    synced_at: str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> SyncReport:
    fetched = await fetch_feeds(settings, transport=transport)
    if not fetched.feeds:
        return SyncReport(fetched.outcomes, None)
    async with open_session() as session:
        counts = await sync_feeds(session, fetched.feeds, synced_at=synced_at)
    return SyncReport(fetched.outcomes, counts)


async def fetch_feeds(settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None) -> FeedFetch:
    feeds: list[PortalCraftFeed] = []
    failures: list[PortalOutcome] = []
    for portal in PORTALS:
        try:
            feeds.append(await peer_for(settings, portal, transport=transport).craft_feed())
        except AppError as error:
            logger.error("craft feed from %s failed: %s", portal, error)
            failures.append(PortalOutcome(portal, False, 0, f"{type(error).__name__}: {error}"))
    return FeedFetch(tuple(feeds), tuple(failures))


async def sync_feeds(
    session: AsyncSession, feeds: tuple[PortalCraftFeed, ...], *, synced_at: str
) -> SyncCounts:
    plan = plan_sync(feeds, await load_known(session), synced_at=synced_at)
    return await apply_plan(session, plan)


async def load_known(session: AsyncSession) -> KnownState:
    categories = (await session.execute(select(CraftCategory.slug, CraftCategory.name))).all()
    subs = (
        await session.execute(
            select(CraftSubCategory.slug, CraftSubCategory.name, CraftCategory.slug).join(
                CraftCategory, CraftSubCategory.categoryId == CraftCategory.id
            )
        )
    ).all()
    target = aliased(Craft)
    crafts = (
        await session.execute(
            select(
                Craft.slug, Craft.name, CraftSubCategory.slug, Craft.status, target.slug, Craft.extraMetadata
            )
            .outerjoin(CraftSubCategory, Craft.subCategoryId == CraftSubCategory.id)
            .outerjoin(target, Craft.mergedIntoId == target.id)
        )
    ).all()
    return KnownState(
        categories=tuple(KnownCategory(slug, name) for slug, name in categories),
        sub_categories=tuple(KnownSubCategory(slug, name, category) for slug, name, category in subs),
        crafts=tuple(KnownCraft(*row[:5], meta=dict(row[5] or {})) for row in crafts),
        codes=frozenset((await session.execute(select(CraftCode.code))).scalars()),
        spellings=frozenset((await session.execute(select(CraftSpelling.spelling))).scalars()),
        master_slugs=frozenset(craft.slug for craft in load_master()),
    )


async def apply_plan(session: AsyncSession, plan: SyncPlan) -> SyncCounts:
    await _write_taxonomy(session, plan)
    await _write_codes(session, plan)
    sub_ids = await ids_by_slug(session, CraftSubCategory)
    for write in plan.crafts:
        values: dict[str, Any] = {"extraMetadata": dict(write.meta)}
        if write.columns is not None:
            values.update(_column_values(write.columns, sub_ids))
        if write.status is not None:
            values["status"] = write.status
        if write.insert:
            await session.execute(insert(Craft).values(id=uuid.UUID(write.id), slug=write.slug, **values))
        else:
            await session.execute(update(Craft).where(Craft.slug == write.slug).values(**values))
    craft_ids = await ids_by_slug(session, Craft)
    await _write_redirects(session, plan, craft_ids)
    aliases = await _write_aliases(session, plan, craft_ids)
    await session.flush()
    return _counts(plan, aliases)


async def _write_taxonomy(session: AsyncSession, plan: SyncPlan) -> None:
    for category in plan.categories:
        await session.execute(
            insert(CraftCategory)
            .values(
                id=uuid.UUID(category.id),
                slug=category.slug,
                name=category.name,
                sortOrder=category.sort_order,
            )
            .on_conflict_do_nothing()
        )
    category_ids = await ids_by_slug(session, CraftCategory)
    for sub in plan.sub_categories:
        await session.execute(
            insert(CraftSubCategory)
            .values(
                id=uuid.UUID(sub.id),
                slug=sub.slug,
                name=sub.name,
                categoryId=category_ids[sub.category_slug],
                sortOrder=sub.sort_order,
            )
            .on_conflict_do_nothing()
        )


async def _write_codes(session: AsyncSession, plan: SyncPlan) -> None:
    for chunk in batched(plan.codes, BATCH, strict=False):
        await session.execute(
            insert(CraftCode)
            .values([{"code": c.code, "name": c.name} for c in chunk])
            .on_conflict_do_nothing()
        )
    for chunk in batched(plan.spellings, BATCH, strict=False):
        rows = [
            {"spelling": s.spelling, "label": s.label, "craftCode": s.craft_code, "source": s.source}
            for s in chunk
        ]
        await session.execute(insert(CraftSpelling).values(rows).on_conflict_do_nothing())


async def _write_redirects(session: AsyncSession, plan: SyncPlan, craft_ids: dict[str, uuid.UUID]) -> None:
    for write in plan.crafts:
        if write.status is None:
            continue
        target = (
            craft_ids[write.merged_into_slug] if write.status == MERGED and write.merged_into_slug else None
        )
        await session.execute(update(Craft).where(Craft.slug == write.slug).values(mergedIntoId=target))


async def _write_aliases(session: AsyncSession, plan: SyncPlan, craft_ids: dict[str, uuid.UUID]) -> int:
    rows = [
        {
            "craftId": craft_ids[alias.craft_slug],
            "alias": alias.alias,
            "aliasNorm": alias.alias_norm,
            "script": alias.script,
            "lang": alias.lang,
            "source": alias.source,
            "status": "ACTIVE",
        }
        for alias in plan.aliases
    ]
    inserted = 0
    for chunk in batched(rows, BATCH, strict=False):
        result = await session.execute(
            insert(CraftAlias)
            .values(list(chunk))
            .on_conflict_do_nothing(index_elements=[CraftAlias.craftId, CraftAlias.aliasNorm])
            .returning(CraftAlias.id)
        )
        inserted += len(result.scalars().all())
    return inserted


def _column_values(columns: CraftColumns, sub_ids: dict[str, uuid.UUID]) -> dict[str, Any]:
    return {
        "name": columns.name,
        "localName": columns.local_name,
        "category": columns.category,
        "subCategoryId": sub_ids[columns.sub_category_slug] if columns.sub_category_slug else None,
        "stateOfOrigin": list(columns.state_of_origin),
        "stateOfPractice": list(columns.state_of_practice),
        "giStatus": columns.gi_status,
        "isCatchAll": columns.is_catch_all,
        "craftCode": columns.craft_code,
    }


def _counts(plan: SyncPlan, aliases: int) -> SyncCounts:
    portal_writes = [write for write in plan.crafts if write.status is not None]
    return SyncCounts(
        categories=len(plan.categories),
        sub_categories=len(plan.sub_categories),
        codes=len(plan.codes),
        spellings=len(plan.spellings),
        crafts_created=sum(1 for write in plan.crafts if write.insert),
        crafts_synced=sum(1 for write in plan.crafts if not write.insert),
        crafts_merged=sum(1 for write in portal_writes if write.status == MERGED),
        crafts_unlisted=sum(1 for write in portal_writes if not write.meta.get(SOURCES_KEY)),
        aliases=aliases,
        name_conflicts=plan.name_conflicts,
    )
