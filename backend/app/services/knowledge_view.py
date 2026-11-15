import time
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.craft_master_loader import normalise
from app.models import (
    AdminDistrict,
    AdminState,
    Claim,
    ClaimSource,
    Concept,
    ConceptEdge,
    Craft,
    CraftAlias,
    CraftCategory,
    CraftLocation,
    CraftSubCategory,
    Process,
    ProcessStage,
    Source,
)

HIDDEN_CLAIM_STATUSES = ("DRAFT", "REJECTED", "RETRACTED")
VISIBLE_SENSITIVITY = "OPEN"
LEVEL_ORDER = {"VERIFIED": 0, "REVIEWED": 1, "PROVISIONAL": 2, "HYPOTHESIS": 3}
MATERIAL_TYPES = ("MATERIAL", "TOOL")
STAGE_TYPE = "PROCESS_STAGE"
EDGE_SECTION = "RELATIONS"
SECTION_HEADINGS = {
    "TRADITION": "The tradition",
    "HISTORICAL_CONTEXT": "History",
    "DESIGN_PRINCIPLE": "Design",
    "MECHANISM": "How it works",
    "EXPLANATION": "How it works",
    "ENVIRONMENTAL_CONDITION": "Place and climate",
    "PROCESS_STAGE": "Process",
    "ARTISAN_ACTION": "Process",
    "ARTISAN_DECISION": "The artisan's judgement",
    "SENSORY_CUE": "The artisan's judgement",
    "MATERIAL": "Materials and tools",
    "TOOL": "Materials and tools",
    "OUTCOME": "Results",
    "COMPARISON": "Comparisons",
    "OPEN_QUESTION": "Open questions",
    EDGE_SECTION: "How the steps connect",
}
SECTION_ORDER = [
    "The tradition",
    "History",
    "Design",
    "Materials and tools",
    "Process",
    "How it works",
    "How the steps connect",
    "Place and climate",
    "The artisan's judgement",
    "Results",
    "Comparisons",
    "Other findings",
    "Open questions",
]
MIN_ALIAS_LENGTH = 4
ALIAS_CACHE_SECONDS = 300.0


@dataclass
class ClaimView:
    id: uuid.UUID
    text: str
    level: str
    concept_type: str
    concept_id: uuid.UUID | None
    rank: float = 0.0
    citations: list[dict[str, Any]] = field(default_factory=list)

    def payload(self) -> dict[str, Any]:
        return {"id": str(self.id), "text": self.text, "level": self.level, "citations": self.citations}


def source_ref(source: Source) -> dict[str, Any]:
    authors = [str(a) if not isinstance(a, dict) else str(a.get("name") or "") for a in source.authors or []]
    url = source.url if source.url and source.url.startswith("https://") else None
    if url is None and source.doi:
        url = f"https://doi.org/{source.doi}"
    return {
        "id": str(source.id),
        "kind": source.kind,
        "title": source.title,
        "authors": [a for a in authors if a],
        "year": source.year,
        "doi": source.doi,
        "url": url,
        "publisher": source.publisher,
        "licence": source.licence,
        "attribution": source.attribution,
        "reliability": source.reliability,
    }


def citation(cite: ClaimSource, level: str) -> dict[str, Any]:
    return {
        "id": str(cite.id),
        "claimId": str(cite.claimId),
        "sourceId": str(cite.sourceId),
        "quote": cite.quote,
        "locator": cite.locator,
        "context": None,
        "evidence": "QUOTED" if cite.quote else "INFERRED",
        "level": level,
    }


def section_heading(concept_type: str) -> str:
    return SECTION_HEADINGS.get(concept_type, "Other findings")


def order_claims(claims: Iterable[ClaimView]) -> list[ClaimView]:
    return sorted(
        claims,
        key=lambda c: (
            SECTION_ORDER.index(section_heading(c.concept_type)),
            -c.rank,
            LEVEL_ORDER.get(c.level, 9),
            c.text,
        ),
    )


async def resolve_craft(session: AsyncSession, slug: str) -> Craft | None:
    craft = (await session.execute(select(Craft).where(Craft.slug == slug))).scalar_one_or_none()
    hops = 0
    while craft is not None and craft.status == "MERGED" and craft.mergedIntoId and hops < 5:
        craft = await session.get(Craft, craft.mergedIntoId)
        hops += 1
    return craft


def craft_ref(craft: Craft) -> dict[str, Any]:
    return {"slug": craft.slug, "name": craft.name, "path": f"/crafts/{craft.slug}"}


async def craft_concepts(session: AsyncSession, craft: Craft) -> list[Concept]:
    scope = [Concept.craftId == craft.id]
    if craft.subCategoryId is not None:
        scope.append((Concept.craftId.is_(None)) & (Concept.subCategoryId == craft.subCategoryId))
    return list(
        (
            await session.execute(
                select(Concept).where(or_(*scope), Concept.sensitivity == VISIBLE_SENSITIVITY)
            )
        )
        .scalars()
        .all()
    )


async def claims_for(
    session: AsyncSession, concepts: list[Concept], *, question: str | None = None
) -> tuple[list[ClaimView], dict[uuid.UUID, Source]]:
    if not concepts:
        return [], {}
    by_id = {c.id: c for c in concepts}
    edges = list(
        (
            await session.execute(
                select(ConceptEdge).where(
                    or_(ConceptEdge.srcId.in_(list(by_id)), ConceptEdge.dstId.in_(list(by_id)))
                )
            )
        )
        .scalars()
        .all()
    )
    edge_ids = [edge.id for edge in edges]
    subject = or_(
        (Claim.subjectType == "CONCEPT") & Claim.subjectId.in_(list(by_id)),
        (Claim.subjectType == "EDGE") & Claim.subjectId.in_(edge_ids) if edge_ids else text("false"),
    )
    rank_column: Any = text("0")
    if question and question.strip():
        query = func.websearch_to_tsquery("english", question.strip())
        rank_column = func.ts_rank(Claim.tsv, query)
    rows = (
        await session.execute(
            select(Claim, rank_column).where(
                subject,
                Claim.status.not_in(HIDDEN_CLAIM_STATUSES),
                Claim.sensitivity == VISIBLE_SENSITIVITY,
            )
        )
    ).all()
    if not rows:
        return [], {}
    claim_ids = [claim.id for claim, _ in rows]
    cites = (
        (await session.execute(select(ClaimSource).where(ClaimSource.claimId.in_(claim_ids)))).scalars().all()
    )
    source_ids = {cite.sourceId for cite in cites}
    sources = {
        source.id: source
        for source in (
            await session.execute(
                select(Source).where(Source.id.in_(source_ids), Source.sensitivity != "RESTRICTED")
            )
        )
        .scalars()
        .all()
    }
    by_claim: dict[uuid.UUID, list[ClaimSource]] = {}
    for cite in cites:
        if cite.sourceId in sources:
            by_claim.setdefault(cite.claimId, []).append(cite)
    edge_concept = {edge.id: edge.srcId if edge.srcId in by_id else edge.dstId for edge in edges}
    views: list[ClaimView] = []
    for claim, rank in rows:
        attached = by_claim.get(claim.id)
        if not attached:
            continue
        if claim.subjectType == "EDGE":
            concept_id = edge_concept.get(claim.subjectId)
            concept_type = EDGE_SECTION
        else:
            concept_id = claim.subjectId
            concept_type = by_id[claim.subjectId].type
        attached.sort(key=lambda c: (c.quote is None, str(c.id)))
        views.append(
            ClaimView(
                id=claim.id,
                text=claim.text,
                level=claim.evidenceLevel,
                concept_type=concept_type,
                concept_id=concept_id,
                rank=float(rank or 0),
                citations=[citation(c, claim.evidenceLevel) for c in attached],
            )
        )
    return views, sources


async def state_points(session: AsyncSession) -> dict[str, dict[str, Any]]:
    rows = (
        await session.execute(
            select(
                AdminState.lgd,
                AdminState.name,
                func.ST_Y(func.ST_PointOnSurface(AdminState.geom)),
                func.ST_X(func.ST_PointOnSurface(AdminState.geom)),
            )
        )
    ).all()
    return {
        name.casefold(): {"lgd": lgd, "name": name, "latitude": lat, "longitude": lon}
        for lgd, name, lat, lon in rows
    }


async def craft_locations(session: AsyncSession, craft: Craft) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    rows = (
        await session.execute(
            select(
                CraftLocation,
                AdminState.name,
                AdminDistrict.name,
                func.ST_Y(func.coalesce(func.geometry(CraftLocation.geom), AdminDistrict.centroid)),
                func.ST_X(func.coalesce(func.geometry(CraftLocation.geom), AdminDistrict.centroid)),
            )
            .outerjoin(AdminState, AdminState.lgd == CraftLocation.stateLgd)
            .outerjoin(AdminDistrict, AdminDistrict.lgd == CraftLocation.districtLgd)
            .where(CraftLocation.craftId == craft.id)
        )
    ).all()
    seen_states: set[str] = set()
    for location, state_name, district_name, lat, lon in rows:
        if state_name:
            seen_states.add(state_name.casefold())
        out.append(
            {
                "id": str(location.id),
                "precision": location.precision,
                "placeLabel": location.placeLabel or district_name or state_name or craft.name,
                "stateName": state_name,
                "districtName": district_name,
                "latitude": lat,
                "longitude": lon,
                "level": location.evidenceLevel,
            }
        )
    states = await state_points(session)
    for name in craft.stateOfPractice or []:
        point = states.get(str(name).casefold())
        if point is None or point["name"].casefold() in seen_states:
            continue
        seen_states.add(point["name"].casefold())
        out.append(
            {
                "id": f"state-{point['lgd']}",
                "precision": "STATE",
                "placeLabel": point["name"],
                "stateName": point["name"],
                "districtName": None,
                "latitude": point["latitude"],
                "longitude": point["longitude"],
                "level": "REVIEWED",
            }
        )
    return out


async def craft_profile(session: AsyncSession, craft: Craft) -> dict[str, Any]:
    names = (
        await session.execute(
            select(CraftSubCategory.name, CraftCategory.name)
            .join(CraftCategory, CraftCategory.id == CraftSubCategory.categoryId)
            .where(CraftSubCategory.id == craft.subCategoryId)
        )
    ).first()
    concepts = await craft_concepts(session, craft)
    claims, sources = await claims_for(session, concepts)
    stage_rows = (
        (
            await session.execute(
                select(ProcessStage)
                .join(Process, Process.id == ProcessStage.processId)
                .where(Process.craftId == craft.id)
                .order_by(Process.name, ProcessStage.ordinal)
            )
        )
        .scalars()
        .all()
    )
    stage_concepts = {stage.conceptId for stage in stage_rows if stage.conceptId}
    material_concepts = sorted(
        (c for c in concepts if c.type in MATERIAL_TYPES), key=lambda c: (c.type, c.name.casefold())
    )
    material_ids = {c.id for c in material_concepts}
    by_concept: dict[uuid.UUID | None, list[ClaimView]] = {}
    for view in claims:
        by_concept.setdefault(view.concept_id, []).append(view)

    def facet(concept_id: uuid.UUID | None) -> list[dict[str, Any]]:
        return [view.payload() for view in order_claims(by_concept.get(concept_id, []))]

    overview = [
        view.payload()
        for view in order_claims(
            v
            for v in claims
            if v.concept_type == EDGE_SECTION
            or (v.concept_id not in stage_concepts and v.concept_id not in material_ids)
        )
    ]
    stages = [
        {
            "id": str(stage.id),
            "ordinal": stage.ordinal,
            "name": stage.name,
            "stageType": stage.stageType,
            "durationText": stage.durationText,
            "claims": facet(stage.conceptId) if stage.conceptId else [],
        }
        for stage in stage_rows
    ]
    materials = [
        {"id": str(c.id), "name": c.name, "description": c.description, "claims": facet(c.id)}
        for c in material_concepts
    ]
    cited: list[str] = []
    for view in claims:
        for cite in view.citations:
            if cite["sourceId"] not in cited:
                cited.append(cite["sourceId"])
    return {
        "craft": {
            **craft_ref(craft),
            "id": str(craft.id),
            "localName": craft.localName,
            "giStatus": craft.giStatus,
            "stateOfPractice": list(craft.stateOfPractice or []),
            "stateOfOrigin": list(craft.stateOfOrigin or []),
            "description": craft.description,
            "categoryName": names[1] if names else craft.category,
            "subCategoryName": names[0] if names else None,
        },
        "overview": overview,
        "locations": await craft_locations(session, craft),
        "stages": stages,
        "materials": materials,
        "science": [],
        "sources": [source_ref(sources[uuid.UUID(sid)]) for sid in cited],
    }


async def map_points(session: AsyncSession) -> list[dict[str, Any]]:
    states = await state_points(session)
    crafts = (
        await session.execute(
            select(Craft.slug, Craft.name, Craft.stateOfPractice).where(
                Craft.status == "ACTIVE", Craft.isCatchAll.is_(False)
            )
        )
    ).all()
    points: dict[str, dict[str, Any]] = {}
    for slug, name, practice in crafts:
        for state in practice or []:
            point = states.get(str(state).casefold())
            if point is None or point["latitude"] is None:
                continue
            key = f"state-{point['lgd']}"
            entry = points.setdefault(
                key,
                {
                    "key": key,
                    "name": point["name"],
                    "latitude": point["latitude"],
                    "longitude": point["longitude"],
                    "crafts": {},
                },
            )
            entry["crafts"][slug] = {"slug": slug, "name": name, "path": f"/crafts/{slug}"}
    located = (
        await session.execute(
            select(
                Craft.slug,
                Craft.name,
                CraftLocation.placeLabel,
                AdminDistrict.lgd,
                AdminDistrict.name,
                func.ST_Y(func.coalesce(func.geometry(CraftLocation.geom), AdminDistrict.centroid)),
                func.ST_X(func.coalesce(func.geometry(CraftLocation.geom), AdminDistrict.centroid)),
            )
            .join(Craft, Craft.id == CraftLocation.craftId)
            .outerjoin(AdminDistrict, AdminDistrict.lgd == CraftLocation.districtLgd)
            .where(Craft.status == "ACTIVE", CraftLocation.precision.in_(("DISTRICT", "POINT")))
        )
    ).all()
    for slug, name, label, district_lgd, district_name, lat, lon in located:
        if lat is None or lon is None:
            continue
        key = f"district-{district_lgd}" if district_lgd else f"point-{lat:.3f},{lon:.3f}"
        entry = points.setdefault(
            key,
            {
                "key": key,
                "name": label or district_name or name,
                "latitude": lat,
                "longitude": lon,
                "crafts": {},
            },
        )
        entry["crafts"][slug] = {"slug": slug, "name": name, "path": f"/crafts/{slug}"}
    out = []
    for entry in points.values():
        listed = sorted(entry["crafts"].values(), key=lambda c: c["name"].casefold())
        out.append({**entry, "total": len(listed), "crafts": listed})
    return sorted(out, key=lambda p: p["name"].casefold())


_alias_cache: dict[str, Any] = {"at": 0.0, "rows": []}


async def alias_rows(session: AsyncSession) -> list[tuple[str, uuid.UUID]]:
    now = time.monotonic()
    if _alias_cache["rows"] and now - _alias_cache["at"] < ALIAS_CACHE_SECONDS:
        return _alias_cache["rows"]
    crafts = (
        await session.execute(
            select(Craft.id, Craft.name).where(Craft.status == "ACTIVE", Craft.isCatchAll.is_(False))
        )
    ).all()
    active = {craft_id for craft_id, _ in crafts}
    rows = [(normalise(name), craft_id) for craft_id, name in crafts]
    aliases = (
        await session.execute(
            select(CraftAlias.aliasNorm, CraftAlias.craftId).where(CraftAlias.status == "ACTIVE")
        )
    ).all()
    rows.extend((alias, craft_id) for alias, craft_id in aliases if craft_id in active)
    cleaned = sorted({(alias, craft_id) for alias, craft_id in rows if len(alias) >= MIN_ALIAS_LENGTH})
    _alias_cache.update(at=now, rows=cleaned)
    return cleaned


def match_aliases(question: str, rows: list[tuple[str, uuid.UUID]]) -> list[uuid.UUID]:
    padded = f" {normalise(question)} "
    best = 0
    found: dict[uuid.UUID, int] = {}
    for alias, craft_id in rows:
        if f" {alias} " in padded:
            length = len(alias)
            found[craft_id] = max(found.get(craft_id, 0), length)
            best = max(best, length)
    return sorted((cid for cid, length in found.items() if length == best), key=str)


def reset_alias_cache() -> None:
    _alias_cache.update(at=0.0, rows=[])
