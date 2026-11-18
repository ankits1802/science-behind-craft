from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence

from app.research.blocks import ImagesBlock
from app.science.mechanisms import Concept

from .builder_interface import BuildAsk
from .simulation_grounding import AnswerConcepts

__all__ = ["CONCEPT_PICTURES_PER_SECTION", "CONCEPT_PICTURE_SECONDS", "ConceptPictures", "PictureSearch"]

logger = logging.getLogger(__name__)

CONCEPT_PICTURES_PER_SECTION = 3
CONCEPT_PICTURE_SECONDS = 8.0

PictureSearch = Callable[[BuildAsk, Concept, str], Awaitable[ImagesBlock | None]]


class ConceptPictures:
    def __init__(self, search: PictureSearch) -> None:
        self._search = search

    async def found(
        self, ask: BuildAsk, concepts: Sequence[Concept], answer: AnswerConcepts
    ) -> list[ImagesBlock]:
        wanted: list[Concept] = []
        for concept in concepts:
            if len(wanted) == CONCEPT_PICTURES_PER_SECTION:
                break
            if concept.shown_claim_ids and answer.picture(concept.key):
                wanted.append(concept)
        searched = await asyncio.gather(
            *(
                self._bounded(ask, concept, f"{ask.section.id}.concept{n}")
                for n, concept in enumerate(wanted, 1)
            )
        )
        return [block for block in searched if block is not None]

    async def _bounded(self, ask: BuildAsk, concept: Concept, block_id: str) -> ImagesBlock | None:
        try:
            async with asyncio.timeout(CONCEPT_PICTURE_SECONDS):
                return await self._search(ask, concept, block_id)
        except TimeoutError:
            logger.warning("the picture for concept %s took over %s s", concept.key, CONCEPT_PICTURE_SECONDS)
        except Exception:
            logger.warning("the picture for concept %s failed", concept.key, exc_info=True)
        return None
