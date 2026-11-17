from __future__ import annotations

import uuid
from collections.abc import Collection, Iterable

from app.research.blocks_matter import ReactionPlayerBlock, ReactionStep
from app.research.citations import Citation
from app.schemas.science import CitedClaim, ReactionView

from .process_view import craft_process
from .records import ProcessRecords

__all__ = ["REACTION_STEPS_MAX", "reaction_player", "reaction_player_problems"]

REACTION_STEPS_MAX = 8

Played = tuple[uuid.UUID, ReactionView]


def reaction_player(
    records: ProcessRecords, *, block_id: str, cited_claim_ids: Collection[str] = ()
) -> ReactionPlayerBlock | None:
    played = _chosen(_played(records), cited_claim_ids)
    if not played:
        return None
    return ReactionPlayerBlock(
        id=block_id,
        kind="reaction_player",
        version=1,
        reuse=None,
        steps=[_step(stage_id, view) for stage_id, view in played],
    )


def reaction_player_problems(block: ReactionPlayerBlock, records: ProcessRecords) -> list[str]:
    stored = {view.id: (stage_id, view) for stage_id, view in _played(records)}
    problems: list[str] = []
    for step in block.steps:
        found = stored.get(step.reaction_id)
        if found is None:
            problems.append(f"reaction {step.reaction_id} is not a stored reaction of {records.craft.slug}")
            continue
        row = _step(*found)
        if _shown(step) != _shown(row):
            problems.append(f"reaction {step.reaction_id} does not match its stored row")
        linked = {citation.id for citation in row.citations}
        if any(citation.id not in linked for citation in step.citations):
            problems.append(f"reaction {step.reaction_id} cites a passage that is not linked to it")
    return problems


def _played(records: ProcessRecords) -> list[Played]:
    return [
        (stage.id, reaction)
        for process in craft_process(records).processes
        for stage in process.stages
        for reaction in stage.reactions
    ]


def _chosen(played: list[Played], cited_claim_ids: Collection[str]) -> list[Played]:
    if len(played) <= REACTION_STEPS_MAX:
        return played

    def unrelated(position: int) -> bool:
        return not any(str(claim.id) in cited_claim_ids for claim in played[position][1].claims)

    kept = sorted(range(len(played)), key=lambda position: (unrelated(position), position))
    return [played[position] for position in sorted(kept[:REACTION_STEPS_MAX])]


def _step(stage_id: uuid.UUID, view: ReactionView) -> ReactionStep:
    return ReactionStep(
        reaction_id=view.id,
        stage_id=stage_id,
        kind=view.kind,
        label=view.label,
        species=list(view.species),
        equation=view.equation,
        balanced=view.balanced,
        level=view.level,
        citations=_citations(view.claims),
    )


def _citations(claims: Iterable[CitedClaim]) -> list[Citation]:
    seen: dict[str, Citation] = {}
    for claim in claims:
        for citation in claim.citations:
            seen.setdefault(citation.id, citation)
    return list(seen.values())


def _shown(step: ReactionStep) -> tuple[object, ...]:
    return (step.stage_id, step.kind, step.label, step.species, step.equation, step.balanced)
