from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping, Sequence
from types import MappingProxyType

from app.research.blocks_play import SimulationBlock
from app.research.citations import Citation
from app.research.piece_reuse import ClaimState
from app.research.simulation_draft import (
    REACTION_REF_PREFIX,
    STATEMENT_REF_PREFIX,
    Grounding,
    OfferedReaction,
    OfferedStatement,
)
from app.science.mechanisms import Concept, simulation_reaction
from app.science.process_view import craft_process
from app.science.records import KnownClaim, ProcessRecords

from .knowledge_view import ClaimView
from .piece_lookup import view_states

__all__ = [
    "EXPLAINERS_PER_ANSWER",
    "STATEMENTS_MAX",
    "AnswerConcepts",
    "concept_states",
    "explainer_limit",
    "grounded_claim_ids",
    "grounding_for",
    "reactions_hold",
]

STATEMENTS_MAX = 16
EXPLAINERS_PER_ANSWER: Mapping[str, int] = MappingProxyType({"BASIC": 1, "DETAILED": 2, "EXPERT": 3})


class AnswerConcepts:
    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._built: set[str] = set()
        self._pictured: set[str] = set()

    def take(self, key: str) -> bool:
        if key in self._built or key in self._pictured or len(self._built) >= self._limit:
            return False
        self._built.add(key)
        return True

    def give_back(self, key: str) -> None:
        self._built.discard(key)

    def picture(self, key: str) -> bool:
        if key in self._built or key in self._pictured:
            return False
        self._pictured.add(key)
        return True


def explainer_limit(depth: str | None) -> int:
    return EXPLAINERS_PER_ANSWER.get(depth or "EXPERT", 0)


def grounding_for(facts: Sequence[KnownClaim], concept: Concept | None) -> Grounding:
    known = [(claim.id, claim.text, tuple(claim.citations)) for claim in concept.claims] if concept else []
    known += [(fact.id, fact.text, tuple(fact.citations)) for fact in facts]
    unique: dict[uuid.UUID, tuple[str, tuple[Citation, ...]]] = {}
    for claim_id, text, cites in known:
        unique.setdefault(claim_id, (text, cites))
    statements = tuple(
        OfferedStatement(f"{STATEMENT_REF_PREFIX}{n}", text, cites)
        for n, (text, cites) in enumerate(list(unique.values())[:STATEMENTS_MAX], 1)
    )
    reactions = tuple(
        OfferedReaction(f"{REACTION_REF_PREFIX}{n}", simulation_reaction(view))
        for n, view in enumerate(concept.reactions if concept else (), 1)
    )
    return Grounding(statements=statements, reactions=reactions)


def grounded_claim_ids(grounding: Grounding) -> set[uuid.UUID]:
    cited = [c for s in grounding.statements for c in s.citations]
    cited += [c for r in grounding.reactions for c in r.reaction.citations]
    return {uuid.UUID(citation.claim_id) for citation in cited}


def concept_states(views: Iterable[ClaimView], concept: Concept | None) -> dict[uuid.UUID, ClaimState]:
    states = view_states(views)
    for claim in concept.claims if concept else ():
        states.setdefault(claim.id, ClaimState(claim.level, frozenset(c.id for c in claim.citations)))
    return states


def reactions_hold(block: SimulationBlock, records: ProcessRecords | None) -> bool:
    if not block.reactions:
        return True
    if records is None:
        return False
    stored = {
        view.id: simulation_reaction(view)
        for process in craft_process(records).processes
        for stage in process.stages
        for view in stage.reactions
    }
    return all(stored.get(reaction.reaction_id) == reaction for reaction in block.reactions)
