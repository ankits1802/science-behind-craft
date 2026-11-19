from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, Select, and_, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AdminDistrict,
    Compound,
    Concept,
    Craft,
    CraftLocation,
    KnowledgePiece,
    KnowledgePieceSubject as Subject,
    Material,
    Process,
    ProcessStage,
    StageMaterial,
)
from app.models.enums import DISTRICT_PLACE_PREFIX
from app.research.knowledge_api import (
    COMPONENTS_LIMIT_MAX,
    ComponentSubject,
    ComponentSummary,
    CraftComponents,
)
from app.retrieval.statements import TEXT_SEARCH_CONFIG, lexical_rank, text_query
from app.retrieval.text import or_tsquery

from .knowledge_api import known_craft

__all__ = ["library_components"]

OPEN_CONCEPT = "OPEN"
DISTRICT_KEY_PREFIX = f"{DISTRICT_PLACE_PREFIX}:"
LABEL_SEPARATORS = "/-"


async def library_components(
    session: AsyncSession,
    *,
    slug: str | None = None,
    field: str | None = None,
    kind: str | None = None,
    query: str | None = None,
) -> CraftComponents:
    conditions = [
        KnowledgePiece.label.is_not(None),
        KnowledgePiece.hiddenAt.is_(None),
        KnowledgePiece.supersededById.is_(None),
    ]
    if slug is not None:
        craft = await known_craft(session, slug)
        conditions.append(or_(KnowledgePiece.craftId == craft.id, KnowledgePiece.id.in_(_applying(craft.id))))
    if field is not None:
        conditions.append(or_(KnowledgePiece.facet == field, KnowledgePiece.fields.any(field)))
    if kind is not None:
        conditions.append(KnowledgePiece.kind == kind)
    rows = (await session.execute(_listing(conditions, query))).all()
    subjects = await _subjects(session, [piece.id for piece, _ in rows])
    return CraftComponents(
        craft_slug=slug,
        field=field,
        kind=kind,
        query=query,
        components=[_summary(piece, owner, subjects.get(piece.id, [])) for piece, owner in rows],
    )


def _listing(conditions: list[ColumnElement[bool]], query: str | None) -> Select[Any]:
    statement = (
        select(KnowledgePiece, Craft.slug)
        .outerjoin(Craft, Craft.id == KnowledgePiece.craftId)
        .where(*conditions)
        .limit(COMPONENTS_LIMIT_MAX)
    )
    terms = or_tsquery(query) if query else None
    if query and terms is None:
        return statement.where(false())
    if terms is None:
        return statement.order_by(KnowledgePiece.label)
    document = _document()
    asked = text_query(terms)
    return statement.where(document.op("@@")(asked)).order_by(
        lexical_rank(document, asked).desc(), KnowledgePiece.label
    )


def _document() -> ColumnElement[Any]:
    words = func.concat_ws(
        " ",
        func.translate(KnowledgePiece.label, LABEL_SEPARATORS, " " * len(LABEL_SEPARATORS)),
        KnowledgePiece.title,
        KnowledgePiece.description,
    )
    return func.to_tsvector(TEXT_SEARCH_CONFIG, words)


def _applying(craft_id: uuid.UUID) -> Select[tuple[uuid.UUID]]:
    stages = (
        select(ProcessStage.id)
        .join(Process, Process.id == ProcessStage.processId)
        .where(Process.craftId == craft_id)
    )
    materials = select(StageMaterial.materialId).where(StageMaterial.stageId.in_(stages))
    concepts = (
        select(Concept.id).where(Concept.craftId == craft_id),
        select(ProcessStage.conceptId).where(ProcessStage.id.in_(stages)),
        select(Material.conceptId).where(Material.id.in_(materials)),
    )
    compounds = select(Material.compoundId).where(Material.id.in_(materials))
    places = select(func.concat(DISTRICT_KEY_PREFIX, CraftLocation.districtLgd)).where(
        CraftLocation.craftId == craft_id, CraftLocation.districtLgd.is_not(None)
    )
    return select(Subject.pieceId).where(
        or_(
            Subject.craftId == craft_id,
            *(Subject.conceptId.in_(found) for found in concepts),
            Subject.compoundId.in_(compounds),
            Subject.placeKey.in_(places),
        )
    )


async def _subjects(
    session: AsyncSession, piece_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, list[ComponentSubject]]:
    if not piece_ids:
        return {}
    rows = await session.execute(
        select(
            Subject,
            Craft.slug.label("craft_slug"),
            Craft.name.label("craft_name"),
            Concept.name.label("concept"),
            Compound.name.label("compound"),
            AdminDistrict.name.label("district"),
        )
        .outerjoin(Craft, Craft.id == Subject.craftId)
        .outerjoin(Concept, and_(Concept.id == Subject.conceptId, Concept.sensitivity == OPEN_CONCEPT))
        .outerjoin(Compound, Compound.id == Subject.compoundId)
        .outerjoin(AdminDistrict, func.concat(DISTRICT_KEY_PREFIX, AdminDistrict.lgd) == Subject.placeKey)
        .where(Subject.pieceId.in_(list(piece_ids)))
        .order_by(Subject.pieceId, Subject.kind, Subject.createdAt)
    )
    found: dict[uuid.UUID, list[ComponentSubject]] = {}
    for row in rows.all():
        shown = _subject(row[0], row)
        if shown is not None:
            found.setdefault(row[0].pieceId, []).append(shown)
    return found


def _subject(subject: Subject, names: Any) -> ComponentSubject | None:
    if subject.craftId is not None and names.craft_slug and names.craft_name:
        return ComponentSubject(kind=subject.kind, key=names.craft_slug, name=names.craft_name)
    if subject.conceptId is not None and names.concept:
        return ComponentSubject(kind=subject.kind, key=str(subject.conceptId), name=names.concept)
    if subject.compoundId is not None and names.compound:
        return ComponentSubject(kind=subject.kind, key=str(subject.compoundId), name=names.compound)
    if subject.placeKey is not None:
        return ComponentSubject(
            kind=subject.kind, key=subject.placeKey, name=names.district or subject.placeKey
        )
    return None


def _summary(piece: KnowledgePiece, owner: str | None, subjects: list[ComponentSubject]) -> ComponentSummary:
    return ComponentSummary(
        label=piece.label,
        title=piece.title,
        description=piece.description,
        kind=piece.kind,
        field=piece.facet,
        fields=piece.fields,
        craft_slug=owner,
        subjects=subjects,
    )
