from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from app.research.explainer_versions import IMAGES_KIND

from .section_blocks import KeptSentence

__all__ = ["LADDER_KIND", "NEW_SECTION", "Deepening"]

LADDER_KIND = "process_ladder"


@dataclass(frozen=True)
class Deepening:
    first_block: int = 1
    kinds: frozenset[str] = frozenset()
    claims: frozenset[uuid.UUID] = frozenset()

    def number(self, ordinal: int) -> int:
        return self.first_block + ordinal - 1

    def shows(self, kind: str) -> bool:
        return kind in self.kinds

    @property
    def adds_pictures(self) -> bool:
        return not self.shows(IMAGES_KIND)

    def unshown(self, sentences: Sequence[KeptSentence]) -> list[KeptSentence]:
        return [sentence for sentence in sentences if not self._shown(sentence)]

    def _shown(self, sentence: KeptSentence) -> bool:
        claims = set(sentence.claim_ids)
        return not sentence.open_question and bool(claims) and claims <= self.claims


NEW_SECTION = Deepening()
