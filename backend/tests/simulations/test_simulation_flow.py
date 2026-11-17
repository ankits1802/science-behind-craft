import dataclasses
from typing import Any

from app.services.block_builders import BLOCK_BUILDERS, BlockBuilders
from app.services.builder_interface import BuilderTools
from app.services.simulation_builder import SimulationBuilder

from ..answering.fakes import SOURCES, VIEWS, WRITTEN_LAKE_ID, pipeline, streamed
from ..answering.piece_fakes import MemoryPieces
from ..answering.test_answer_flow import REPLY, events
from ..answering.test_piece_reuse_flow import asked
from .fixtures import BUILT_AT, DraftModel, StoredPieces

BATH_STATED = ("Mordanting baths of 8 g/L alum were", "were heated to 60 °C")
BATH_HTML = (
    '<p id="bath"></p>\n<script>\nconst data = JSON.parse(document.getElementById("kv-data").textContent);\n'
    'document.getElementById("bath").textContent = data.alumGrams + " g/L of alum at " + data.bathHeat;\n'
    "</script>"
)
BATH_REPLY = {
    "build": True,
    "concept": "Alum mordant bath",
    "title": "What the mordant bath holds",
    "values": [
        {"ref": "v1", "key": "alumGrams", "label": "Alum in the bath", "unit": "g/L"},
        {"ref": "v2", "key": "bathHeat", "label": "Heat of the bath", "unit": "°C"},
    ],
    "html": BATH_HTML,
}


def simulations_only(model: DraftModel) -> BlockBuilders:
    (entry,) = [entry for entry in BLOCK_BUILDERS if entry.kind == "simulation"]
    tools = BuilderTools(sessions=None, live=None, plan_model=None, compose_model=model)
    return BlockBuilders([(entry, SimulationBuilder(tools, stored=StoredPieces(), clock=lambda: BUILT_AT))])


def blocks_of(found: list[tuple[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    return [payload["block"] for name, payload in found if name == "block"]


async def test_an_explainer_built_in_one_answer_is_reused_by_the_next_with_no_model_call() -> None:
    model, pieces = DraftModel([BATH_REPLY]), MemoryPieces(views=list(VIEWS), sources=dict(SOURCES))
    first = dataclasses.replace(pipeline(replies=[REPLY], pieces=pieces), builders=simulations_only(model))
    shown = blocks_of(events(await streamed(asked(), first)))
    assert [(block["id"], block["kind"], block["reuse"]) for block in shown] == [
        ("s1.b1", "prose", None),
        ("s1.b2", "simulation", None),
    ]
    assert [(v["value"], v["stated"]) for v in shown[1]["values"]] == [
        (8.0, BATH_STATED[0]),
        (60.0, BATH_STATED[1]),
    ]
    assert {c["claimId"] for v in shown[1]["values"] for c in v["citations"]} == {str(WRITTEN_LAKE_ID)}
    stored = [piece for piece in pieces.current() if piece.kind == "simulation"]
    assert [(piece.craft_id, piece.topic_key, piece.claim_ids) for piece in stored] == [
        (None, "concept:alum-mordant-bath", [WRITTEN_LAKE_ID])
    ]
    second = dataclasses.replace(pipeline(pieces=pieces), builders=simulations_only(model))
    again = blocks_of(events(await streamed(asked(), second)))
    assert [(block["kind"], block["reuse"]["pieceId"]) for block in again][1] == (
        "simulation",
        str(stored[0].id),
    )
    assert again[1]["html"] == BATH_HTML
    assert len(model.calls) == 1
    assert pieces.kept[-1][2] == ()
    assert [piece.id for piece in pieces.pieces if piece.kind == "simulation"] == [stored[0].id]
