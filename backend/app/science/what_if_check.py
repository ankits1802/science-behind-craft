from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence

from app.research.blocks_play import WhatIfBlock, WhatIfOption, WhatIfOutcome

from .records import CompoundRecord, MaterialRecord, ProcessRecords, ReactionRecord

__all__ = ["what_if_problems"]


def what_if_problems(block: WhatIfBlock, records: ProcessRecords) -> list[str]:
    craft = records.craft.slug
    problems: list[str] = []
    if block.stage_id is not None and block.stage_id not in {stage.id for stage in records.stages}:
        problems.append(
            f"what if {block.id} changes an input of stage {block.stage_id}, not a stage of {craft}"
        )
    uses: dict[uuid.UUID, list[MaterialRecord]] = {}
    for use in records.materials:
        if use.material_id is not None:
            uses.setdefault(use.material_id, []).append(use)
    reactions = {reaction.id: reaction for reaction in records.reactions}
    for option in block.options:
        problems += _option_problems(block, option, uses, reactions, craft=craft)
    return problems


def _option_problems(
    block: WhatIfBlock,
    option: WhatIfOption,
    uses: Mapping[uuid.UUID, Sequence[MaterialRecord]],
    reactions: Mapping[uuid.UUID, ReactionRecord],
    *,
    craft: str,
) -> list[str]:
    if option.term_key is not None:
        return [f"option {option.label!r} is a glossary term, which the stored rows cannot re-check"]
    if option.material_id is None:
        return []
    found = uses.get(option.material_id)
    if not found:
        return [f"option {option.label!r} is not a stored material of {craft}"]
    problems: list[str] = []
    if option.label != found[0].name:
        problems.append(f"option {option.label!r} does not match its stored material {found[0].name!r}")
    if block.stage_id is not None and all(use.stage_id != block.stage_id for use in found):
        problems.append(f"option {option.label!r} is not used at the stage the what-if changes")
    compound = found[0].compound
    for outcome in option.outcomes:
        if outcome.reaction_id is not None:
            problems += _reaction_problems(option, outcome, reactions.get(outcome.reaction_id), compound)
    return problems


def _reaction_problems(
    option: WhatIfOption,
    outcome: WhatIfOutcome,
    reaction: ReactionRecord | None,
    compound: CompoundRecord | None,
) -> list[str]:
    if reaction is None:
        return [f"option {option.label!r} rests on reaction {outcome.reaction_id}, which is not stored"]
    if compound is None or compound.id not in {species.compound_id for species in reaction.species}:
        return [f"reaction {reaction.id} holds no compound of option {option.label!r}"]
    linked = {citation_id for _, citation_id in reaction.citations}
    if not any(citation.id in linked for citation in outcome.sentence.citations):
        return [f"an outcome of option {option.label!r} cites no passage linked to reaction {reaction.id}"]
    return []
