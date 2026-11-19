from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ArticleSection as SectionRow, Craft, CuratedCraft, KnowledgePiece
from app.research.article_sections import ArticleSection
from app.research.crafts import CraftRef
from app.research.knowledge_api import ComponentSummary
from app.research.knowledge_export import CraftExport, ExportedComponent

from . import knowledge_view
from .component_library import library_components
from .knowledge_api import every_fact, known_craft

__all__ = ["EXPORT_COMPONENTS_MAX", "craft_export", "exported_slugs"]

EXPORT_COMPONENTS_MAX = 5000
PUBLISHED = "PUBLISHED"
CRAFT_SUBJECT = "craft"


async def craft_export(session: AsyncSession, slug: str, *, site: str, now: datetime) -> CraftExport:
    craft = await known_craft(session, slug)
    facts, sources = await every_fact(session, craft)
    shown = {fact.id for fact in facts}
    return CraftExport(
        craft=_craft_ref(craft),
        curation_version=await session.scalar(
            select(CuratedCraft.version).where(CuratedCraft.craftId == craft.id)
        ),
        exported_at=now,
        facts=facts,
        sources=sources,
        sections=await _sections(session, craft, shown),
        components=await _components(session, craft, shown),
        page_url=f"{site}/crafts/{craft.slug}",
    )


async def exported_slugs(session: AsyncSession) -> list[str]:
    curated = select(CuratedCraft.craftId)
    sectioned = select(SectionRow.craftId).where(SectionRow.craftId.is_not(None))
    rows = await session.scalars(
        select(Craft.slug).where(Craft.id.in_(curated) | Craft.id.in_(sectioned)).order_by(Craft.slug)
    )
    return list(rows.all())


async def _sections(session: AsyncSession, craft: Craft, shown: set[uuid.UUID]) -> list[ArticleSection]:
    rows = await session.scalars(
        select(SectionRow)
        .where(SectionRow.craftId == craft.id, SectionRow.status == PUBLISHED)
        .order_by(SectionRow.field)
    )
    sections = []
    for row in rows:
        sentences = [s for s in row.sentences if {uuid.UUID(str(c)) for c in s["claimIds"]} <= shown]
        if sentences:
            sections.append(
                ArticleSection(
                    subject_kind=CRAFT_SUBJECT,
                    subject_slug=craft.slug,
                    field=row.field,
                    version=row.version,
                    status=row.status,
                    sentences=sentences,
                )
            )
    return sections


async def _components(session: AsyncSession, craft: Craft, shown: set[uuid.UUID]) -> list[ExportedComponent]:
    listed = await library_components(session, slug=craft.slug, limit=EXPORT_COMPONENTS_MAX)
    labels = [component.label for component in listed.components]
    rows = (
        await session.scalars(select(KnowledgePiece).where(KnowledgePiece.label.in_(labels)))
        if labels
        else []
    )
    stored = {row.label: row for row in rows}
    exported = (_component(c, stored[c.label], shown) for c in listed.components if c.label in stored)
    return [component for component in exported if component is not None]


def _component(
    summary: ComponentSummary, row: KnowledgePiece, shown: set[uuid.UUID]
) -> ExportedComponent | None:
    rests_on = [claim_id for claim_id in _uuids(row.claimIds) if claim_id in shown]
    if not rests_on:
        return None
    return ExportedComponent(
        **summary.model_dump(),
        claim_ids=rests_on,
        spec=_spec(row.payload),
    )


def _spec(payload: Any) -> dict[str, Any]:
    return dict(payload) if isinstance(payload, dict) else {}


def _uuids(values: Sequence[Any]) -> list[uuid.UUID]:
    return [value if isinstance(value, uuid.UUID) else uuid.UUID(str(value)) for value in values]


def _craft_ref(craft: Craft) -> CraftRef:
    return CraftRef.model_validate(knowledge_view.craft_ref(craft))
