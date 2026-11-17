from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import and_, case, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Claim, Concept, Craft, Term, TermConcept, TermCraft
from app.research.blocks_learning import CONCEPT_CRAFTS_MAX
from app.research.citations import SourceRef
from app.research.crafts import CraftRef
from app.research.offered_facts import OfferedFact
from app.research.retrieval import HIDDEN_CLAIM_STATUSES, VISIBLE_SENSITIVITY
from app.research.shared_science import (
    SHARED_SCIENCE_NODES_MAX,
    SharedConcept,
    SharedScience,
    TermCraftOffer,
    TermOffer,
    shared_concept,
    shared_science,
)
from app.research.vocabulary import FACT_LEVELS, LEVEL_ORDER

from . import knowledge_view
from .learning_facts import offered_fact, source_refs

__all__ = [
    "CLAIMS_PER_CONCEPT",
    "SHARED_TERMS_SCANNED",
    "TermOffers",
    "craft_shared_science",
    "shared_concept_of",
    "term_ids_of",
    "term_offers",
]

CLAIMS_PER_CONCEPT = 3
SHARED_TERMS_SCANNED = 2 * SHARED_SCIENCE_NODES_MAX
MERGED = "MERGED"
CONCEPT_SUBJECT = "CONCEPT"


@dataclass(frozen=True)
class TermOffers:
    offers: tuple[TermOffer, ...] = ()
    sources: Mapping[str, SourceRef] = field(default_factory=dict)


async def craft_shared_science(session: AsyncSession, craft: Craft) -> SharedScience:
    found = await term_offers(session, await _shared_term_ids(session, craft.id), focus=craft.id)
    return shared_science(
        CraftRef.model_validate(knowledge_view.craft_ref(craft)), found.offers, found.sources
    )


async def shared_concept_of(
    session: AsyncSession, term_key: str, focus: Craft | None
) -> SharedConcept | None:
    term_ids = await term_ids_of(session, [term_key])
    if not term_ids:
        return None
    found = await term_offers(session, term_ids, focus=focus.id if focus is not None else None)
    if not found.offers:
        return None
    return shared_concept(found.offers[0], found.sources, focus=focus.slug if focus is not None else None)


async def term_ids_of(session: AsyncSession, keys: Sequence[str]) -> list[uuid.UUID]:
    if not keys:
        return []
    rows = (await session.execute(select(Term.key, Term.id).where(Term.key.in_(list(keys))))).all()
    by_key = {row.key: row.id for row in rows}
    return [by_key[key] for key in dict.fromkeys(keys) if key in by_key]


async def term_offers(
    session: AsyncSession, term_ids: Sequence[uuid.UUID], *, focus: uuid.UUID | None = None
) -> TermOffers:
    if not term_ids:
        return TermOffers()
    terms = await _terms(session, term_ids)
    crafts = await _term_crafts(session, term_ids, focus)
    craft_ids = {craft_id for rows in crafts.values() for craft_id, _ in rows}
    concepts = await _term_concepts(session, term_ids, craft_ids)
    claim_ids = await _ranked_claim_ids(session, term_ids, [c for ids in concepts.values() for c in ids])
    views, sources = await knowledge_view.claims_by_id(session, claim_ids)
    refs = source_refs(sources)
    facts: dict[uuid.UUID, list[OfferedFact]] = defaultdict(list)
    for view in views.values():
        fact = offered_fact(view, refs)
        if fact is not None and view.concept_id is not None:
            facts[view.concept_id].append(fact)
    offers = tuple(
        _offer(terms[term_id], crafts.get(term_id, []), concepts, facts)
        for term_id in term_ids
        if term_id in terms
    )
    return TermOffers(offers=offers, sources=refs)


def _offer(
    term: Any,
    crafts: Sequence[tuple[uuid.UUID, CraftRef]],
    concepts: Mapping[tuple[uuid.UUID, uuid.UUID], Sequence[uuid.UUID]],
    facts: Mapping[uuid.UUID, Sequence[OfferedFact]],
) -> TermOffer:
    entries = []
    for craft_id, craft in crafts:
        own = tuple(concepts.get((term.id, craft_id), ()))
        if own:
            found = tuple(fact for concept_id in own for fact in facts.get(concept_id, ()))
            entries.append(TermCraftOffer(craft=craft, concept_ids=own, facts=found))
    return TermOffer(
        key=term.key,
        label=term.label,
        surfaces=(term.label, *term.aliases, *term.localNames),
        crafts=tuple(entries),
    )


async def _shared_term_ids(session: AsyncSession, craft_id: uuid.UUID) -> list[uuid.UUID]:
    others = (
        select(TermCraft.termId)
        .join(Craft, Craft.id == TermCraft.craftId)
        .where(TermCraft.craftId != craft_id, Craft.status != MERGED)
    )
    rows = await session.scalars(
        select(Term.id)
        .join(TermCraft, TermCraft.termId == Term.id)
        .where(TermCraft.craftId == craft_id, Term.id.in_(others))
        .order_by(Term.label, Term.key)
        .limit(SHARED_TERMS_SCANNED)
    )
    return list(rows)


async def _terms(session: AsyncSession, term_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, Any]:
    rows = await session.execute(
        select(Term.id, Term.key, Term.label, Term.aliases, Term.localNames).where(
            Term.id.in_(list(term_ids))
        )
    )
    return {row.id: row for row in rows.all()}


async def _term_crafts(
    session: AsyncSession, term_ids: Sequence[uuid.UUID], focus: uuid.UUID | None
) -> dict[uuid.UUID, list[tuple[uuid.UUID, CraftRef]]]:
    first = case((Craft.id == focus, 0), else_=1) if focus is not None else literal(1)
    numbered = (
        select(
            TermCraft.termId.label("term_id"),
            Craft.id.label("craft_id"),
            Craft.slug.label("slug"),
            Craft.name.label("name"),
            func.row_number()
            .over(partition_by=TermCraft.termId, order_by=(first, Craft.name, Craft.slug))
            .label("n"),
        )
        .join(Craft, Craft.id == TermCraft.craftId)
        .where(TermCraft.termId.in_(list(term_ids)), Craft.status != MERGED)
        .subquery()
    )
    rows = await session.execute(
        select(numbered).where(numbered.c.n <= CONCEPT_CRAFTS_MAX).order_by(numbered.c.term_id, numbered.c.n)
    )
    crafts: dict[uuid.UUID, list[tuple[uuid.UUID, CraftRef]]] = defaultdict(list)
    for row in rows.all():
        ref = CraftRef(slug=row.slug, name=row.name, path=f"/crafts/{row.slug}")
        crafts[row.term_id].append((row.craft_id, ref))
    return crafts


async def _term_concepts(
    session: AsyncSession, term_ids: Sequence[uuid.UUID], craft_ids: set[uuid.UUID]
) -> dict[tuple[uuid.UUID, uuid.UUID], list[uuid.UUID]]:
    if not craft_ids:
        return {}
    rows = await session.execute(
        select(TermConcept.termId, Concept.id, Concept.craftId)
        .join(Concept, Concept.id == TermConcept.conceptId)
        .where(
            TermConcept.termId.in_(list(term_ids)),
            Concept.craftId.in_(list(craft_ids)),
            Concept.sensitivity == VISIBLE_SENSITIVITY,
        )
        .order_by(TermConcept.termId, Concept.craftId, Concept.name, Concept.id)
    )
    concepts: dict[tuple[uuid.UUID, uuid.UUID], list[uuid.UUID]] = defaultdict(list)
    for row in rows.all():
        concepts[(row.termId, row.craftId)].append(row.id)
    return concepts


async def _ranked_claim_ids(
    session: AsyncSession, term_ids: Sequence[uuid.UUID], concept_ids: Sequence[uuid.UUID]
) -> list[uuid.UUID]:
    if not concept_ids:
        return []
    level_rank = case(dict(LEVEL_ORDER), value=Claim.evidenceLevel, else_=len(LEVEL_ORDER))
    names = case((func.strpos(func.lower(Claim.text), func.lower(Term.label)) > 0, 0), else_=1)
    numbered = (
        select(
            Claim.id.label("claim_id"),
            func.row_number()
            .over(
                partition_by=(TermConcept.termId, Claim.subjectId),
                order_by=(names, level_rank, Claim.createdAt, Claim.id),
            )
            .label("n"),
        )
        .join(
            TermConcept,
            and_(TermConcept.conceptId == Claim.subjectId, TermConcept.termId.in_(list(term_ids))),
        )
        .join(Term, Term.id == TermConcept.termId)
        .where(
            Claim.subjectType == CONCEPT_SUBJECT,
            Claim.subjectId.in_(list(dict.fromkeys(concept_ids))),
            Claim.status.not_in(HIDDEN_CLAIM_STATUSES),
            Claim.sensitivity == VISIBLE_SENSITIVITY,
            Claim.evidenceLevel.in_(FACT_LEVELS),
        )
        .subquery()
    )
    rows = await session.scalars(select(numbered.c.claim_id).where(numbered.c.n <= CLAIMS_PER_CONCEPT))
    return list(dict.fromkeys(rows))
