import uuid

import pytest

from app.research.blocks import ReuseMarker
from app.services.piece_lookup import PieceLookup
from app.services.piece_store import BuiltSection, kept_pieces, piece_id

from .fixtures import STORED_AT, build_ask, golden_block

ANSWER = uuid.UUID("3b9f1e2d-6c7a-4d8b-9e0f-1a2b3c4d5e6f")
CRAFT_ID = uuid.UUID("54081f83-8396-5a46-a3bc-a467984eebc2")
CRAFT_LOOKUP = PieceLookup(
    craft_id=CRAFT_ID, topics={"GEOGRAPHY": "water:kachchh"}, craft_slug="Kutch-Ajrakh"
)
SIMULATION_SLOT = (None, "GEOGRAPHY", "concept:falling-water-table", "EXPERT")
SIMULATION_ID = "s1.b2"
KEPT_SIMULATION = (piece_id(ANSWER, SIMULATION_ID), "simulation", *SIMULATION_SLOT)


def section(*, deepened: bool = False) -> BuiltSection:
    prose = build_ask().blocks[0]
    return BuiltSection("GEOGRAPHY", (prose, golden_block(id=SIMULATION_ID)), deepened=deepened)


def slots(lookup: PieceLookup, built: BuiltSection) -> list[tuple[object, ...]]:
    kept = kept_pieces(lookup, answer_id=ANSWER, depth="EXPERT", sections=[built])
    return [
        (piece.id, piece.kind, piece.craft_id, piece.facet, piece.topic_key, piece.depth) for piece in kept
    ]


def test_a_section_of_a_craft_keeps_its_own_pieces_and_its_generated_explainer() -> None:
    assert slots(CRAFT_LOOKUP, section()) == [
        (piece_id(ANSWER, "s1.b1"), "prose", CRAFT_ID, "GEOGRAPHY", "water:kachchh", "EXPERT"),
        KEPT_SIMULATION,
    ]


@pytest.mark.parametrize(
    "lookup",
    [PieceLookup(), PieceLookup(craft_id=CRAFT_ID, topics={"HISTORY": "history:kutch-ajrakh"})],
    ids=["any craft", "a facet with no topic"],
)
def test_without_a_section_slot_only_the_cross_craft_generated_explainer_is_kept(lookup: PieceLookup) -> None:
    assert slots(lookup, section()) == [KEPT_SIMULATION]


def test_a_deepened_follow_up_section_keeps_only_its_generated_explainer() -> None:
    assert slots(CRAFT_LOOKUP, section(deepened=True)) == [KEPT_SIMULATION]


def test_a_placed_explainer_is_never_kept_again() -> None:
    marker = ReuseMarker(piece_id=uuid.uuid4(), stored_at=STORED_AT)
    placed = BuiltSection("GEOGRAPHY", (golden_block().model_copy(update={"reuse": marker}),))
    assert kept_pieces(PieceLookup(), answer_id=ANSWER, depth="EXPERT", sections=[placed]) == []
