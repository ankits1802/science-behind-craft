import uuid

import httpx

from app.research.blocks import ImagesBlock
from app.research.image_relevance import ClaimText
from app.services.live_sources import LiveSourcesStore
from app.services.section_images import SectionImages, SectionImagesAsk, image_search_text

from .fakes import FakeMediaStore, FakeSource, candidate

STICKY = ClaimText(uuid.UUID(int=11), "Printing with sticky gums takes skill.")
WASHED = ClaimText(uuid.UUID(int=12), "The cloth is washed in the river.")


def ask(*claims: ClaimText) -> SectionImagesAsk:
    return SectionImagesAsk(
        block_id="s2.b3", craft_name="Kutch Ajrakh", claim_ids=tuple(c.claim_id for c in claims)
    )


async def test_an_images_block_shows_open_pictures_inline_and_others_as_link_cards() -> None:
    commons = FakeSource(
        "wikimedia_commons",
        [candidate("commons", 1, "Sticky gums for printing", licence="CC BY-SA 4.0", author="SMarndi")],
    )
    web = FakeSource("searxng", [candidate("web", 2, "Printing with sticky gums", licence=None, author=None)])
    store = FakeMediaStore({STICKY.claim_id: STICKY, WASHED.claim_id: WASHED})
    block = await SectionImages(sources=(commons, web), store=store).block(ask(STICKY, WASHED))
    assert isinstance(block, ImagesBlock)
    assert block.id == "s2.b3"
    assert [item.media.display for item in block.items] == ["INLINE", "LINK_CARD"]
    assert [item.claim_ids for item in block.items] == [[STICKY.claim_id], [STICKY.claim_id]]
    assert {item.relevance for item in block.items} == {"TEXT"}
    assert block.illustrated_claim_ids() == {str(STICKY.claim_id)}


async def test_a_failing_image_service_leaves_the_others_to_answer() -> None:
    broken = FakeSource("openverse", [], failing=True)
    commons = FakeSource(
        "wikimedia_commons", [candidate("commons", 1, "Sticky gums for printing", licence="CC0", author="A")]
    )
    store = FakeMediaStore({STICKY.claim_id: STICKY})
    block = await SectionImages(sources=(broken, commons), store=store).block(ask(STICKY))
    assert block is not None
    assert len(block.items) == 1


async def test_a_slow_image_service_is_left_out_and_the_others_still_answer() -> None:
    found = [candidate("web", 2, "Printing with sticky gums", licence=None, author=None)]
    slow = FakeSource("searxng", found, hanging=True)
    commons = FakeSource(
        "wikimedia_commons", [candidate("commons", 1, "Sticky gums for printing", licence="CC0", author="A")]
    )
    store = FakeMediaStore({STICKY.claim_id: STICKY})
    images = SectionImages(sources=(slow, commons), store=store, search_seconds=0.01)
    block = await images.block(ask(STICKY))
    assert block is not None
    assert [item.media.provider for item in block.items] == ["commons"]
    assert slow.queries == ["Kutch Ajrakh printing sticky"]


async def test_no_relevant_picture_or_no_visible_claim_is_no_block() -> None:
    unrelated = FakeSource(
        "wikimedia_commons", [candidate("commons", 1, "Mountain lake at dawn", licence="CC0", author="A")]
    )
    store = FakeMediaStore({WASHED.claim_id: WASHED})
    assert await SectionImages(sources=(unrelated,), store=store).block(ask(WASHED)) is None
    assert await SectionImages(sources=(unrelated,), store=FakeMediaStore({})).block(ask(STICKY)) is None
    assert store.kept == []


async def test_an_empty_search_with_topic_words_is_tried_again_with_the_craft_name() -> None:
    empty = FakeSource("openverse", [])
    store = FakeMediaStore({STICKY.claim_id: STICKY})
    await SectionImages(sources=(empty,), store=store).block(ask(STICKY))
    assert empty.queries == ["Kutch Ajrakh printing sticky", "Kutch Ajrakh"]


def test_the_search_text_is_the_craft_name_and_the_most_shared_claim_words() -> None:
    assert image_search_text("Kutch Ajrakh", [STICKY, WASHED]) == "Kutch Ajrakh printing sticky"


async def test_the_live_store_builds_the_three_image_sources_once() -> None:
    store = LiveSourcesStore(client_factory=httpx.AsyncClient)
    try:
        first = await store.images()
        assert [source.name for source in first] == ["wikimedia_commons", "openverse", "searxng"]
        assert await store.images() is first
    finally:
        await store.aclose()
