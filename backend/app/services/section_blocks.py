from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from app.core.errors import InvalidInput
from app.research.blocks import ExplainerSentence, ProseBlock
from app.research.blocks_lede import LEDE_BLOCK_ID, LedeBlock
from app.research.composition import LEDE_SENTENCES_MAX, LEDE_SENTENCES_MIN, ComposedAnswer
from app.research.planning import OPEN_QUESTION_LEVEL
from app.research.quotes import unsupported_figures
from app.research.vocabulary import FACT_LEVELS, weakest_level

from .answer_events import CitedClaims
from .knowledge_view import ClaimView
from .stated_names import unstated_names
from .write_back_plan import composed_sentences

__all__ = [
    "BlockRefused",
    "KeptSentence",
    "SectionSentences",
    "cited_sentence",
    "kept_sentences",
    "lede_block",
    "prose_block",
    "prose_problems",
    "section_sentences",
]

logger = logging.getLogger(__name__)


class BlockRefused(InvalidInput):
    def __init__(self, block_id: str, problems: Sequence[str]) -> None:
        super().__init__(f"block {block_id} is refused: {'; '.join(problems)}")
        self.block_id = block_id
        self.problems = tuple(problems)


@dataclass(frozen=True)
class KeptSentence:
    text: str
    claim_ids: tuple[uuid.UUID, ...]
    evidence_ids: tuple[str, ...]
    open_question: bool


@dataclass(frozen=True)
class SectionSentences:
    facts: tuple[KeptSentence, ...]
    open_questions: tuple[KeptSentence, ...]


def kept_sentences(composed: ComposedAnswer, claims_of: Sequence[Sequence[uuid.UUID]]) -> list[KeptSentence]:
    pairs = list(composed_sentences(composed))
    if len(pairs) != len(claims_of):
        raise InvalidInput(f"{len(claims_of)} claim lists were given for {len(pairs)} sentences")
    return [
        KeptSentence(sentence.text, tuple(claim_ids), tuple(sentence.evidence_ids), heading is None)
        for (sentence, heading), claim_ids in zip(pairs, claims_of, strict=True)
    ]


def section_sentences(sentences: Sequence[KeptSentence], cited: CitedClaims) -> SectionSentences:
    facts: list[KeptSentence] = []
    open_questions: list[KeptSentence] = []
    for sentence in sentences:
        views = _views(sentence, cited)
        unstated = unstated_names(sentence.text, _supports(views))
        if unstated:
            logger.warning(
                "dropped a sentence naming %s, which no cited claim or quote states", ", ".join(unstated)
            )
            continue
        level = _level(views)
        if level == OPEN_QUESTION_LEVEL:
            open_questions.append(sentence)
        elif sentence.open_question and level is None:
            logger.warning("dropped an open question with no stored citation")
        else:
            facts.append(sentence)
    return SectionSentences(tuple(facts), tuple(open_questions))


def prose_problems(sentences: Sequence[KeptSentence], cited: CitedClaims) -> list[str]:
    problems: list[str] = []
    for number, sentence in enumerate(sentences, start=1):
        views = _views(sentence, cited)
        citations = _citations(views)
        if not citations:
            problems.append(f"sentence {number} cites no stored claim")
            continue
        if _level(views) not in FACT_LEVELS:
            problems.append(f"sentence {number} is not a fact")
        supports = _supports(views)
        figures = unsupported_figures(sentence.text, supports)
        if figures:
            problems.append(
                f"sentence {number} states {', '.join(figures)}, which no cited claim or quote holds"
            )
        unstated = unstated_names(sentence.text, supports)
        if unstated:
            problems.append(
                f"sentence {number} names {', '.join(unstated)}, which no cited claim or quote states"
            )
    return problems


def prose_block(block_id: str, sentences: Sequence[KeptSentence], cited: CitedClaims) -> ProseBlock:
    problems = prose_problems(sentences, cited) if sentences else ["the block has no sentence"]
    if problems:
        raise BlockRefused(block_id, problems)
    return ProseBlock(
        id=block_id,
        kind="prose",
        version=1,
        reuse=None,
        sentences=[
            ExplainerSentence.model_validate(
                cited_sentence(f"{block_id}.{n}", sentence, cited) | {"terms": []}
            )
            for n, sentence in enumerate(sentences, start=1)
        ],
    )


def lede_block(question: str, sentences: Sequence[KeptSentence], cited: CitedClaims) -> LedeBlock:
    kept: list[KeptSentence] = []
    for sentence in sentences:
        problems = prose_problems([sentence], cited)
        if problems:
            logger.warning("dropped a lede sentence: %s", "; ".join(problems))
        else:
            kept.append(sentence)
    if len(kept) < LEDE_SENTENCES_MIN:
        raise BlockRefused(LEDE_BLOCK_ID, [f"{len(kept)} sentence(s) pass, not {LEDE_SENTENCES_MIN} or more"])
    return LedeBlock(
        id=LEDE_BLOCK_ID,
        kind="lede",
        version=1,
        reuse=None,
        headline=question,
        sentences=[
            ExplainerSentence.model_validate(
                cited_sentence(f"{LEDE_BLOCK_ID}.{n}", sentence, cited) | {"terms": []}
            )
            for n, sentence in enumerate(kept[:LEDE_SENTENCES_MAX], start=1)
        ],
        figure=None,
    )


def cited_sentence(sentence_id: str, sentence: KeptSentence, cited: CitedClaims) -> dict[str, Any]:
    views = _views(sentence, cited)
    return {
        "id": sentence_id,
        "text": sentence.text,
        "level": _level(views),
        "citations": _citations(views),
    }


def _views(sentence: KeptSentence, cited: CitedClaims) -> list[ClaimView]:
    return [cited.views[claim_id] for claim_id in sentence.claim_ids if claim_id in cited.views]


def _supports(views: Sequence[ClaimView]) -> list[str]:
    quotes = [citation["quote"] for citation in _citations(views) if citation["quote"]]
    return [*(view.text for view in views), *quotes]


def _level(views: Sequence[ClaimView]) -> str | None:
    return weakest_level(view.level for view in views) if views else None


def _citations(views: Sequence[ClaimView]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for view in views:
        for citation in view.citations:
            seen.setdefault(citation["id"], citation)
    return list(seen.values())
