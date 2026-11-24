from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from .compose_held import About, Composition, CraftHeld, HeldAfter, HeldStage, composed, refused
from .compose_parts import FIGURE, UnitBook, composed_component, unique_word
from .compose_scene import piece_drawing

__all__ = ["BATH_STAGES", "dip_player"]

BATH_STAGES = frozenset({"SCOUR", "MORDANT", "DYE", "RESIST", "WASH"})
PHASES_MIN = 2
STRIP = "The stages, in order"
DIP_AGAIN = "Dip again"
DIPS_LABEL = "The colour after each stage"
NO_STAGE = "the stage {key}: {slug} holds no stage of its own in a bath under that key"
NO_MATERIAL = "the material {key}: no stage of {slug} in a bath uses it"
NO_AFTER = (
    "the colour after the stage {key} ({name}): propose_structure STAGE_AFTER for {slug} with its colours "
    "and the fact that states them"
)
NO_TOKEN = (
    "a depicted colour recorded with the fact that states the colour after the stage {key} ({name}): ask the "
    "team for its specimen token, since a dip draws a stage only in the colour its fact states"
)
TOO_FEW = (
    "two stages of {name} in a bath, each with its colour after and that colour recorded as a depicted "
    "material: {slug} holds {count}"
)


@dataclass(frozen=True)
class _Phase:
    stage: HeldStage
    after: HeldAfter
    token: str
    claims: tuple[uuid.UUID, ...]


def dip_player(craft: CraftHeld, about: About) -> Composition:
    stages, problem = _bath_stages(craft, about)
    if problem is not None:
        return refused(problem)
    phases, gaps = _phases(craft, stages)
    if len(phases) < PHASES_MIN:
        return refused(TOO_FEW.format(name=craft.name, slug=craft.slug, count=len(phases)), *gaps)
    book = UnitBook()
    return composed(composed_component(craft, _piece(craft, phases, book), book), left_out=gaps)


def _bath_stages(craft: CraftHeld, about: About) -> tuple[list[HeldStage], str | None]:
    stages = [stage for stage in craft.stages if stage.stage_type in BATH_STAGES]
    if about.material is not None:
        stages = [stage for stage in stages if about.material in stage.material_keys]
        if not stages:
            return [], NO_MATERIAL.format(key=about.material, slug=craft.slug)
    if about.stage is not None:
        keys = [stage.key for stage in stages]
        if about.stage not in keys:
            return [], NO_STAGE.format(key=about.stage, slug=craft.slug)
        stages = stages[: keys.index(about.stage) + 1]
    return stages, None


def _phases(craft: CraftHeld, stages: Sequence[HeldStage]) -> tuple[list[_Phase], list[str]]:
    phases: list[_Phase] = []
    gaps: list[str] = []
    for stage in stages:
        after = stage.after
        if after is None or not craft.stated([after.claim_id]):
            gaps.append(NO_AFTER.format(key=stage.key, name=stage.name, slug=craft.slug))
            continue
        if not after.tokens:
            gaps.append(NO_TOKEN.format(key=stage.key, name=stage.name))
            continue
        phases.append(_Phase(stage, after, after.tokens[0], craft.stated([after.claim_id, *stage.claim_ids])))
    return phases, gaps


def _piece(craft: CraftHeld, phases: Sequence[_Phase], book: UnitBook) -> dict[str, Any]:
    last = phases[-1]
    title = f"The colour of {craft.name} after each stage"
    poses: list[str] = []
    strip = [_phase(phase, book, poses) for phase in phases]
    spec = {
        "id": f"dip-{craft.label_root()}",
        "head": {"figure": None, "number": book.label(FIGURE), "title": book.label(title, _claims(phases))},
        "phase": book.label(last.stage.name, last.claims),
        "scene": piece_drawing(last.token),
        "stripLabel": STRIP,
        "phases": strip,
        "dipAgain": DIP_AGAIN,
        "status": book.label(last.stage.name, last.claims),
        "dipsLabel": book.label(DIPS_LABEL),
        "dips": list(dict.fromkeys(phase.token for phase in phases)),
    }
    return {
        "name": "colour-after-each-stage",
        "kind": "dip_player",
        "title": title,
        "description": (
            f"Plays the stages of {craft.name} in a bath one after another, each drawn in the depicted colour "
            f"recorded with the fact that states its colour after, and cited by that fact. Place it in the "
            f"chemistry chapter of the page of {craft.name}."
        ),
        "spec": spec,
    }


def _phase(phase: _Phase, book: UnitBook, poses: list[str]) -> dict[str, Any]:
    pose = unique_word(phase.stage.name, poses)
    poses.append(pose)
    return {
        "pose": pose,
        "drawing": piece_drawing(phase.token),
        "kicker": book.label(phase.stage.name, phase.claims),
        "text": book.cited(phase.after.text, [phase.after.claim_id]),
    }


def _claims(phases: Sequence[_Phase]) -> tuple[uuid.UUID, ...]:
    return tuple(dict.fromkeys(phase.after.claim_id for phase in phases))
