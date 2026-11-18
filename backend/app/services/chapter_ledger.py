from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from app.research.blocks import DifferReading, ExplainerSentence, ProseBlock
from app.research.citations import AnswerSentence
from app.research.explainer import Block
from app.research.vocabulary import FACT_LEVELS

from .claim_ledger import ClaimLedger
from .ledger_payloads import sentence_keys

__all__ = ["PageLedger"]

CARRIER_ID = "page.shown"


class PageLedger:
    def __init__(self, sources: Mapping[str, Mapping[str, Any]]) -> None:
        self._ledger = ClaimLedger()
        self._sources = sources
        self._texts: dict[str, str] = {}

    def merged_sources(self) -> dict[str, dict[str, Any]]:
        return self._ledger.sources.refs()

    def note(self, sentences: Iterable[AnswerSentence]) -> None:
        shown = list(sentences)
        for sentence in shown:
            for citation in sentence.citations:
                self._ledger.sources.register(citation.source_id, self._sources.get(citation.source_id))
            for key in sentence_keys(sentence.text, sentence.original):
                self._texts.setdefault(key, sentence.id)
        facts = {s.id: s for s in shown if isinstance(s, ExplainerSentence) and s.level in FACT_LEVELS}
        if facts:
            carrier = ProseBlock(
                id=CARRIER_ID, kind="prose", version=1, reuse=None, sentences=list(facts.values())
            )
            self._ledger.admit_lede(carrier, self._sources)

    def blocks(self, chapter: str, blocks: Sequence[Block]) -> list[Block]:
        admitted = self._ledger.admit(chapter, blocks, self._sources)
        for block in admitted:
            for sentence in block.cited_sentences():
                for key in sentence_keys(sentence.text, sentence.original):
                    self._texts.setdefault(key, sentence.id)
        return admitted

    def fresh(self, sentences: Sequence[ExplainerSentence]) -> list[ExplainerSentence]:
        kept = [sentence for sentence in sentences if self.shown_in(sentence) is None]
        self.note(kept)
        return kept

    def shown_in(self, sentence: AnswerSentence) -> str | None:
        for key in sentence_keys(sentence.text, sentence.original):
            if self._texts.get(key, sentence.id) != sentence.id:
                return self._texts[key]
        return None

    def reading(self, reading: DifferReading) -> DifferReading:
        voices = []
        for voice in reading.readings:
            shown = None if voice.sentence is None else self.shown_in(voice.sentence)
            voices.append(
                voice if shown is None else voice.model_copy(update={"sentence": None, "shown_in": shown})
            )
        self.note([voice.sentence for voice in voices if voice.sentence is not None])
        return reading.model_copy(update={"readings": voices})
