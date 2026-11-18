from __future__ import annotations

import itertools
import logging
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.research.blocks import ExplainerSentence
from app.research.blocks_lede import LedeBlock
from app.research.blocks_signature import SignatureBlock, chosen_signature
from app.research.crafts import CraftRef
from app.research.explainer import with_payload_sentences
from app.research.vocabulary import FACT_LEVELS, LEVEL_ORDER
from app.science.records import CompoundRecord

from .answer_events import CitedClaims
from .craft_matter import craft_matter
from .knowledge_view import ClaimView
from .section_enrichment import Enrichment
from .signature_rules import FigureEvidence, figure_fields

__all__ = [
    "FIGURE_BLOCK_ID",
    "CompoundsOf",
    "CraftCompounds",
    "FiguredLede",
    "SignatureFigures",
    "craft_compounds",
    "ranked_facts",
    "signature_block",
    "signature_figures",
]

logger = logging.getLogger(__name__)

FIGURE_BLOCK_ID = "lede.figure"
COMPOUND_KINDS = frozenset({"indigo_vat"})
FIGURE = TypeAdapter(SignatureBlock)


@dataclass(frozen=True)
class CraftCompounds:
    compounds: tuple[CompoundRecord, ...] = ()
    sources: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)


CompoundsOf = Callable[[CraftRef], Awaitable[CraftCompounds]]


@dataclass(frozen=True)
class FiguredLede:
    lede: LedeBlock
    sources: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class SignatureFigures:
    compounds: CompoundsOf

    async def figured(
        self,
        lede: LedeBlock,
        *,
        question: str,
        craft: CraftRef | None,
        evidence: CitedClaims,
        enrichment: Enrichment,
    ) -> FiguredLede:
        try:
            return await self._figured(lede, question, craft, evidence, enrichment)
        except Exception:
            logger.warning("the lede's figure was not built; the lede is sent without one", exc_info=True)
            return FiguredLede(lede)

    async def _figured(
        self,
        lede: LedeBlock,
        question: str,
        craft: CraftRef | None,
        evidence: CitedClaims,
        enrichment: Enrichment,
    ) -> FiguredLede:
        keys = [span.term_key for span in enrichment.marker.spans(question)]
        keys += [span.term_key for sentence in lede.sentences for span in sentence.terms]
        kind = chosen_signature(list(dict.fromkeys(keys)))
        if kind is None or craft is None:
            return FiguredLede(lede)
        found = await self.compounds(craft) if kind in COMPOUND_KINDS else CraftCompounds()
        facts = FigureEvidence(ranked_facts(evidence), found.compounds, found.sources)
        figure = signature_block(kind, facts)
        if figure is None:
            return FiguredLede(lede)
        payload = lede.model_dump(mode="json", by_alias=True)
        shown = enrichment.marked(LedeBlock.model_validate(payload | {"figure": _plain(figure)}))
        known = {**evidence.sources, **found.sources}
        return FiguredLede(shown, {sid: known[sid] for sid in figure.cited_source_ids() if sid in known})


def signature_block(
    kind: str, evidence: FigureEvidence, *, block_id: str = FIGURE_BLOCK_ID
) -> SignatureBlock | None:
    fields = figure_fields(kind, evidence)
    if fields is None:
        return None
    counter = itertools.count(1)
    payload = {"id": block_id, "kind": kind, "version": 1, "reuse": None, **_plain(fields)}
    numbered = with_payload_sentences(
        payload, lambda sentence: {**sentence, "id": f"{block_id}.{next(counter)}"}
    )
    try:
        return FIGURE.validate_python(numbered)
    except ValidationError as refused:
        logger.warning("the %s figure is refused: %s", kind, refused.errors()[0]["msg"])
        return None


def ranked_facts(evidence: CitedClaims) -> tuple[ExplainerSentence, ...]:
    views = sorted(evidence.views.values(), key=lambda view: (-view.rank, LEVEL_ORDER.get(view.level, 9)))
    facts = (_fact(f"fact.{number}", view) for number, view in enumerate(views, start=1))
    return tuple(fact for fact in facts if fact is not None)


def craft_compounds(sessions: async_sessionmaker[AsyncSession]) -> CompoundsOf:
    async def compounds(craft: CraftRef) -> CraftCompounds:
        matter = await craft_matter(sessions, craft)
        if matter is None:
            return CraftCompounds()
        return CraftCompounds(tuple(matter.compounds.values()), dict(matter.record_sources))

    return compounds


def signature_figures(sessions: async_sessionmaker[AsyncSession]) -> SignatureFigures | None:
    if not get_settings().signature_figures_enabled:
        return None
    return SignatureFigures(compounds=craft_compounds(sessions))


def _fact(sentence_id: str, view: ClaimView) -> ExplainerSentence | None:
    if view.level not in FACT_LEVELS or not view.citations:
        return None
    try:
        return ExplainerSentence.model_validate(
            {
                "id": sentence_id,
                "text": view.text,
                "level": view.level,
                "citations": view.citations,
                "terms": [],
            }
        )
    except ValidationError:
        logger.info(
            "claim %s is not offered to a figure: its citations are off the sentence contract", view.id
        )
        return None


def _plain(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(item) for item in value]
    return value
