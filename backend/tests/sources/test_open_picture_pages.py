import re
from urllib.parse import parse_qs, urlsplit

import pytest

from app.core.errors import InvalidInput
from app.research.open_pictures import COMMONS, FLICKR, OPENVERSE, open_link, open_source
from app.sources.images.flickr import FlickrPhotos
from app.sources.images.open_picture_pages import OpenPicturePages
from app.sources.images.openverse import OpenverseAdapter
from app.sources.reference.commons import WikimediaCommonsAdapter

from .recorded import RETRIEVED, Recorder, Reply, fixed_clock, source_http

COMMONS_API = "commons.wikimedia.org/w/api.php"
FLICKR_OEMBED = "www.flickr.com/services/oembed/"
DRYING = "8aaf6614-3a94-4478-9cab-ca3aefdf940e"
ELSEWHERE = "0f6d5c3b-2a19-4e87-9b10-5d4c3b2a1908"
BLOCK_PAGE = "https://commons.wikimedia.org/wiki/File:Printing_with_Hand_Carved_Block.jpg"
BLOCK_FILE = "https://upload.wikimedia.org/wikipedia/commons/3/3c/Printing_with_Hand_Carved_Block.jpg"


def openverse_record(identifier: str) -> str:
    return f"api.openverse.org/v1/images/{identifier}/"


def pages(routes: dict[str, Reply | list[Reply]]) -> tuple[OpenPicturePages, Recorder]:
    recorder = Recorder(routes)
    clock = fixed_clock()
    return (
        OpenPicturePages(
            WikimediaCommonsAdapter(source_http(recorder, "wikimedia_commons"), clock=clock),
            OpenverseAdapter(source_http(recorder, "openverse"), clock=clock),
            FlickrPhotos(source_http(recorder, "flickr"), clock=clock),
        ),
        recorder,
    )


def asked(recorder: Recorder, at: int = 0) -> dict[str, list[str]]:
    return parse_qs(urlsplit(str(recorder.requests[at].url)).query)


async def test_a_commons_file_is_read_with_its_licence_author_original_and_the_widest_width_the_site_draws() -> (
    None
):
    reader, recorder = pages({COMMONS_API: Reply("commons_picture.json")})
    found = await reader.record(open_link(BLOCK_PAGE))
    assert (found.site, found.page_url, found.file_url) == (COMMONS, BLOCK_PAGE, BLOCK_FILE)
    assert found.fetch_url == (
        "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3c/Printing_with_Hand_Carved_Block.jpg/"
        "1920px-Printing_with_Hand_Carved_Block.jpg"
    )
    assert (found.author, found.licence, found.licence_url) == (
        "Ketayun Katz",
        "CC BY-SA 4.0",
        "https://creativecommons.org/licenses/by-sa/4.0",
    )
    assert (found.title, found.width, found.height, found.read_at) == (
        "Printing with Hand Carved Block",
        4000,
        3000,
        RETRIEVED,
    )
    sent = asked(recorder)
    assert (sent["titles"], sent["iiurlwidth"], sent["redirects"]) == (
        ["File:Printing with Hand Carved Block.jpg"],
        ["1920"],
        ["1"],
    )
    assert "extmetadata" in sent["iiprop"][0].split("|")
    assert parse_qs(urlsplit(found.record_url).query)["titles"] == [
        "File:Printing with Hand Carved Block.jpg"
    ]


async def test_a_commons_name_with_no_file_is_refused() -> None:
    reader, _ = pages({COMMONS_API: Reply("commons_picture_missing.json")})
    with pytest.raises(
        InvalidInput, match=re.escape("Wikimedia Commons has no file named File:No such picture.jpg")
    ):
        await reader.record(open_link("https://commons.wikimedia.org/wiki/File:No_such_picture.jpg"))


async def test_an_openverse_record_of_a_flickr_photo_is_read_from_flickr_itself() -> None:
    routes: dict[str, Reply | list[Reply]] = {
        openverse_record(DRYING): Reply("openverse_picture.json"),
        FLICKR_OEMBED: Reply("flickr_oembed.json"),
    }
    reader, recorder = pages(routes)
    found = await reader.record(open_link(f"https://openverse.org/image/{DRYING}"))
    assert (found.site, found.page_url, found.author) == (
        FLICKR,
        "https://www.flickr.com/photos/nevilzaveri/339988080/",
        "nevil zaveri (thanks for 25M views)",
    )
    assert asked(recorder, 1) == {
        "url": ["https://www.flickr.com/photos/43109416@N00/339988080/"],
        "format": ["json"],
    }
    assert open_source(found).credit == "Photo: nevil zaveri (thanks for 25M views), CC BY 2.0, via Flickr"


async def test_an_openverse_record_from_another_site_is_credited_via_openverse_from_that_site() -> None:
    reader, _ = pages({openverse_record(ELSEWHERE): Reply("openverse_picture_elsewhere.json")})
    found = await reader.record(open_link(f"https://openverse.org/image/{ELSEWHERE}"))
    assert (found.site, found.licence, found.original_site, found.width) == (
        OPENVERSE,
        "CC0 1.0",
        "rawpixel.com",
        1800,
    )
    assert open_source(found).credit == "Photo: Jane Doe, CC0 1.0, via Openverse from rawpixel.com"


async def test_an_openverse_identifier_it_does_not_hold_is_refused() -> None:
    reader, _ = pages({openverse_record(ELSEWHERE): Reply("openverse_missing.json", status=404)})
    with pytest.raises(InvalidInput, match=f"Openverse holds no picture {ELSEWHERE}"):
        await reader.record(open_link(f"https://openverse.org/image/{ELSEWHERE}"))


async def test_a_flickr_photo_s_licence_and_author_come_from_flickr_s_own_record() -> None:
    reader, _ = pages({FLICKR_OEMBED: Reply("flickr_oembed_reserved.json")})
    found = await reader.record(open_link("https://www.flickr.com/photos/bees/2341623661/"))
    assert (found.licence, found.licence_url) == ("All Rights Reserved", None)
    with pytest.raises(InvalidInput, match="Its licence, All Rights Reserved, reserves all rights"):
        open_source(found)
