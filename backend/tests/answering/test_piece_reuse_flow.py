import uuid

from app.research.crafts import CraftResolution
from app.services.answering import AnswerAsk

from ..composer.fixtures import ALUM_CLAIM_ID, QUESTION, quote, section_reply, sentence
from .fakes import (
    SOURCES,
    UNDERSTOOD_REPLY,
    VIEWS,
    WRITTEN_LAKE_ID,
    WRITTEN_WASH_ID,
    FakeResearch,
    SectionModel,
    pipeline,
    streamed,
    understanding_model,
)
from .piece_fakes import MemoryPieces
from .test_answer_flow import LAKE_PAPER, REPLY, events

ANSWER_TEXT = "0b1c2d3e-4f50-4617-8293-a4b5c6d7e8f9"
FIRST_STORED_AT = "2026-11-12T08:16:00Z"
STORED_FOLLOW_UPS = [
    "What happens at each step of Kutch Ajrakh?",
    "What is the chemistry or physics behind Kutch Ajrakh?",
    "How do local water, soil and climate shape Kutch Ajrakh?",
]
FACTS = [
    "Alum is the mordant that binds alizarin to cotton.",
    "Mordant baths held 8 g/L alum and were heated to 60 °C.",
    "The red lake withstood 20 washes.",
]
WITHOUT_WASH = section_reply(
    sentence(
        "Alum is the mordant that binds alizarin to cotton.",
        quote(ALUM_CLAIM_ID, "Alum is the mordant that binds alizarin to cotton"),
    ),
    sentence(
        "Mordant baths held 8 g/L alum and were heated to 60 °C.",
        quote(LAKE_PAPER, "Mordanting baths of 8 g/L alum were heated to 60 °C"),
    ),
)
HISTORY_REPLY = section_reply(
    sentence(
        "Alum is the mordant that binds alizarin to cotton.",
        quote(ALUM_CLAIM_ID, "Alum is the mordant that binds alizarin to cotton"),
    )
)


def asked(depth: str = "DETAILED", *, fresh: bool = False) -> AnswerAsk:
    return AnswerAsk(question=QUESTION, depth=depth, fresh=fresh)


def memory() -> MemoryPieces:
    return MemoryPieces(views=list(VIEWS), sources=dict(SOURCES))


async def first_answer(pieces: MemoryPieces, depth: str = "DETAILED") -> None:
    await streamed(asked(depth), pipeline(replies=[REPLY], pieces=pieces))


def reuse_marks(found: list[tuple[str, dict]]) -> list[dict | None]:
    return [payload["block"]["reuse"] for name, payload in found if name == "block"]


REUSED_STREAM = [
    "understood",
    "status",
    "trail",
    "section_started",
    "source",
    "source",
    "source",
    "block",
    "section_done",
    "follow_ups",
    "done",
]


def piece_trail(piece_id: uuid.UUID) -> dict:
    return {
        "key": f"piece:{piece_id}",
        "stage": "FOUND",
        "group": "STORED",
        "title": "The chemistry",
        "url": None,
        "publisher": None,
        "year": None,
        "sourceId": None,
        "storedAt": FIRST_STORED_AT,
    }


async def test_the_first_answer_keeps_its_checked_block_as_a_piece() -> None:
    pieces = memory()
    await first_answer(pieces)
    (stored,) = pieces.current()
    assert (stored.kind, stored.facet, stored.topic_key, stored.depth) == (
        "prose",
        "CHEMISTRY",
        "reaction:kutch-ajrakh",
        "DETAILED",
    )
    assert stored.claim_ids == sorted([ALUM_CLAIM_ID, WRITTEN_LAKE_ID, WRITTEN_WASH_ID])
    assert [s.text for s in stored.payload.sentences] == FACTS


async def test_a_second_ask_reuses_the_stored_piece_and_researches_nothing() -> None:
    pieces = memory()
    await first_answer(pieces)
    (stored,) = pieces.current()
    research = FakeResearch()
    found = events(await streamed(asked(), pipeline(research=research, pieces=pieces)))
    assert research.requests == []
    assert [name for name, _ in found] == REUSED_STREAM
    assert found[2][1] == piece_trail(stored.id)
    assert found[3][1] == {
        "id": "s1",
        "discipline": "CHEMISTRY",
        "title": "The chemistry",
        "order": 1,
        "state": "WRITING",
    }
    block = found[7][1]["block"]
    assert (block["id"], block["reuse"]) == (
        "s1.b1",
        {"pieceId": str(stored.id), "storedAt": FIRST_STORED_AT},
    )
    assert [s["text"] for s in block["sentences"]] == FACTS
    assert found[8][1] == {"sectionId": "s1", "state": "READY", "searched": None}
    assert found[-2:] == [("follow_ups", {"items": STORED_FOLLOW_UPS}), ("done", {"answerId": ANSWER_TEXT})]
    assert pieces.kept[-1][2] == ()


async def test_research_runs_only_for_the_facet_without_a_reusable_piece() -> None:
    pieces = memory()
    await first_answer(pieces)
    research = FakeResearch()
    model = SectionModel(replies={"History": [HISTORY_REPLY]})
    two_fields = understanding_model({**UNDERSTOOD_REPLY, "disciplines": ["CHEMISTRY", "HISTORY"]})
    answer_pipeline = pipeline(
        research=research, understand_model=two_fields, compose_model=model, pieces=pieces
    )
    found = events(await streamed(asked(), answer_pipeline))
    assert [request.focus for request in research.requests] == ["HISTORY"]
    assert [call["title"] for call in model.calls] == ["History"]
    started = [(payload["id"], payload["state"]) for name, payload in found if name == "section_started"]
    assert started == [("s1", "WRITING"), ("s2", "RESEARCHING")]
    blocks = [
        (payload["sectionId"], payload["block"]["reuse"] is not None) for n, payload in found if n == "block"
    ]
    assert blocks == [("s1", True), ("s2", False)]
    assert {(piece.facet, piece.topic_key) for piece in pieces.current()} == {
        ("CHEMISTRY", "reaction:kutch-ajrakh"),
        ("HISTORY", "history:kutch-ajrakh"),
    }


async def test_a_basic_piece_is_not_reused_for_an_expert_ask() -> None:
    pieces = memory()
    await first_answer(pieces, depth="BASIC")
    (basic,) = pieces.current()
    research = FakeResearch()
    expert = events(
        await streamed(asked("EXPERT"), pipeline(research=research, replies=[REPLY], pieces=pieces))
    )
    assert len(research.requests) == 1
    assert reuse_marks(expert) == [None]
    (deeper,) = pieces.current()
    assert (deeper.depth, basic.id in {p.id for p in pieces.pieces}) == ("EXPERT", True)
    assert next(p for p in pieces.pieces if p.id == basic.id).superseded_by_id == deeper.id
    again = FakeResearch()
    found = events(await streamed(asked("BASIC"), pipeline(research=again, pieces=pieces)))
    assert again.requests == []
    assert [mark["pieceId"] for mark in reuse_marks(found)] == [str(deeper.id)]


async def test_fresh_research_bypasses_a_reusable_piece_and_replaces_it() -> None:
    pieces = memory()
    await first_answer(pieces)
    (old,) = pieces.current()
    research = FakeResearch()
    found = events(
        await streamed(asked(fresh=True), pipeline(research=research, replies=[REPLY], pieces=pieces))
    )
    assert len(research.requests) == 1
    assert reuse_marks(found) == [None]
    assert pieces.asked[-1].fresh is True
    (new,) = pieces.current()
    assert new.id != old.id
    assert next(p for p in pieces.pieces if p.id == old.id).superseded_by_id == new.id


async def test_a_retracted_claim_stales_the_piece_and_the_next_answer_rebuilds_it() -> None:
    pieces = memory()
    await first_answer(pieces)
    (old,) = pieces.current()
    pieces.retract(WRITTEN_WASH_ID)
    research = FakeResearch()
    rebuilt = events(
        await streamed(asked(), pipeline(research=research, replies=[WITHOUT_WASH], pieces=pieces))
    )
    assert len(research.requests) == 1
    assert reuse_marks(rebuilt) == [None]
    (new,) = pieces.current()
    assert new.claim_ids == sorted([ALUM_CLAIM_ID, WRITTEN_LAKE_ID])
    stale = next(p for p in pieces.pieces if p.id == old.id)
    assert (stale.stale_since is not None, stale.superseded_by_id) == (True, new.id)
    again = FakeResearch()
    found = events(await streamed(asked(), pipeline(research=again, pieces=pieces)))
    assert again.requests == []
    assert [mark["pieceId"] for mark in reuse_marks(found)] == [str(new.id)]


async def test_an_answer_for_any_craft_neither_reuses_nor_keeps_pieces() -> None:
    none = CraftResolution(status="NONE", craft=None, candidates=[], normalised="why", script="Latn")
    pieces = memory()
    await streamed(asked(), pipeline(resolution=none, replies=[REPLY], pieces=pieces))
    assert (pieces.asked[-1].craft, pieces.pieces) == (None, [])
    assert isinstance(pieces.kept[-1][0], uuid.UUID)
