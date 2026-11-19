from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.models import (
    ArticleSection,
    ClaimSource,
    Compound,
    Craft,
    CuratedClaim,
    KnowledgePiece,
    KnowledgePieceSubject,
)
from app.research.article_sections import SectionSentence
from app.research.monograph_page import ComponentEntry, MonographContent, TextUnit

from . import knowledge_view

__all__ = ["SECTION_TAGS", "MonographLoad", "load_monograph"]

SECTION_TAGS = frozenset({"p", "li", "blockquote", "dd", "figcaption", "td"})
PUBLISHED = "PUBLISHED"
SUPERSEDED = "SUPERSEDED"
SHARED_PREFIX = "shared/"
TOPIC_PREFIX = "monograph:"
TOPIC_KEY_MAX = 200
LANGUAGE = "en"
DEPTH = "EXPERT"


@dataclass
class MonographLoad:
    craft_slug: str
    sections_written: list[str] = field(default_factory=list)
    sections_unchanged: list[str] = field(default_factory=list)
    sentences: int = 0
    sentences_awaiting_facts: int = 0
    components_written: list[str] = field(default_factory=list)
    components_unchanged: int = 0
    components_awaiting_facts: list[str] = field(default_factory=list)
    unresolved_subjects: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "craftSlug": self.craft_slug,
            "sectionsWritten": self.sections_written,
            "sectionsUnchanged": self.sections_unchanged,
            "sentences": self.sentences,
            "sentencesAwaitingFacts": self.sentences_awaiting_facts,
            "componentsWritten": len(self.components_written),
            "componentsUnchanged": self.components_unchanged,
            "componentsAwaitingFacts": self.components_awaiting_facts,
            "unresolvedSubjects": sorted(set(self.unresolved_subjects)),
        }


@dataclass(frozen=True)
class _Loading:
    craft: Craft
    content: MonographContent
    claims: Mapping[str, uuid.UUID]
    report: MonographLoad


async def load_monograph(session: AsyncSession, content: MonographContent, *, now: datetime) -> MonographLoad:
    craft = await knowledge_view.resolve_craft(session, content.craft_slug)
    if craft is None:
        raise InvalidInput(f"No craft has the slug {content.craft_slug}")
    report = MonographLoad(craft_slug=craft.slug)
    claims = await _claim_ids(session, craft.id)
    sections = _sections(content, claims, report)
    for discipline, sentences in sections.items():
        written = await _write_section(session, craft.id, discipline, sentences)
        (report.sections_written if written else report.sections_unchanged).append(discipline)
    loading = _Loading(craft=craft, content=content, claims=claims, report=report)
    for component in content.components:
        await _register(session, loading, component)
    await session.flush()
    return report


async def _claim_ids(session: AsyncSession, craft_id: uuid.UUID) -> dict[str, uuid.UUID]:
    rows = await session.execute(
        select(CuratedClaim.key, CuratedClaim.claimId).where(CuratedClaim.craftId == craft_id)
    )
    return {str(key): claim_id for key, claim_id in rows.all()}


def _sections(
    content: MonographContent, claims: Mapping[str, uuid.UUID], report: MonographLoad
) -> dict[str, list[SectionSentence]]:
    sections: dict[str, list[SectionSentence]] = {}
    for entry in content.layout:
        unit = content.units.get(entry.ref) if entry.kind == "unit" else None
        if unit is None or unit.field is None or unit.tag not in SECTION_TAGS:
            continue
        for text, keys in _unit_sentences(unit):
            if not keys:
                continue
            found = _stored_claims(content, keys, claims)
            if not found:
                report.sentences_awaiting_facts += 1
                continue
            sections.setdefault(unit.field, []).append(SectionSentence(text=text, claim_ids=found))
            report.sentences += 1
    return sections


def _unit_sentences(unit: TextUnit) -> list[tuple[str, list[str]]]:
    marked = [node for node in unit.nodes if isinstance(node, dict) and node.get("m") == "s"]
    if not marked:
        return [(_text(unit.nodes).strip(), _cites(unit.nodes))]
    return [(_text(node["c"]).strip(), _cites(node["c"])) for node in marked]


def _text(nodes: Sequence[Any]) -> str:
    return "".join(node if isinstance(node, str) else _text(node.get("c", [])) for node in nodes)


def _cites(nodes: Sequence[Any]) -> list[str]:
    keys: list[str] = []
    for node in nodes:
        if isinstance(node, dict):
            if node.get("m") == "cite":
                keys.append(node["key"])
            keys += _cites(node.get("c", []))
    return keys


def _stored_claims(
    content: MonographContent, keys: Iterable[str], claims: Mapping[str, uuid.UUID]
) -> list[uuid.UUID]:
    found = [claims[key] for cite in keys for key in content.citation_claims.get(cite, []) if key in claims]
    return list(dict.fromkeys(found))


async def _write_section(
    session: AsyncSession, craft_id: uuid.UUID, discipline: str, sentences: list[SectionSentence]
) -> bool:
    stored = [sentence.model_dump(mode="json", by_alias=True) for sentence in sentences]
    current = await session.scalar(
        select(ArticleSection).where(
            ArticleSection.craftId == craft_id,
            ArticleSection.field == discipline,
            ArticleSection.status == PUBLISHED,
        )
    )
    if current is not None and current.sentences == stored:
        return False
    latest = await session.scalar(
        select(func.max(ArticleSection.version)).where(
            ArticleSection.craftId == craft_id, ArticleSection.field == discipline
        )
    )
    if current is not None:
        current.status = SUPERSEDED
        await session.flush()
    session.add(
        ArticleSection(
            craftId=craft_id, field=discipline, version=(latest or 0) + 1, sentences=stored, status=PUBLISHED
        )
    )
    return True


async def _register(session: AsyncSession, loading: _Loading, component: ComponentEntry) -> None:
    content, report = loading.content, loading.report
    units = [e.ref for e in content.layout if e.kind == "unit" and e.within == component.label]
    keys = [key for ref in units for key in _cites(content.units[ref].nodes)]
    claim_ids = _stored_claims(content, keys, loading.claims)
    if not claim_ids:
        report.components_awaiting_facts.append(component.label)
        return
    source_ids = await _source_ids(session, claim_ids)
    values = _piece_values(loading.craft, content, component, (claim_ids, source_ids, units))
    row = await session.scalar(select(KnowledgePiece).where(KnowledgePiece.label == component.label))
    if row is not None and row.contentHash == values["contentHash"]:
        report.components_unchanged += 1
        return
    if row is None:
        row = KnowledgePiece(**values)
        session.add(row)
    else:
        for name, value in values.items():
            setattr(row, name, value)
    await session.flush()
    await _write_subjects(session, row.id, component.subjects, report)
    report.components_written.append(component.label)


async def _source_ids(session: AsyncSession, claim_ids: Sequence[uuid.UUID]) -> list[str]:
    rows = await session.scalars(
        select(ClaimSource.sourceId).where(ClaimSource.claimId.in_(list(claim_ids))).distinct()
    )
    return sorted(str(source_id) for source_id in rows)


def _piece_values(
    craft: Craft,
    content: MonographContent,
    component: ComponentEntry,
    rests_on: tuple[list[uuid.UUID], list[str], list[str]],
) -> dict[str, Any]:
    claim_ids, source_ids, units = rests_on
    payload = {
        "monograph": content.craft_slug,
        "anchor": component.anchor,
        "chapter": component.chapter,
        "units": units,
    }
    described = {
        "label": component.label,
        "kind": component.kind,
        "title": component.title,
        "description": component.description,
        "fields": component.fields,
        "subjects": component.subjects,
        "payload": payload,
        "claimIds": [str(claim_id) for claim_id in claim_ids],
        "sourceIds": source_ids,
    }
    return {
        "craftId": None if component.label.startswith(SHARED_PREFIX) else craft.id,
        "kind": component.kind,
        "facet": component.field,
        "topicKey": f"{TOPIC_PREFIX}{component.label}"[:TOPIC_KEY_MAX],
        "language": LANGUAGE,
        "depth": DEPTH,
        "payload": payload,
        "claimIds": claim_ids,
        "sourceIds": source_ids,
        "contentHash": hashlib.sha256(json.dumps(described, sort_keys=True).encode("utf-8")).hexdigest(),
        "label": component.label,
        "title": component.title,
        "description": component.description,
        "fields": [f for f in component.fields if f != component.field],
    }


async def _write_subjects(
    session: AsyncSession, piece_id: uuid.UUID, subjects: Sequence[str], report: MonographLoad
) -> None:
    await session.execute(delete(KnowledgePieceSubject).where(KnowledgePieceSubject.pieceId == piece_id))
    seen: set[str] = set()
    for subject in subjects:
        values = await _subject_values(session, subject)
        if values is None:
            report.unresolved_subjects.append(subject)
            continue
        key = json.dumps(values, default=str, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        session.add(KnowledgePieceSubject(pieceId=piece_id, **values))
    await session.flush()


async def _subject_values(session: AsyncSession, subject: str) -> dict[str, Any] | None:
    kind, _, key = subject.partition(":")
    if kind == "craft":
        craft = await knowledge_view.resolve_craft(session, key)
        return {"kind": "CRAFT", "craftId": craft.id} if craft else None
    if kind == "compound" and key.isdigit():
        compound_id = await session.scalar(select(Compound.id).where(Compound.pubchemCid == int(key)))
        return {"kind": "COMPOUND", "compoundId": compound_id} if compound_id else None
    if kind == "place" and key.startswith(("lgd:", "basin:")):
        return {"kind": "PLACE", "placeKey": key}
    return None
