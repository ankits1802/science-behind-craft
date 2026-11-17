from __future__ import annotations

import uuid
from collections.abc import Mapping

from pydantic import ValidationError

from app.models import Source
from app.research.blocks import ExplainerSentence
from app.research.citations import SourceRef
from app.research.offered_facts import STORED_CLAIM, OfferedFact, fact_rank
from app.research.vocabulary import FACT_LEVELS

from .knowledge_view import ClaimView, source_ref

__all__ = ["OFFERED_SENTENCE_ID", "fact_sentence", "offered_fact", "source_refs"]

OFFERED_SENTENCE_ID = "offered"


def source_refs(sources: Mapping[uuid.UUID, Source]) -> dict[str, SourceRef]:
    return {
        str(source_id): SourceRef.model_validate(source_ref(source)) for source_id, source in sources.items()
    }


def fact_sentence(view: ClaimView) -> ExplainerSentence | None:
    if view.level not in FACT_LEVELS or not view.citations:
        return None
    try:
        return ExplainerSentence.model_validate(
            {
                "id": f"{OFFERED_SENTENCE_ID}.{view.id}",
                "text": view.text,
                "level": view.level,
                "citations": view.citations,
                "translated": False,
                "terms": [],
            }
        )
    except ValidationError:
        return None


def offered_fact(
    view: ClaimView,
    sources: Mapping[str, SourceRef],
    *,
    facet: str | None = None,
    origin: int = STORED_CLAIM,
) -> OfferedFact | None:
    sentence = fact_sentence(view)
    if sentence is None:
        return None
    return OfferedFact(
        sentence=sentence,
        rank=fact_rank(sentence, sources, origin=origin),
        facet=facet,
        concept_id=view.concept_id,
    )
