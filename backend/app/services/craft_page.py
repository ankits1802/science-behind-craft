from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping, Sequence
from types import MappingProxyType
from typing import Any

from app.models.enums import DISCIPLINES
from app.research.blocks import ProseBlock
from app.research.citations import Citation, SourceRef
from app.research.craft_page import (
    CRAFT_PAGE_SCHEMA_VERSION,
    CraftPage,
    CurationHeader,
    KeyFact,
    OverviewSection,
    PageClaim,
    PageOverview,
    PageSentence,
    SearchedFor,
    SubjectRef,
)
from app.research.knowledge_pieces import KnowledgePiece
from app.research.sections import DISCIPLINE_TITLES
from app.research.vocabulary import LEVEL_ORDER, weakest_level

from .craft_page_context import (
    page_depth,
    page_environment,
    page_events,
    page_gi,
    page_tabs,
)
from .craft_page_evidence import page_evidence, stored_overview_sections
from .craft_page_family import family_place, suggested_questions
from .craft_page_parts import (
    Visible,
    page_communities,
    page_differ,
    page_glossary,
    page_pictures,
    page_places,
    page_process,
    page_questions,
)
from .craft_page_records import ClaimFacts, CraftPageRecords
from .curated_index import CuratedPage
from .knowledge_view import ClaimView

__all__ = [
    "CONCEPT_SUBJECT_KINDS",
    "CONCEPT_TYPE_DISCIPLINES",
    "ORIGIN_PROVENANCES",
    "craft_page",
    "page_claims",
]

CURATED = "CURATED"
HYPOTHESIS = "HYPOTHESIS"
FALLBACK_DISCIPLINE = "OVERVIEW"
CONCEPT_TYPE_DISCIPLINES: Mapping[str, str] = MappingProxyType(
    {
        "TRADITION": "OVERVIEW",
        "HISTORICAL_CONTEXT": "HISTORY",
        "DESIGN_PRINCIPLE": "DESIGN",
        "PROCESS_STAGE": "PROCESS",
        "ARTISAN_ACTION": "PROCESS",
        "ARTISAN_DECISION": "PROCESS",
        "SENSORY_CUE": "PROCESS",
        "MATERIAL": "MATERIALS",
        "TOOL": "MATERIALS",
        "PROPERTY": "MATERIALS",
        "MECHANISM": "CHEMISTRY",
        "EXPLANATION": "CHEMISTRY",
        "CHANGE": "CHEMISTRY",
        "ENVIRONMENTAL_CONDITION": "GEOGRAPHY",
    }
)
CONCEPT_SUBJECT_KINDS: Mapping[str, str] = MappingProxyType(
    {"PROCESS_STAGE": "STAGE", "MATERIAL": "MATERIAL", "TOOL": "TOOL", "TRADITION": "CRAFT"}
)
ORIGIN_PROVENANCES: Mapping[str, str] = MappingProxyType(
    {
        "IMPORT": "SEED",
        "RESEARCHER": "RESEARCHER",
        "ENRICHMENT": "FROM_ANSWERS",
        "MODEL": "FROM_ANSWERS",
        "LIVE_RESEARCH": "FROM_ANSWERS",
    }
)


def craft_page(records: CraftPageRecords) -> CraftPage:
    claims = page_claims(records)
    visible = Visible(
        levels={claim.id: claim.level for claim in claims},
        order={claim.id: index for index, claim in enumerate(claims)},
        disciplines={claim.id: claim.discipline for claim in claims},
    )
    curated = records.curated
    craft = records.craft
    parts = _parts(records, claims, visible)
    process, pictures = parts["process"], parts["pictures"]
    sources = _sources(claims, records.sources)
    place = family_place(craft.category_name, craft.sub_category_name)
    return CraftPage(
        schema_version=CRAFT_PAGE_SCHEMA_VERSION,
        craft=craft,
        curated=curated is not None,
        curation=_header(curated),
        tabs=page_tabs(process, records.offers, sources=bool(sources), evidence=bool(claims)),
        depth=page_depth(curated, claims, (len(sources), len(process.stages), len(pictures))),
        suggested_questions=suggested_questions(place, craft.display_name, catch_all=records.catch_all),
        same_family=list(records.relatives),
        evidence=page_evidence(claims),
        claims=claims,
        sources=_numbered(_reading_order(craft.local_names, parts, claims), claims, sources),
        **parts,
    )


def _parts(records: CraftPageRecords, claims: Sequence[PageClaim], visible: Visible) -> dict[str, Any]:
    curated = records.curated
    differ = page_differ(curated, visible)
    places = page_places(curated, visible)
    return {
        "overview": _overview(records, claims, visible),
        "gi_card": page_gi(records.craft.gi_status, records.market.gi, visible),
        "events": page_events(records.market, claims, visible, curated=curated is not None),
        "environment": page_environment(curated, visible, places),
        "sources_differ": differ,
        "places": places,
        "communities": page_communities(curated, visible, places),
        "process": page_process(records, visible, differ),
        "glossary": page_glossary(records, visible),
        "pictures": page_pictures(records, visible),
        "open_questions": page_questions(curated, visible),
    }


def page_claims(records: CraftPageRecords) -> list[PageClaim]:
    kinds = records.curated.concept_kinds() if records.curated else {}
    claims = [_claim(view, records.facts[view.id], kinds, records.craft.name) for view in records.views]
    return sorted(
        claims, key=lambda c: (DISCIPLINES.index(c.discipline), LEVEL_ORDER[c.level], c.text, str(c.id))
    )


def _claim(view: ClaimView, facts: ClaimFacts, kinds: Mapping[uuid.UUID, str], craft_name: str) -> PageClaim:
    concept_type = facts.concept_type or ""
    discipline = facts.discipline or CONCEPT_TYPE_DISCIPLINES.get(concept_type, FALLBACK_DISCIPLINE)
    if facts.concept_name is None:
        subject = SubjectRef(id=None, name=craft_name, kind="CRAFT")
    else:
        kind = kinds.get(view.concept_id) or CONCEPT_SUBJECT_KINDS.get(concept_type, "CONCEPT")
        subject = SubjectRef(id=view.concept_id, name=facts.concept_name, kind=kind)
    return PageClaim(
        id=view.id,
        text=view.text,
        level=view.level,
        discipline=discipline,
        subject=subject,
        provenance=CURATED if facts.discipline else ORIGIN_PROVENANCES[facts.origin],
        sources_differ=facts.sources_differ,
        citations=[Citation.model_validate(citation) for citation in view.citations],
    )


def _header(curated: CuratedPage | None) -> CurationHeader | None:
    if curated is None:
        return None
    return CurationHeader(
        version=curated.version,
        curated_at=curated.curated_at,
        coverage=curated.coverage,
        searched=[SearchedFor(query=item.query, site=item.site) for item in curated.searched],
    )


def _overview(records: CraftPageRecords, claims: Sequence[PageClaim], visible: Visible) -> PageOverview:
    curated = records.curated
    if curated is None:
        return PageOverview(lede=[], key_facts=[], sections=stored_overview_sections(claims))
    lede = records.pieces.get(curated.overview.lede_piece_id) if curated.overview.lede_piece_id else None
    sections = []
    for section in curated.overview.sections:
        sentences = _piece_sentences(records.pieces.get(section.piece_id), visible)
        if sentences:
            sections.append(
                OverviewSection(
                    discipline=section.discipline,
                    title=DISCIPLINE_TITLES[section.discipline],
                    basis=CURATED,
                    sentences=sentences,
                )
            )
    facts = [
        KeyFact(label=fact.label, value=fact.value, claim_ids=fact.claim_ids)
        for fact in curated.overview.key_facts
        if visible.all_shown(fact.claim_ids)
    ]
    return PageOverview(lede=_piece_sentences(lede, visible), key_facts=facts, sections=sections)


def _piece_sentences(piece: KnowledgePiece | None, visible: Visible) -> list[PageSentence]:
    if piece is None or not isinstance(piece.payload, ProseBlock):
        return []
    shown = []
    for sentence in piece.payload.sentences:
        claim_ids = list(dict.fromkeys(uuid.UUID(citation.claim_id) for citation in sentence.citations))
        if not visible.all_shown(claim_ids):
            continue
        level = weakest_level(visible.levels[claim_id] for claim_id in claim_ids)
        if level != HYPOTHESIS:
            shown.append(
                PageSentence(
                    id=sentence.id, text=sentence.text, level=level, claim_ids=claim_ids, terms=sentence.terms
                )
            )
    return shown


def _sources(claims: Sequence[PageClaim], known: Mapping[str, SourceRef]) -> list[SourceRef]:
    ordered = dict.fromkeys(citation.source_id for claim in claims for citation in claim.citations)
    return [known[source_id] for source_id in ordered if source_id in known]


def _reading_order(
    names: Iterable[Any], parts: Mapping[str, Any], claims: Sequence[PageClaim]
) -> list[uuid.UUID]:
    overview: PageOverview = parts["overview"]
    rows = [
        *overview.lede,
        *overview.key_facts,
        *parts["pictures"],
        *names,
        *(sentence for section in overview.sections for sentence in section.sentences),
        parts["gi_card"],
        *parts["events"],
        *parts["environment"],
        *parts["sources_differ"],
        *parts["open_questions"],
        *parts["glossary"],
    ]
    later = [*parts["places"], *parts["communities"]]
    return [
        *(claim_id for row in rows for claim_id in row.claim_ids),
        *parts["process"].cited_claim_ids(),
        *(claim_id for row in later for claim_id in row.claim_ids),
        *(claim.id for claim in claims),
    ]


def _numbered(
    order: Sequence[uuid.UUID], claims: Sequence[PageClaim], sources: Sequence[SourceRef]
) -> list[SourceRef]:
    cited = {claim.id: claim.citations for claim in claims}
    first = dict.fromkeys(citation.source_id for claim_id in order for citation in cited[claim_id])
    listed = {source.id: source for source in sources}
    return [listed[source_id] for source_id in first if source_id in listed]
