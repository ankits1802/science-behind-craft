from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable, Collection, Sequence
from datetime import UTC, datetime

from app.composer.simulation import DraftReply, SimulationBrief, draft_simulation, redraft_simulation
from app.core.errors import ExternalFailure, InvalidInput
from app.models.enums import EXPLAINER_DEPTHS
from app.research.blocks_play import SimulationBlock
from app.research.knowledge_pieces import SIMULATION_NAMESPACE, KnowledgePiece, placed_block
from app.research.piece_reuse import SIMULATION_KIND, reusable_simulation
from app.research.simulation_draft import DraftCheck, OfferedValue, checked_draft, offered_values
from app.research.structured import MODEL_SERVICE
from app.research.subject_keys import topic_key

from .builder_evidence import section_facts
from .builder_interface import BuildAsk, BuilderTools, Built
from .piece_lookup import view_states
from .simulation_pieces import simulation_pieces

__all__ = [
    "SIMULATION_WAIT_SECONDS",
    "SimulationBuilder",
    "StoredSimulations",
    "hidden_again",
]

logger = logging.getLogger(__name__)

SIMULATION_WAIT_SECONDS = 60.0
PROBLEMS_LOGGED = 8

StoredSimulations = Callable[[Collection[uuid.UUID], str], Awaitable[list[KnowledgePiece]]]
Clock = Callable[[], datetime]


class SimulationBuilder:
    def __init__(
        self, tools: BuilderTools, *, stored: StoredSimulations | None = None, clock: Clock | None = None
    ) -> None:
        self._tools = tools
        self._stored = stored or self._stored_in_database
        self._clock = clock or (lambda: datetime.now(UTC))

    async def build(self, ask: BuildAsk) -> Built:
        facts = section_facts(ask.blocks, ask.cited)
        offers = offered_values(citation for fact in facts for citation in fact.citations)
        if not offers:
            return Built()
        offered = {fact.id for fact in facts}
        stored = await self._stored(offered, ask.section.discipline)
        reused = reusable_simulation(
            stored,
            facet=ask.section.discipline,
            depth=ask.request.depth or EXPLAINER_DEPTHS[-1],
            offered=offered,
            current=view_states(ask.cited.views.values()),
        )
        if reused is not None:
            return Built((placed_block(reused, _block_id(ask)),))
        hidden = [piece for piece in stored if piece.hidden_at is not None]
        block = await self._built(ask, _brief(ask, [fact.text for fact in facts], offers, hidden), offers)
        if block is None:
            return Built()
        if hidden_again(block, hidden):
            logger.warning("the generated explainer of section %s adds nothing: HIDDEN", ask.section.id)
            return Built()
        return Built((block,))

    async def _built(
        self, ask: BuildAsk, brief: SimulationBrief, offers: Sequence[OfferedValue]
    ) -> SimulationBlock | None:
        reply = await draft_simulation(self._tools.compose_model, brief)
        if not reply.draft.build:
            return None
        check = self._checked(ask, reply, offers)
        if check.block is None:
            logger.info(
                "section %s redrafts its generated explainer: %s", ask.section.id, ",".join(check.rules)
            )
            reply = await redraft_simulation(self._tools.compose_model, brief, reply.draft, check.problems)
            if not reply.draft.build:
                return None
            check = self._checked(ask, reply, offers)
        if check.block is None:
            logger.warning(
                "the generated explainer of section %s adds nothing; rules failed: %s; %s",
                ask.section.id,
                ",".join(check.rules),
                "; ".join(f"{p.rule} {p.detail}" for p in check.problems[:PROBLEMS_LOGGED]),
            )
        return check.block

    def _checked(self, ask: BuildAsk, reply: DraftReply, offers: Sequence[OfferedValue]) -> DraftCheck:
        if reply.model is None:
            raise ExternalFailure("the route that wrote the explainer named no model", service=MODEL_SERVICE)
        return checked_draft(
            reply.draft, offers, block_id=_block_id(ask), model=reply.model, created_at=self._clock()
        )

    async def _stored_in_database(self, claim_ids: Collection[uuid.UUID], facet: str) -> list[KnowledgePiece]:
        async with self._tools.sessions() as session:
            return await simulation_pieces(session, claim_ids, [facet])


def hidden_again(block: SimulationBlock, hidden: Sequence[KnowledgePiece]) -> bool:
    try:
        key = topic_key(SIMULATION_NAMESPACE, block.concept)
    except InvalidInput:
        return False
    claims = sorted({uuid.UUID(claim) for claim in block.cited_claim_ids()})
    return any(piece.topic_key == key and piece.claim_ids == claims for piece in hidden)


def _brief(
    ask: BuildAsk, statements: Sequence[str], offers: Sequence[OfferedValue], hidden: Sequence[KnowledgePiece]
) -> SimulationBrief:
    return SimulationBrief(
        question=ask.request.english_question or ask.request.question,
        craft=ask.request.craft.name if ask.request.craft is not None else None,
        section=ask.section.title,
        discipline=ask.section.discipline,
        shown=tuple(dict.fromkeys(block.kind for block in ask.blocks)),
        statements=tuple(statements),
        offers=tuple(offers),
        hidden=tuple(
            dict.fromkeys(
                piece.payload.concept for piece in hidden if isinstance(piece.payload, SimulationBlock)
            )
        ),
    )


def _block_id(ask: BuildAsk) -> str:
    return f"{ask.section.id}.{SIMULATION_KIND}"
