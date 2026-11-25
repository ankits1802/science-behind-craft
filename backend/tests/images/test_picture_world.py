import uuid

from app.research.blocks import ImagesBlock
from app.research.image_relevance import ClaimText
from app.services.section_images import SectionImages, SectionImagesAsk

from .fakes import FakeContexts, FakeMediaStore, FakeSource, candidate, searched_by, stored_picture

STICKY = ClaimText(uuid.UUID(int=31), "Printing with sticky gums and lime takes skill.")
BRICKS = candidate("openverse", 1, "Brick House iPhone Background", licence="CC BY 2.0", author="P. Hoesly")
GUMS = candidate("wikimedia_commons", 2, "Sticky gums for printing", licence="CC0", author="A")
CARD = candidate("searxng", 3, "Ajrakh Block Printing | Crafts of Kutch", licence=None, author=None)
VATS = candidate(
    "curation",
    4,
    "Workers beating the vats at an indigo factory in Allahabad in 1877",
    licence="Public domain",
    author="Oscar Mallitte",
)
FIELD = candidate(
    "field_repository",
    5,
    "An artisan at work",
    licence="CC BY 4.0",
    author="A field team",
    credit="Field Repository",
)
LAKE = candidate("openverse", 6, "Mountain lake at dawn", licence="CC0", author="B")


def ask(*, craft_slug: str | None = "Kutch-Ajrakh") -> SectionImagesAsk:
    return SectionImagesAsk(
        block_id="s3.b2", craft_name="Kutch Ajrakh", claim_ids=(STICKY.claim_id,), craft_slug=craft_slug
    )


async def shown(store: FakeMediaStore, *found: FakeSource) -> ImagesBlock | None:
    return await SectionImages(sources=searched_by(*found), store=store, context=FakeContexts()).block(ask())


async def test_a_stored_text_picture_of_another_world_is_not_served_and_the_section_searches() -> None:
    commons = FakeSource("wikimedia_commons", [GUMS])
    store = FakeMediaStore({STICKY.claim_id: STICKY}, pictures=[stored_picture(BRICKS, STICKY.claim_id)])
    block = await shown(store, commons)
    assert block is not None
    assert [item.media.title for item in block.items] == ["Sticky gums for printing"]
    assert commons.queries == ["Kutch Ajrakh printing sticky"]
    assert [picture.media.title for picture in store.pictures] == ["Brick House iPhone Background"]


async def test_a_stored_text_picture_naming_the_craft_s_world_is_served_without_a_search() -> None:
    commons = FakeSource("wikimedia_commons", [GUMS])
    store = FakeMediaStore({STICKY.claim_id: STICKY}, pictures=[stored_picture(CARD, STICKY.claim_id)])
    block = await shown(store, commons)
    assert block is not None
    assert [(item.media.title, item.relevance) for item in block.items] == [
        ("Ajrakh Block Printing | Crafts of Kutch", "TEXT")
    ]
    assert commons.queries == []


async def test_a_curator_s_pick_a_field_photo_and_a_vision_verdict_are_served_whatever_their_words() -> None:
    store = FakeMediaStore(
        {STICKY.claim_id: STICKY},
        pictures=[
            stored_picture(VATS, STICKY.claim_id),
            stored_picture(FIELD, STICKY.claim_id),
            stored_picture(LAKE, STICKY.claim_id, "VISION"),
            stored_picture(BRICKS, STICKY.claim_id),
        ],
    )
    block = await shown(store)
    assert block is not None
    assert [(item.media.title, item.relevance) for item in block.items] == [
        ("Workers beating the vats at an indigo factory in Allahabad in 1877", "TEXT"),
        ("An artisan at work", "TEXT"),
        ("Mountain lake at dawn", "VISION"),
    ]


async def test_a_searched_picture_naming_nothing_of_the_craft_s_world_is_never_kept() -> None:
    store = FakeMediaStore({STICKY.claim_id: STICKY})
    walls = candidate("openverse", 7, "Brick walls with lime and gums", licence="CC0", author="C")
    block = await shown(store, FakeSource("openverse", [walls]))
    assert block is None
    assert store.kept == []


async def test_the_craft_s_world_is_read_for_the_craft_the_ask_names() -> None:
    contexts = FakeContexts()
    store = FakeMediaStore({STICKY.claim_id: STICKY}, pictures=[stored_picture(CARD, STICKY.claim_id)])
    images = SectionImages(sources=searched_by(), store=store, context=contexts)
    await images.block(ask())
    await images.block(ask(craft_slug=None))
    assert contexts.asked == ["Kutch-Ajrakh", None]
