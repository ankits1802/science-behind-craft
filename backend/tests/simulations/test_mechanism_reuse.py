import dataclasses
import uuid
from datetime import UTC, datetime
from typing import Any

from app.research.blocks import ReuseMarker
from app.research.blocks_play import SimulationBlock
from app.research.knowledge_pieces import PieceSlot, knowledge_piece, piece_slot
from app.services.builder_interface import BuildAsk

from ..matter.fixtures import matter
from .at_the_bar import IRON_AT_THE_BAR, at_the_bar
from .fixtures import DraftModel, StoredPieces, builder
from .test_mechanism_explainers import IRON_REACTION, iron_ask, mechanism_draft, mechanism_golden

STORED_AT = datetime(2026, 11, 17, 9, 0, tzinfo=UTC)


def reused_iron_ask() -> BuildAsk:
    ask = iron_ask()
    marker = ReuseMarker(piece_id=uuid.UUID(int=5), stored_at=STORED_AT)
    placed = tuple(block.model_copy(update={"reuse": marker}) for block in ask.blocks)
    return dataclasses.replace(ask, blocks=placed)


def stored_mechanism(block: SimulationBlock) -> StoredPieces:
    slot = piece_slot(block, PieceSlot(None, "CHEMISTRY", "chemistry:kutch-ajrakh", "EXPERT"))
    piece = knowledge_piece(block, slot, piece_id=uuid.uuid4(), answer_id=uuid.uuid4(), created_at=STORED_AT)
    return StoredPieces([piece])


async def test_a_reused_section_s_placed_prose_still_finds_its_concept_and_builds() -> None:
    explainer = DraftModel([mechanism_draft()])
    built = await builder(DraftModel([]), matter=matter(), explainer=explainer).build(reused_iron_ask())
    (block,) = built.blocks
    assert [r.reaction_id for r in block.reactions] == [IRON_REACTION]
    assert block.reuse is None


def stored_at_the_bar() -> dict[str, Any]:
    return mechanism_golden()["block"] | at_the_bar(IRON_AT_THE_BAR)


async def test_a_stored_mechanism_explainer_is_reused_while_its_reaction_matches_the_stored_row() -> None:
    golden = SimulationBlock.model_validate(stored_at_the_bar())
    explainer = DraftModel([mechanism_draft()])
    shared = builder(DraftModel([]), stored_mechanism(golden), matter=matter(), explainer=explainer)
    (block,) = (await shared.build(iron_ask())).blocks
    assert block.reuse is not None and explainer.calls == []


async def test_a_stored_explainer_whose_reaction_changed_is_built_again() -> None:
    payload = stored_at_the_bar()
    changed = {**payload, "reactions": [{**payload["reactions"][0], "label": "Iron in vinegar"}]}
    stale = SimulationBlock.model_validate(changed)
    explainer = DraftModel([mechanism_draft()])
    shared = builder(DraftModel([]), stored_mechanism(stale), matter=matter(), explainer=explainer)
    (block,) = (await shared.build(iron_ask())).blocks
    assert block.reuse is None and len(explainer.calls) == 1
    assert block.reactions[0].label == "Scrap iron dissolving into iron acetate"


async def test_a_stored_explainer_drawn_below_the_bar_is_never_reused_and_is_drawn_again_at_the_bar() -> None:
    recorded = SimulationBlock.model_validate(mechanism_golden()["block"])
    explainer = DraftModel([mechanism_draft()])
    shared = builder(DraftModel([]), stored_mechanism(recorded), matter=matter(), explainer=explainer)
    (block,) = (await shared.build(iron_ask())).blocks
    assert block.reuse is None and len(explainer.calls) == 1
    assert block.html == IRON_AT_THE_BAR
