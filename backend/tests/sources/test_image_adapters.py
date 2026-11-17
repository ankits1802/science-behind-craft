import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.research.images import (
    MEDIA_TEXT_MAX_CHARS,
    ImageQuery,
    clipped,
    media_ref_of,
    same_site,
    without_tracking,
)
from app.sources.images.openverse import OpenverseAdapter
from app.sources.records import UnusableRecord
from app.sources.reference.commons import WikimediaCommonsAdapter
from app.sources.web.searxng import SearxngAdapter

from .recorded import FIXTURES, Recorder, Reply, source_http

COMMONS_API = "commons.wikimedia.org/w/api.php"
OPENVERSE_API = "api.openverse.org/v1/images/"
SEARXNG = "search.example.org/search"
RETRIEVED = datetime(2026, 11, 17, 10, 20, tzinfo=UTC)
GOLDEN = Path(__file__).resolve().parents[3] / "shared" / "explainer.document.golden.json"
INLINE_FIXTURE_ID = uuid.UUID("a1c3e5f7-0b2d-4f6a-8c9e-1d3f5a7b9c0e")


class UnusedFetcher:
    async def fetch(self, request: object) -> object:
        raise AssertionError("image search never reads a page")


def at_retrieval() -> datetime:
    return RETRIEVED


def golden_media(display: str) -> dict:
    document = json.loads(GOLDEN.read_text(encoding="utf-8"))
    for section in document["sections"]:
        for block in section["blocks"]:
            if block["kind"] == "images":
                return next(item["media"] for item in block["items"] if item["media"]["display"] == display)
    raise AssertionError("the golden explainer has no image block")


async def test_commons_images_keep_the_file_page_thumbnail_size_author_and_licence() -> None:
    recorder = Recorder({COMMONS_API: Reply("commons_images.json")})
    adapter = WikimediaCommonsAdapter(source_http(recorder, "wikimedia_commons"), clock=at_retrieval)
    found = await adapter.images(ImageQuery(text="Ajrak printing"), 3)
    assert [image.title for image in found] == [
        "Ajrak Printing Materials 2",
        "Ajrak Printing Materials 1",
        "Ajrak",
    ]
    gums = found[1]
    assert gums.page_url == "https://commons.wikimedia.org/wiki/File:Ajrak_Printing_Materials_1.jpg"
    assert gums.image_url == (
        "https://thumb.wikimedia.org/wikipedia/commons/thumb/4/4e/Ajrak_Printing_Materials_1.jpg/"
        "960px-Ajrak_Printing_Materials_1.jpg"
    )
    assert (
        gums.original_url
        == "https://upload.wikimedia.org/wikipedia/commons/4/4e/Ajrak_Printing_Materials_1.jpg"
    )
    assert (gums.width, gums.height) == (4160, 3120)
    assert (gums.author, gums.licence, gums.site) == ("SMarndi", "CC BY-SA 4.0", "Wikimedia Commons")
    assert gums.licence_url == "https://creativecommons.org/licenses/by-sa/4.0"
    assert gums.alt == "Sticky gums used during indigo printing."
    sent = recorder.requests[0].url.params
    assert (sent["generator"], sent["gsrnamespace"], sent["gsrlimit"], sent["iiurlwidth"]) == (
        "search",
        "6",
        "3",
        "960",
    )
    assert "size" in sent["iiprop"].split("|")


async def test_a_commons_image_becomes_the_inline_media_of_the_contract_fixture() -> None:
    recorder = Recorder({COMMONS_API: Reply("commons_images.json")})
    adapter = WikimediaCommonsAdapter(source_http(recorder, "wikimedia_commons"), clock=at_retrieval)
    gums = (await adapter.images(ImageQuery(text="Ajrak printing"), 3))[1]
    media = media_ref_of(gums, media_id=INLINE_FIXTURE_ID, source_id=None)
    assert media.model_dump(mode="json", by_alias=True) == golden_media("INLINE")


async def test_openverse_keeps_only_open_licences_with_a_creator() -> None:
    recorder = Recorder({OPENVERSE_API: Reply("openverse_images.json")})
    adapter = OpenverseAdapter(source_http(recorder, "openverse"), clock=at_retrieval)
    found = await adapter.images(ImageQuery(text="block printing india"), 8)
    assert [image.page_url.rsplit("/", 1)[1] for image in found] == [
        "3346259692",
        "4145434931",
        "8356931475",
        "8356877663",
        "8356860093",
    ]
    first = found[0]
    assert (first.licence, first.licence_url) == ("CC BY 2.0", "https://creativecommons.org/licenses/by/2.0/")
    assert (first.author, first.site, first.title) == (
        "nevil zaveri (thank you for 20+M views:)",
        "Flickr",
        "stretch of art, dhamadka kutch",
    )
    assert (
        first.image_url == "https://api.openverse.org/v1/images/7b9d6538-0d6f-47f9-a3cd-202481032537/thumb/"
    )
    assert first.original_url == "https://live.staticflickr.com/3123/3346259692_408c436f2b.jpg"
    assert (first.width, first.height) == (484, 324)
    assert first.description is not None and first.description.startswith(
        "bhuj, block, blog, color, dhamadka"
    )
    sent = recorder.requests[0].url.params
    assert (sent["license"], sent["page_size"], sent["mature"]) == ("by,by-sa,cc0,pdm", "8", "false")


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"license": "by-nc-sa"}, "not open"),
        ({"creator": None}, "no creator"),
        ({"mature": True}, "mature"),
        ({"thumbnail": "http://api.openverse.org/thumb/"}, "no https"),
    ],
)
def test_an_openverse_result_without_an_open_licence_or_credit_is_left_out(change: dict, reason: str) -> None:
    record = json.loads((FIXTURES / "openverse_images.json").read_text(encoding="utf-8"))["results"][0]
    adapter = OpenverseAdapter(source_http(Recorder({}), "openverse"), clock=at_retrieval)
    with pytest.raises(UnusableRecord, match=reason):
        adapter._candidate(record | change, RETRIEVED)


async def test_searxng_image_results_are_link_cards_served_by_the_page_site() -> None:
    recorder = Recorder({SEARXNG: Reply("searxng_images.synthetic.json")})
    adapter = SearxngAdapter(
        source_http(recorder, "searxng"),
        base_url="https://search.example.org",
        fetcher=UnusedFetcher(),
        clock=at_retrieval,
    )
    found = await adapter.images(ImageQuery(text="Kutch Ajrakh resist paste"), 10)
    assert [image.page_url for image in found] == [
        "https://collections.vam.ac.uk/item/O132500/",
        "https://museum.example.org/collection/ajrakh-resist-paste",
    ]
    vam, museum = found
    assert vam.image_url == "https://framemark.vam.ac.uk/collections/2015HK4003/full/!100,100/0/default.jpg"
    assert (vam.width, vam.height, vam.site, vam.licence) == (None, None, "collections.vam.ac.uk", None)
    assert (museum.width, museum.height, museum.author) == (1200, 800, "Museum photography studio")
    assert recorder.requests[0].url.params["categories"] == "images"
    cards = [media_ref_of(image, media_id=uuid.uuid4(), source_id=None) for image in found]
    assert [card.display for card in cards] == ["LINK_CARD", "LINK_CARD"]


async def test_a_non_open_or_uncredited_picture_becomes_a_link_card() -> None:
    recorder = Recorder({COMMONS_API: Reply("commons_images.json")})
    adapter = WikimediaCommonsAdapter(source_http(recorder, "wikimedia_commons"), clock=at_retrieval)
    gums = (await adapter.images(ImageQuery(text="Ajrak printing"), 3))[1]
    closed = gums.model_copy(
        update={"licence": "CC BY-NC 4.0", "licence_url": "https://creativecommons.org/licenses/by-nc/4.0"}
    )
    uncredited = gums.model_copy(update={"author": None})
    assert media_ref_of(gums, media_id=uuid.uuid4(), source_id=None).display == "INLINE"
    assert media_ref_of(closed, media_id=uuid.uuid4(), source_id=None).display == "LINK_CARD"
    assert media_ref_of(uncredited, media_id=uuid.uuid4(), source_id=None).display == "LINK_CARD"


@pytest.mark.parametrize(
    ("page", "image", "same"),
    [
        ("https://collections.vam.ac.uk/item/O1/", "https://framemark.vam.ac.uk/a.jpg", True),
        ("https://www.example.org/a", "https://media.example.org/a.jpg", True),
        ("https://shop.example.in/a", "https://cdn.imagehost.example.net/a.jpg", False),
        ("https://a.gov.in/page", "https://b.gov.in/a.jpg", False),
        ("https://10.0.0.1/page", "https://10.0.0.1/a.jpg", False),
        ("https://localhost/page", "https://localhost/a.jpg", False),
    ],
)
def test_an_image_is_from_the_page_site_only_when_both_share_a_registrable_name(
    page: str, image: str, same: bool
) -> None:
    assert same_site(page, image) is same


def test_tracking_parameters_are_dropped_and_other_parameters_kept() -> None:
    assert (
        without_tracking("https://a.example.org/x.jpg?utm_source=c&utm_content=t")
        == "https://a.example.org/x.jpg"
    )
    assert (
        without_tracking("https://a.example.org/x.jpg?w=200&utm_source=c")
        == "https://a.example.org/x.jpg?w=200"
    )
    assert (
        without_tracking("https://a.example.org/x/!100,100/0.jpg") == "https://a.example.org/x/!100,100/0.jpg"
    )


def test_long_picture_text_is_clipped_on_a_word_with_an_ellipsis() -> None:
    long = "word " * 100
    shown = clipped(long)
    assert len(shown) <= MEDIA_TEXT_MAX_CHARS
    assert shown.endswith("word…")
    assert clipped("  Sticky   gums  ") == "Sticky gums"
