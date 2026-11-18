from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Iterator
from typing import Any

from app.data.craft_text import fold
from app.research.blocks import BlockBase
from app.research.citations import AnswerSentence
from app.research.explainer import Explainer

RESTATING = ("prose", "material_card", "expert_view")


def blocks_of(explainer: Explainer) -> list[BlockBase]:
    return [block for section in explainer.sections for block in section.blocks]


def rendered_sentences(blocks: Iterable[BlockBase]) -> Iterator[AnswerSentence]:
    paired: set[frozenset[str]] = set()
    for block in blocks:
        if block.kind == "supply_map":
            yield from _grouped_links(block)
        elif block.kind == "expert_view":
            yield from block.take
            yield from _unpaired_views(block, paired)
        else:
            yield from block.cited_sentences()


def _grouped_links(block: Any) -> Iterator[AnswerSentence]:
    grouped: set[tuple[str, str]] = set()
    for link in block.links:
        if (link.material.casefold(), link.sentence.text) not in grouped:
            grouped.add((link.material.casefold(), link.sentence.text))
            yield link.sentence


def _unpaired_views(block: Any, paired: set[frozenset[str]]) -> Iterator[AnswerSentence]:
    for difference in block.differs:
        pair = frozenset({block.seat, difference.seat})
        if pair not in paired:
            paired.add(pair)
            yield from (difference.this_view, difference.other_view)


def repeated_sentences(blocks: Iterable[BlockBase]) -> int:
    counts = Counter(fold(sentence.text) for sentence in rendered_sentences(blocks))
    return sum(count - 1 for count in counts.values())


def claims_of(sentence: AnswerSentence) -> set[str]:
    return {citation.claim_id for citation in sentence.citations}


def restated(blocks: Iterable[BlockBase]) -> list[str]:
    earlier: set[str] = set()
    found = []
    for block in (block for block in blocks if block.kind in RESTATING):
        sentences = list(block.cited_sentences())
        found += [sentence.text for sentence in sentences if claims_of(sentence) <= earlier]
        earlier |= {claim for sentence in sentences for claim in claims_of(sentence)}
    return found
