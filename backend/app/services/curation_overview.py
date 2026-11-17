from __future__ import annotations

import uuid
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass

from app.curation.dossier import Dossier
from app.curation.overview import OverviewSentence
from app.research.blocks import ProseBlock
from app.research.knowledge_pieces import KnowledgePiece, PieceSlot, knowledge_piece, piece_content_hash
from app.research.piece_topics import FACET_NAMESPACES, TopicSubjects, facet_topic
from app.research.subject_keys import topic_key
from app.research.term_marking import GlossaryEntry, TermMarker

from .answer_events import CitedClaims
from .curated_index import CuratedPage, IndexOverview, IndexSection
from .curation_keys import CURATED_DEPTH, curated_id
from .curation_records import glossary_key, term_names
from .curation_rows import CraftTarget
from .section_blocks import KeptSentence, prose_block, prose_problems

__all__ = [
    "LEDE_FACET",
    "LEDE_PART",
    "OverviewPieces",
    "curated_glossary",
    "indexed_overview",
    "overview_pieces",
    "piece_topic",
]

LEDE_PART = "lede"
LEDE_FACET = "OVERVIEW"


@dataclass(frozen=True)
class OverviewPieces:
    pieces: tuple[KnowledgePiece, ...]
    parts: Mapping[str, uuid.UUID]
    dropped: tuple[str, ...]


def curated_glossary(dossier: Dossier) -> list[GlossaryEntry]:
    entries = {}
    for term in dossier.glossary:
        key = glossary_key(term)
        if key is not None:
            entries.setdefault(key, GlossaryEntry(key=key, surfaces=tuple(term_names(term))))
    return list(entries.values())


def piece_topic(facet: str, craft: CraftTarget, districts: Sequence[str]) -> str:
    found = facet_topic(facet, TopicSubjects(craft_slug=craft.slug, districts=tuple(districts)))
    return found or topic_key(FACET_NAMESPACES[facet], craft.slug)


def overview_pieces(
    dossier: Dossier, craft: CraftTarget, cited: CitedClaims, districts: Sequence[str]
) -> OverviewPieces:
    marker = TermMarker(curated_glossary(dossier))
    pieces: list[KnowledgePiece] = []
    parts: dict[str, uuid.UUID] = {}
    dropped: list[str] = []
    for part, facet, sentences in _parts(dossier):
        kept = []
        for index, sentence in enumerate(sentences):
            candidate = _candidate(craft.slug, sentence)
            problems = prose_problems([candidate], cited)
            if problems:
                dropped.append(f"overview.{part}.{index}: {'; '.join(problems)}")
            else:
                kept.append(candidate)
        if kept:
            block = _marked(prose_block(f"curation.{part.lower()}", kept, cited), marker)
            piece = _piece(dossier, craft, (part, facet), block, piece_topic(facet, craft, districts))
            pieces.append(piece)
            parts[part] = piece.id
    return OverviewPieces(pieces=tuple(pieces), parts=parts, dropped=tuple(dropped))


def _parts(dossier: Dossier) -> Iterator[tuple[str, str, Sequence[OverviewSentence]]]:
    yield LEDE_PART, LEDE_FACET, dossier.overview.lede
    for section in dossier.overview.sections:
        yield section.discipline, section.discipline, section.sentences


def _candidate(slug: str, sentence: OverviewSentence) -> KeptSentence:
    claims = tuple(curated_id(slug, claim_id) for claim_id in sentence.claim_ids)
    return KeptSentence(text=sentence.text, claim_ids=claims, evidence_ids=(), open_question=False)


def _marked(block: ProseBlock, marker: TermMarker) -> ProseBlock:
    payload = block.model_dump(mode="json", by_alias=True)
    for sentence in payload["sentences"]:
        sentence["terms"] = [
            span.model_dump(mode="json", by_alias=True) for span in marker.spans(sentence["text"])
        ]
    return ProseBlock.model_validate(payload)


def _piece(
    dossier: Dossier, craft: CraftTarget, part: tuple[str, str], block: ProseBlock, topic: str
) -> KnowledgePiece:
    name, facet = part
    piece_id = curated_id(craft.slug, "piece", name, topic, piece_content_hash(block))
    slot = PieceSlot(craft.id, facet, topic, CURATED_DEPTH)
    return knowledge_piece(block, slot, piece_id=piece_id, answer_id=None, created_at=dossier.curated_at)


def indexed_overview(index: CuratedPage, overview: OverviewPieces) -> CuratedPage:
    sections = [
        IndexSection(discipline=part, piece_id=piece_id)
        for part, piece_id in overview.parts.items()
        if part != LEDE_PART
    ]
    placed = IndexOverview(
        lede_piece_id=overview.parts.get(LEDE_PART), sections=sections, key_facts=index.overview.key_facts
    )
    return index.model_copy(update={"overview": placed})
