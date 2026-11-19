from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.models import ArticleSection as SectionRow, Claim, Craft, Source
from app.models.enums import DISCIPLINES
from app.research.article_sections import ArticleSection
from app.research.chapter_keys import DISCIPLINE_CHAPTERS
from app.research.crafts import CraftRef
from app.research.knowledge_api import (
    FACTS_LIMIT_DEFAULT,
    CraftFacts,
    CraftSection,
    Fact,
    FactCitation,
    FactSource,
    FieldInfo,
    FieldList,
    FoundCraft,
    FoundCrafts,
)
from app.research.retrieval import OPEN_CHUNK_ACLS
from app.research.sections import DISCIPLINE_FIELDS, DISCIPLINE_TITLES
from app.research.vocabulary import LEVEL_ORDER

from . import knowledge_view
from .craft_matching import lexical_match, resolution_from
from .craft_resolver import CraftIndexStore

__all__ = [
    "UNKNOWN_CRAFT",
    "craft_facts",
    "craft_section",
    "field_list",
    "found_crafts",
    "known_craft",
]

UNKNOWN_CRAFT = "No craft has the slug {slug}; find_crafts gives the slugs."
PUBLIC_MODE = "HYBRID"
PUBLISHED = "PUBLISHED"
CRAFT_SUBJECT = "craft"


def field_list() -> FieldList:
    return FieldList(
        fields=[
            FieldInfo(
                field=field,
                title=DISCIPLINE_TITLES[field],
                covers=DISCIPLINE_FIELDS[field],
                chapter=DISCIPLINE_CHAPTERS[field],
            )
            for field in DISCIPLINES
        ]
    )


async def found_crafts(
    session: AsyncSession, store: CraftIndexStore, query: str, *, site: str
) -> FoundCrafts:
    index = await store.get(session)
    resolution = resolution_from(index, lexical_match(index, query))
    return FoundCrafts(
        query=query,
        crafts=[
            FoundCraft(craft=candidate.craft, score=candidate.score, page_url=f"{site}{candidate.craft.path}")
            for candidate in resolution.candidates
        ],
    )


async def craft_facts(
    session: AsyncSession,
    slug: str,
    *,
    site: str,
    field: str | None = None,
    query: str | None = None,
    limit: int = FACTS_LIMIT_DEFAULT,
) -> CraftFacts:
    craft = await known_craft(session, slug)
    views, sources = await knowledge_view.claims_for(
        session, craft, mode=PUBLIC_MODE, question=query, acls=OPEN_CHUNK_ACLS
    )
    placed = await _claim_fields(session, [view.id for view in views])
    chosen = [view for view in views if field is None or field in placed[view.id]]
    ordered = _ranked(chosen) if query else knowledge_view.order_claims(chosen)
    facts = [_fact(view, placed[view.id]) for view in ordered[:limit]]
    cited = {citation.source_id for fact in facts for citation in fact.citations}
    return CraftFacts(
        craft=_ref(craft),
        field=field,
        query=query,
        facts=facts,
        sources=[_source(source) for source_id, source in sorted(sources.items()) if str(source_id) in cited],
        page_url=f"{site}/crafts/{craft.slug}",
    )


async def craft_section(session: AsyncSession, slug: str, field: str, *, site: str) -> CraftSection:
    craft = await known_craft(session, slug)
    row = await session.scalar(
        select(SectionRow).where(
            SectionRow.craftId == craft.id, SectionRow.field == field, SectionRow.status == PUBLISHED
        )
    )
    section = None
    if row is not None:
        section = ArticleSection(
            subject_kind=CRAFT_SUBJECT,
            subject_slug=craft.slug,
            field=row.field,
            version=row.version,
            status=row.status,
            sentences=row.sentences,
        )
    return CraftSection(
        craft=_ref(craft), field=field, section=section, page_url=f"{site}/crafts/{craft.slug}"
    )


async def known_craft(session: AsyncSession, slug: str) -> Craft:
    craft = await knowledge_view.resolve_craft(session, slug)
    if craft is None:
        raise InvalidInput(UNKNOWN_CRAFT.format(slug=slug))
    return craft


async def _claim_fields(session: AsyncSession, claim_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, list[str]]:
    if not claim_ids:
        return {}
    rows = await session.execute(
        select(Claim.id, Claim.field, Claim.fields).where(Claim.id.in_(list(claim_ids)))
    )
    return {
        claim_id: ([primary] if primary else []) + list(others) for claim_id, primary, others in rows.all()
    }


def _ranked(views: list[knowledge_view.ClaimView]) -> list[knowledge_view.ClaimView]:
    return sorted(
        views, key=lambda view: (-view.rank, LEVEL_ORDER.get(view.level, len(LEVEL_ORDER)), view.text)
    )


def _fact(view: knowledge_view.ClaimView, fields: list[str]) -> Fact:
    return Fact(
        id=view.id,
        text=view.text,
        level=view.level,
        field=fields[0] if fields else None,
        fields=fields[1:],
        citations=[
            FactCitation(source_id=cite["sourceId"], quote=cite["quote"], locator=cite["locator"])
            for cite in view.citations
        ],
    )


def _source(source: Source) -> FactSource:
    shown = knowledge_view.source_ref(source)
    return FactSource(
        id=shown["id"],
        kind=shown["kind"],
        title=shown["title"],
        authors=shown["authors"],
        year=shown["year"],
        doi=shown["doi"],
        url=shown["url"],
        publisher=shown["publisher"],
        licence=shown["licence"],
        attribution=shown["attribution"],
    )


def _ref(craft: Craft) -> CraftRef:
    return CraftRef.model_validate(knowledge_view.craft_ref(craft))
