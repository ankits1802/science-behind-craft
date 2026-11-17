from __future__ import annotations

import itertools
import logging
from collections.abc import Mapping, Sequence

from pydantic import ValidationError

from app.composer.what_if import WhatIfChoice
from app.research.blocks_play import WHAT_IF_OUTCOMES_MAX, WhatIfBlock, WhatIfOption, WhatIfOutcome
from app.research.quotes import content_stems

from .builder_evidence import fact_sentence
from .what_if_offers import OfferedInput, OfferedOption, OfferedOutcome, input_words

__all__ = ["CHANGED_MAX_CHARS", "two_inputs_changed", "what_if_block"]

logger = logging.getLogger(__name__)

CHANGED_MAX_CHARS = 80

Shown = tuple[OfferedOption, tuple[OfferedOutcome, ...]]


def what_if_block(
    choice: WhatIfChoice, inputs: Sequence[OfferedInput], *, block_id: str
) -> WhatIfBlock | None:
    chosen = next((offered for offered in inputs if offered.ref == choice.input), None)
    if chosen is None:
        logger.info("the what-if %s changes no offered input", block_id)
        return None
    if two_inputs_changed(choice, inputs):
        logger.warning("the what-if %s is refused: it changes two inputs at once", block_id)
        return None
    picked: dict[str, list[str]] = {}
    for option in choice.options:
        picked.setdefault(option.option, option.outcomes)
    shown = [found for option in chosen.options if (found := _shown(option, picked)) is not None]
    changed = " ".join(choice.changed.split())
    problem = _problem(changed, shown, chosen)
    if problem is not None:
        logger.info("the what-if %s adds nothing: %s", block_id, problem)
        return None
    return _block(block_id, changed, chosen, shown)


def two_inputs_changed(choice: WhatIfChoice, inputs: Sequence[OfferedInput]) -> bool:
    owners = {option.ref: offered.ref for offered in inputs for option in offered.options}
    changed = {choice.input, *(owners[o.option] for o in choice.options if o.option in owners)}
    return len(changed) > 1


def _shown(option: OfferedOption, picked: Mapping[str, Sequence[str]]) -> Shown | None:
    if not option.outcomes:
        return option, ()
    refs = picked.get(option.ref)
    if refs is None:
        return None
    offered = {outcome.ref: outcome for outcome in option.outcomes}
    dropped = [ref for ref in refs if ref not in offered]
    if dropped:
        logger.info("option %s drops %s: no stored claim of it", option.ref, ", ".join(dropped))
    kept = [offered[ref] for ref in dict.fromkeys(refs) if ref in offered][:WHAT_IF_OUTCOMES_MAX]
    return (option, tuple(kept)) if kept else None


def _problem(changed: str, shown: Sequence[Shown], chosen: OfferedInput) -> str | None:
    if len(shown) < 2:
        return "fewer than two options are left"
    if not any(outcomes for _, outcomes in shown):
        return "no option is left with a cited outcome"
    if not changed or len(changed) > CHANGED_MAX_CHARS:
        return f"the input is named in no words or over {CHANGED_MAX_CHARS} characters"
    if not content_stems(changed) <= content_stems(" ".join(input_words(chosen))):
        return f"the input is named with words its stage, options and statements do not use: {changed!r}"
    return None


def _block(block_id: str, changed: str, chosen: OfferedInput, shown: Sequence[Shown]) -> WhatIfBlock | None:
    numbers = itertools.count(1)
    try:
        return WhatIfBlock(
            id=block_id,
            kind="what_if",
            version=1,
            reuse=None,
            changed=changed,
            stage_id=chosen.stage.id,
            options=[
                WhatIfOption(
                    label=option.material.name,
                    material_id=option.material.material_id,
                    term_key=None,
                    outcomes=[
                        WhatIfOutcome(
                            sentence=fact_sentence(outcome.claim, f"{block_id}.{next(numbers)}"),
                            reaction_id=outcome.reaction_id,
                        )
                        for outcome in outcomes
                    ],
                )
                for option, outcomes in shown
            ],
        )
    except ValidationError as refused:
        logger.warning("the what-if %s is refused: %s", block_id, refused)
        return None
