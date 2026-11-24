from __future__ import annotations

import uuid
from collections.abc import Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, replace

from app.research.blocks import ExplainerSentence, LadderStage, ProcessLadderBlock
from app.research.blocks_matter import MaterialCardBlock
from app.research.blocks_signature import MordantBathBlock
from app.research.citations import Citation
from app.research.colour_key import KEY_COLOURS_MIN, agent_materials, agent_names, depicted_material
from app.research.colours import colour_of, states_colour
from app.research.explainer import Block
from app.research.quotes import quote_key
from app.science.reaction_colours import step_colours

from .document_components import DocumentStructure, StructureBlock
from .knowledge_view import ClaimView

__all__ = ["KeyColour", "KeyFacts", "KeyText", "key_claim_ids", "key_colours", "told_key"]

AFTER, BEFORE = "AFTER", "BEFORE"
HYPOTHESIS = "HYPOTHESIS"
CARD_ROLES = frozenset({"DYE", "MORDANT"})
ENDS = (".", "!", "?")
NAME_SEPARATOR = ", "


@dataclass(frozen=True)
class KeyText:
    text: str
    claim_ids: tuple[uuid.UUID, ...]


@dataclass(frozen=True)
class KeyColour:
    colour: str
    agent: str
    caption: str
    names: tuple[str, ...]
    text: KeyText
    why: KeyText | None = None
    before: str | None = None

    @property
    def dye(self) -> str | None:
        return depicted_material(self.colour, self.names)

    @property
    def before_dye(self) -> str | None:
        return depicted_material(self.before, self.names) if self.dye is not None else None


@dataclass(frozen=True)
class KeyFacts:
    visible: Mapping[uuid.UUID, ClaimView]
    told: Collection[str] = frozenset()

    def shown(self, text: KeyText | None) -> bool:
        if text is None or not text.claim_ids or told_key(text.text) in self.told:
            return False
        return all(
            claim in self.visible and self.visible[claim].level != HYPOTHESIS for claim in text.claim_ids
        )

    def kept(self, colour: KeyColour) -> KeyColour | None:
        if not self.shown(colour.text) or not states_colour(colour.text.text, colour.colour):
            return None
        return colour if colour.why is None or self.shown(colour.why) else replace(colour, why=None)


def told_key(text: str) -> str:
    return quote_key(text).casefold()


def key_colours(structure: DocumentStructure | None, facts: KeyFacts) -> list[KeyColour]:
    kept = [found for colour in _candidates(structure) if (found := facts.kept(colour)) is not None]
    chosen = _chosen(kept)
    return chosen if len(chosen) >= KEY_COLOURS_MIN else []


def key_claim_ids(structure: DocumentStructure | None) -> list[uuid.UUID]:
    found = [
        claim
        for colour in _candidates(structure)
        for text in (colour.text, colour.why)
        if text is not None
        for claim in text.claim_ids
    ]
    return list(dict.fromkeys(found))


def _candidates(structure: DocumentStructure | None) -> list[KeyColour]:
    if structure is None:
        return []
    blocks = [item.block for item in structure.items() if isinstance(item, StructureBlock)]
    return [colour for block in blocks for colour in _block_colours(block)]


def _block_colours(block: Block) -> Iterator[KeyColour]:
    if isinstance(block, ProcessLadderBlock):
        for stage in block.stages:
            yield from _stage_colours(stage)
    elif isinstance(block, MordantBathBlock):
        yield from _mordant_colours(block)
    elif isinstance(block, MaterialCardBlock) and block.role in CARD_ROLES:
        yield from _card_colours(block)


def _stage_colours(stage: LadderStage) -> Iterator[KeyColour]:
    after = stage.after
    if after is None:
        return
    agents = agent_materials(stage.materials)
    names = agent_names(agents)
    text = KeyText(_closed(after.text), _claims(after.citations))
    why = _key_text(stage.why) if stage.why is not None else None
    befores = _changes(after.citations)
    agent = _listed(material.name for material in agents) or stage.name
    for colour in after.colours:
        yield KeyColour(colour, agent, stage.name, names, text, why, befores.get(colour))


def _mordant_colours(bath: MordantBathBlock) -> Iterator[KeyColour]:
    for swatch in bath.swatches:
        colour = colour_of(swatch.colour)
        if colour is None:
            continue
        agent = f"{bath.dye} on {swatch.mordant}" if swatch.mordant else bath.dye
        names = (bath.dye, *((swatch.mordant,) if swatch.mordant else ()))
        yield KeyColour(
            colour, _capital(agent), swatch.mordant or bath.dye, names, _key_text(swatch.sentence)
        )


def _card_colours(card: MaterialCardBlock) -> Iterator[KeyColour]:
    names = (card.name, *card.local_names)
    for fact in card.facts:
        befores = _changes(fact.citations)
        for colour in _afters(fact.citations):
            yield KeyColour(colour, card.name, card.name, names, _key_text(fact), before=befores.get(colour))


def _chosen(found: Sequence[KeyColour]) -> list[KeyColour]:
    picked: dict[str, tuple[int, KeyColour]] = {}
    for at, colour in enumerate(found):
        held = picked.get(colour.colour)
        if held is None or (held[1].dye is None and colour.dye is not None):
            picked[colour.colour] = (at, colour)
    return [colour for _, colour in sorted(picked.values(), key=lambda placed: placed[0])]


def _sides(citation: Citation) -> dict[str, str]:
    return {colour.side: colour.colour for colour in step_colours([citation])}


def _changes(citations: Iterable[Citation]) -> dict[str, str]:
    found: dict[str, str] = {}
    for citation in citations:
        sides = _sides(citation)
        if BEFORE in sides and AFTER in sides and sides[BEFORE] != sides[AFTER]:
            found.setdefault(sides[AFTER], sides[BEFORE])
    return found


def _afters(citations: Iterable[Citation]) -> list[str]:
    found: list[str] = []
    for citation in citations:
        after = _sides(citation).get(AFTER)
        if after is not None and after not in found:
            found.append(after)
    return found


def _key_text(sentence: ExplainerSentence) -> KeyText:
    return KeyText(sentence.text, _claims(sentence.citations))


def _claims(citations: Iterable[Citation]) -> tuple[uuid.UUID, ...]:
    found: list[uuid.UUID] = []
    for citation in citations:
        try:
            found.append(uuid.UUID(citation.claim_id))
        except ValueError:
            return ()
    return tuple(dict.fromkeys(found))


def _closed(text: str) -> str:
    stripped = text.strip()
    return stripped if stripped.endswith(ENDS) else f"{stripped}."


def _listed(names: Iterable[str]) -> str:
    return NAME_SEPARATOR.join(dict.fromkeys(names))


def _capital(text: str) -> str:
    return text[:1].upper() + text[1:]
