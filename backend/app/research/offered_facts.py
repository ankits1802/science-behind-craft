from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from app.models.enums import RELIABILITIES

from .blocks import ExplainerSentence, named_in
from .citations import AnswerSentence, SourceRef
from .term_marking import GlossaryEntry, TermMarker
from .vocabulary import LEVEL_ORDER

__all__ = [
    "PIECE_FIRST",
    "STORED_CLAIM",
    "FactRank",
    "OfferedFact",
    "best_reliability",
    "fact_rank",
    "first_naming",
    "sentence_claim_ids",
    "shown_sentence",
    "term_marker",
]

PIECE_FIRST = 0
STORED_CLAIM = 1

FactRank = tuple[int, int, int, int, str, str]


@dataclass(frozen=True)
class OfferedFact:
    sentence: ExplainerSentence
    rank: FactRank
    facet: str | None = None
    concept_id: uuid.UUID | None = None
    piece_id: uuid.UUID | None = None

    @property
    def claim_ids(self) -> frozenset[str]:
        return sentence_claim_ids(self.sentence)


def sentence_claim_ids(sentence: AnswerSentence) -> frozenset[str]:
    return frozenset(citation.claim_id for citation in sentence.citations)


def best_reliability(sentence: AnswerSentence, sources: Mapping[str, SourceRef]) -> int:
    tiers = [
        RELIABILITIES.index(source.reliability)
        for source in (sources.get(c.source_id) for c in sentence.citations)
        if source is not None and source.reliability is not None
    ]
    return min(tiers, default=len(RELIABILITIES))


def fact_rank(
    sentence: AnswerSentence, sources: Mapping[str, SourceRef], *, origin: int = STORED_CLAIM
) -> FactRank:
    return (
        origin,
        LEVEL_ORDER.get(sentence.level, len(LEVEL_ORDER)),
        best_reliability(sentence, sources),
        -len({citation.source_id for citation in sentence.citations}),
        sentence.text.casefold(),
        sentence.id,
    )


def first_naming(
    facts: Iterable[OfferedFact], label: str, *, avoiding: frozenset[str] = frozenset()
) -> OfferedFact | None:
    for fact in sorted(facts, key=lambda offered: offered.rank):
        if fact.claim_ids & avoiding:
            continue
        if named_in(label, fact.sentence):
            return fact
    return None


def term_marker(key: str, surfaces: Sequence[str]) -> TermMarker:
    return TermMarker([GlossaryEntry(key=key, surfaces=tuple(surfaces))])


def shown_sentence(
    fact: OfferedFact, sentence_id: str, marker: TermMarker | None = None
) -> ExplainerSentence:
    spans = marker.spans(fact.sentence.text) if marker is not None else []
    return fact.sentence.model_copy(update={"id": sentence_id, "terms": spans})
