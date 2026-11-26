from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Craft, CraftCategory, LayoutProposal, PageLayout, PageUpgrade
from app.research.page_counts import BAR_SLUG
from app.research.page_upgrades import UPGRADE_CUTOFF, upgrade_lines

from .compose_components import ComposeDeps
from .monograph_document import stored_document
from .open_work_upgrades import approved_layouts, same_page
from .page_layout_proposals import APPROVED
from .page_report_held import held_shapes

__all__ = ["BuiltPage", "PageUpgradesReport", "built_before_round", "raise_page_upgrades", "upgrades_due"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BuiltPage:
    kind: str
    slug: str
    version: int

    @property
    def key(self) -> str:
        return f"{self.kind}:{self.slug}"


@dataclass
class PageUpgradesReport:
    raised: list[str] = field(default_factory=list)
    already_raised: int = 0
    no_document: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "raised": self.raised,
            "alreadyRaised": self.already_raised,
            "noDocument": self.no_document,
            "failed": self.failed,
        }


async def raise_page_upgrades(
    session: AsyncSession, *, compose: ComposeDeps = ComposeDeps()
) -> PageUpgradesReport:
    report = PageUpgradesReport()
    raised = await _raised(session)
    for page in await built_before_round(session):
        if (page.kind, page.slug) in raised:
            report.already_raised += 1
        else:
            await _raise(session, page, compose, report)
    await session.commit()
    return report


async def upgrades_due(session: AsyncSession) -> list[str]:
    raised = await _raised(session)
    return [page.key for page in await built_before_round(session) if (page.kind, page.slug) not in raised]


async def built_before_round(session: AsyncSession) -> list[BuiltPage]:
    latest = approved_layouts()
    slug = func.coalesce(Craft.slug, CraftCategory.slug)
    rows = await session.execute(
        select(LayoutProposal.subjectKind, slug, PageLayout.version)
        .select_from(LayoutProposal)
        .join(
            latest,
            and_(latest.c.version == LayoutProposal.layoutVersion, same_page(latest.c, LayoutProposal)),
        )
        .join(
            PageLayout,
            and_(PageLayout.version == LayoutProposal.layoutVersion, same_page(PageLayout, LayoutProposal)),
        )
        .outerjoin(Craft, Craft.id == LayoutProposal.craftId)
        .outerjoin(CraftCategory, CraftCategory.id == LayoutProposal.categoryId)
        .where(LayoutProposal.status == APPROVED, PageLayout.createdAt < UPGRADE_CUTOFF)
        .order_by(LayoutProposal.subjectKind, slug)
    )
    return [
        BuiltPage(kind, found, version) for kind, found, version in rows.tuples().all() if found != BAR_SLUG
    ]


async def _raised(session: AsyncSession) -> set[tuple[str, str]]:
    rows = await session.execute(select(PageUpgrade.subjectKind, PageUpgrade.subjectSlug))
    return set(rows.tuples().all())


async def _raise(
    session: AsyncSession, page: BuiltPage, compose: ComposeDeps, report: PageUpgradesReport
) -> None:
    document = await stored_document(session, page.kind, page.slug)
    if document is None:
        report.no_document.append(page.key)
        return
    try:
        lines = upgrade_lines(document, await held_shapes(session, compose, page.kind, page.slug))
    except AppError as failed:
        logger.warning("the upgrade work of %s could not be read: %s", page.key, failed)
        report.failed[page.key] = str(failed)
        return
    stored = await session.scalar(
        insert(PageUpgrade)
        .values(subjectKind=page.kind, subjectSlug=page.slug, layoutVersion=page.version, lines=lines)
        .on_conflict_do_nothing(index_elements=["subjectKind", "subjectSlug"])
        .returning(PageUpgrade.id)
    )
    if stored is None:
        report.already_raised += 1
    else:
        report.raised.append(page.key)
