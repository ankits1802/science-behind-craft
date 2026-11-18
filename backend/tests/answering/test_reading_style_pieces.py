import dataclasses

from app.services.piece_rebuild import rebuild_group

from ..planner.fakes import FakeModel
from .fakes import SOURCES, VIEWS, FakeStore, pipeline, streamed
from .piece_fakes import MemoryPieces
from .test_answer_flow import REPLY, detailed
from .test_piece_rebuild import group


async def test_a_teen_readers_section_is_kept_in_their_style_and_served_only_to_their_style() -> None:
    pieces = MemoryPieces(views=list(VIEWS), sources=dict(SOURCES))
    await streamed(detailed(reading_style="TEEN"), pipeline(replies=[REPLY], pieces=pieces))
    kept = pieces.current()
    assert kept and {piece.reading_style for piece in kept if piece.kind == "prose"} == {"TEEN"}
    assert all(
        piece.reading_style is None
        for piece in kept
        if piece.kind != "prose" and piece.kind != "process_ladder"
    )
    adult = FakeModel([REPLY])
    await streamed(detailed(), pipeline(compose_model=adult, pieces=pieces))
    assert adult.calls, "an adult is never served the teen's section from the store"
    teen = FakeModel([REPLY])
    await streamed(detailed(reading_style="TEEN"), pipeline(compose_model=teen, pieces=pieces))
    assert teen.calls == []


async def test_the_nightly_rebuild_recomposes_a_stale_piece_in_its_own_style() -> None:
    model = FakeModel([REPLY])
    store = FakeStore()
    pieces = MemoryPieces(views=list(VIEWS), sources=dict(SOURCES))
    styled_group = dataclasses.replace(group(), reading_style="CHILD")
    await rebuild_group(styled_group, pipeline(compose_model=model, store=store, pieces=pieces))
    ((ask, _understanding),) = store.begun
    assert ask.reading_style == "CHILD"
    assert all(call["system"].endswith("follow every source rule above.") for call in model.calls)
