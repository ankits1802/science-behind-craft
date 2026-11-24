from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from app.research.colours import states_colour

from .compose_held import About, Composition, CraftHeld, HeldAfter, HeldStage, composed, refused
from .compose_kit import after_token, stage_agent_names, stage_scene
from .compose_parts import FIGURE, UnitBook, composed_component, joined, unique_word

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
NO_COLOUR = (
    "the colours after the stage {key} ({name}): its after names none, so the dip leaves it out; propose "
    "STAGE_AFTER for {slug} again with the colours its fact states, and the stage's dyes, mordants and resists "
    "named by their substance"
)
IN_WORDS = (
    "a specimen colour for {colour} after the stage {key} ({name}): no depicted material shows it from "
    "{agents}, so its phase is drawn as an outline and the colour named in words; ask the team for a specimen "
    "record with the source that states it"
)
NO_PART = (
    "what the stage {key} ({name}) colours, so the kit can draw it: propose_facts for {slug} with a fact naming "
    "the cloth, the shape of the piece or the vessel it is dipped in (a vat, pot, trough or pit)"
)
TOO_FEW = (
    "two stages of {name} in a bath, each with its colour after naming the colours its fact states: "
    "{slug} holds {count}"
)
NONE_DRAWN = (
    "a depicted colour for one stage of {name} at least: no specimen token shows a colour its stages name "
    "from the substances that give it, so the dip has no colour to draw"
)
WHAT_NAMES = "the materials it names"


@dataclass(frozen=True)
class _Phase:
    stage: HeldStage
    after: HeldAfter
    token: str | None
    claims: tuple[uuid.UUID, ...]
    scene: dict[str, Any]


def dip_player(craft: CraftHeld, about: About) -> Composition:
    stages, problem = _bath_stages(craft, about)
    if problem is not None:
        return refused(problem)
    book = UnitBook()
    phases, gaps = _phases(craft, stages, book)
    if len(phases) < PHASES_MIN:
        return refused(TOO_FEW.format(name=craft.name, slug=craft.slug, count=len(phases)), *gaps)
    if all(phase.token is None for phase in phases):
        return refused(NONE_DRAWN.format(name=craft.name), *gaps)
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


def _phases(craft: CraftHeld, stages: Sequence[HeldStage], book: UnitBook) -> tuple[list[_Phase], list[str]]:
    phases: list[_Phase] = []
    gaps: list[str] = []
    for stage in stages:
        after = stage.after
        if after is None or not craft.stated([after.claim_id]):
            gaps.append(NO_AFTER.format(key=stage.key, name=stage.name, slug=craft.slug))
            continue
        if not after.colours:
            gaps.append(NO_COLOUR.format(key=stage.key, name=stage.name, slug=craft.slug))
            continue
        token = after_token(craft, stage, after)
        scene = stage_scene(craft, stage, book)
        if scene is None:
            gaps.append(NO_PART.format(key=stage.key, name=stage.name, slug=craft.slug))
            continue
        if token is None:
            gaps.append(_in_words(craft, stage, after))
        claims = craft.stated([after.claim_id, *stage.claim_ids])
        phases.append(_Phase(stage, after, token, claims, scene))
    return phases, gaps


def _in_words(craft: CraftHeld, stage: HeldStage, after: HeldAfter) -> str:
    agents = list(stage_agent_names(craft, stage))
    return IN_WORDS.format(
        colour=joined([colour.lower() for colour in after.colours]),
        key=stage.key,
        name=stage.name,
        agents=joined(agents) if agents else WHAT_NAMES,
    )


def _piece(craft: CraftHeld, phases: Sequence[_Phase], book: UnitBook) -> dict[str, Any]:
    last = phases[-1]
    title = f"The colour of {craft.name} after each stage"
    poses: list[str] = []
    strip = [_phase(phase, book, poses) for phase in phases]
    spec = {
        "id": f"dip-{craft.label_root()}",
        "head": {"figure": None, "number": book.label(FIGURE), "title": book.label(title, _claims(phases))},
        "phase": book.label(last.stage.name, last.claims),
        "scene": stage_scene(craft, last.stage, book),
        "stripLabel": STRIP,
        "phases": strip,
        "dipAgain": DIP_AGAIN,
        "status": book.label(last.stage.name, last.claims),
        "dipsLabel": book.label(DIPS_LABEL),
        "dips": list(dict.fromkeys(phase.token for phase in phases if phase.token is not None)),
    }
    return {
        "name": "colour-after-each-stage",
        "kind": "dip_player",
        "title": title,
        "description": (
            f"Plays the stages of {craft.name} in a bath one after another, each drawn from the figure kit's parts "
            f"its facts name in the depicted colour of the dye, mordant or resist that gives the colour its fact "
            f"states, or in line work with that colour named where no depicted material shows it, and cited by "
            f"that fact. Place it in the chemistry chapter of the page of {craft.name}."
        ),
        "spec": spec,
    }


def _phase(phase: _Phase, book: UnitBook, poses: list[str]) -> dict[str, Any]:
    pose = unique_word(phase.stage.name, poses)
    poses.append(pose)
    return {
        "pose": pose,
        "drawing": phase.scene,
        "kicker": book.label(phase.stage.name, phase.claims),
        "text": book.cited(_said(phase), [phase.after.claim_id]),
    }


def _said(phase: _Phase) -> str:
    after = phase.after
    if phase.token is not None or any(states_colour(after.text, colour) for colour in after.colours):
        return after.text
    named = joined([colour.lower() for colour in after.colours])
    return f"{named[:1].upper()}{named[1:]}: {after.text}"


def _claims(phases: Sequence[_Phase]) -> tuple[uuid.UUID, ...]:
    return tuple(dict.fromkeys(phase.after.claim_id for phase in phases))
