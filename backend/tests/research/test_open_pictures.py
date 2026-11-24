import io
from datetime import UTC, datetime
from typing import Any

import pytest
from PIL import Image

from app.core.errors import InvalidInput
from app.research.image_intake_pixels import THUMBNAIL_SIDE, thumbnail
from app.research.licences import ALL_RIGHTS_RESERVED, NO_DERIVATIVES, NON_COMMERCIAL, licence_restriction
from app.research.open_pictures import (
    COMMONS,
    FLICKR,
    OPENVERSE,
    OpenLink,
    OpenPictureRecord,
    credited_author,
    credited_licence,
    flickr_photo_id,
    open_link,
    open_source,
    photo_credit,
)

from ..pictures import picture

READ = datetime(2026, 11, 24, 9, 30, tzinfo=UTC)
OPENVERSE_ID = "8aaf6614-3a94-4478-9cab-ca3aefdf940e"
RTL_OVERRIDE, POP = chr(0x202E), chr(0x202C)
HIDDEN_MARKS = f"{RTL_OVERRIDE}{POP}"
ACCEPTED = "KalaVigyan takes only public domain, CC0, CC BY or CC BY-SA pictures, any version"


@pytest.mark.parametrize(
    ("url", "link"),
    [
        (
            "https://commons.wikimedia.org/wiki/File:Printing_with_Hand_Carved_Block.jpg",
            OpenLink(
                COMMONS,
                "File:Printing with Hand Carved Block.jpg",
                "https://commons.wikimedia.org/wiki/File:Printing_with_Hand_Carved_Block.jpg",
            ),
        ),
        (
            "https://commons.m.wikimedia.org/wiki/File:Fabric%20drying.jpg",
            OpenLink(
                COMMONS, "File:Fabric drying.jpg", "https://commons.wikimedia.org/wiki/File:Fabric_drying.jpg"
            ),
        ),
        (
            "https://commons.wikimedia.org/w/index.php?title=File:Workshop_wide_shot.jpg&oldid=1",
            OpenLink(
                COMMONS,
                "File:Workshop wide shot.jpg",
                "https://commons.wikimedia.org/wiki/File:Workshop_wide_shot.jpg",
            ),
        ),
        (
            "https://upload.wikimedia.org/wikipedia/commons/a/ab/Ajrak_Craft.jpeg",
            OpenLink(
                COMMONS, "File:Ajrak Craft.jpeg", "https://commons.wikimedia.org/wiki/File:Ajrak_Craft.jpeg"
            ),
        ),
        (
            f"https://openverse.org/image/{OPENVERSE_ID.upper()}",
            OpenLink(OPENVERSE, OPENVERSE_ID, f"https://openverse.org/image/{OPENVERSE_ID}"),
        ),
        (
            f"https://openverse.org/en-gb/image/{OPENVERSE_ID}/",
            OpenLink(OPENVERSE, OPENVERSE_ID, f"https://openverse.org/image/{OPENVERSE_ID}"),
        ),
        (
            f"https://api.openverse.org/v1/images/{OPENVERSE_ID}/",
            OpenLink(OPENVERSE, OPENVERSE_ID, f"https://openverse.org/image/{OPENVERSE_ID}"),
        ),
        (
            "https://www.flickr.com/photos/43109416@N00/339988080/in/photostream/",
            OpenLink(FLICKR, "339988080", "https://www.flickr.com/photos/43109416@N00/339988080/"),
        ),
        ("https://flic.kr/p/w3wBs", OpenLink(FLICKR, "339988080", "https://flic.kr/p/w3wBs")),
    ],
)
def test_a_picture_s_page_on_commons_openverse_or_flickr_names_what_its_site_is_asked(
    url: str, link: OpenLink
) -> None:
    assert open_link(url) == link


@pytest.mark.parametrize(
    "url",
    [
        "http://commons.wikimedia.org/wiki/File:Ajrak_Craft.jpeg",
        "https://commons.wikimedia.org/wiki/Category:Ajrak",
        "https://www.flickr.com/photos/43109416@N00/albums/72157594",
        "https://example.org/wiki/File:Ajrak_Craft.jpeg",
        "https://openverse.org/image/not-an-identifier",
    ],
)
def test_any_other_address_is_refused_naming_the_pages_taken(url: str) -> None:
    with pytest.raises(InvalidInput, match="is not a picture's page on Wikimedia Commons"):
        open_link(url)


def test_a_flickr_short_code_is_its_photo_number_in_base_58() -> None:
    assert flickr_photo_id("w3wBs") == 339988080


@pytest.mark.parametrize(
    ("name", "url", "shown"),
    [
        ("CC0", "https://creativecommons.org/publicdomain/zero/1.0/", "CC0"),
        ("Public domain", None, "Public domain"),
        ("Public Domain Mark 1.0", None, "Public Domain Mark 1.0"),
        (None, "https://creativecommons.org/publicdomain/mark/1.0/", "Public Domain Mark 1.0"),
        ("CC BY 2.0", "https://creativecommons.org/licenses/by/2.0/", "CC BY 2.0"),
        ("CC BY 4.0", None, "CC BY 4.0"),
        ("CC BY-SA 3.0", "https://creativecommons.org/licenses/by-sa/3.0", "CC BY-SA 3.0"),
        ("CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0", "CC BY-SA 4.0"),
        ("Attribution-ShareAlike License", "https://creativecommons.org/licenses/by-sa/2.0/", "CC BY-SA 2.0"),
    ],
)
def test_public_domain_cc0_cc_by_and_cc_by_sa_of_any_version_are_taken(
    name: str | None, url: str | None, shown: str
) -> None:
    assert credited_licence(name, url) == shown


@pytest.mark.parametrize(
    ("name", "url", "says"),
    [
        ("CC BY-NC 2.0", None, "Its licence, CC BY-NC 2.0, forbids commercial use (NC)"),
        ("CC BY-NC-SA 4.0", None, "Its licence, CC BY-NC-SA 4.0, forbids commercial use (NC)"),
        ("CC BY-ND 4.0", None, "Its licence, CC BY-ND 4.0, forbids changes such as a crop (ND)"),
        (
            "CC BY 2.0",
            "https://creativecommons.org/licenses/by-nd/2.0/",
            "Its licence, CC BY 2.0, forbids changes such as a crop (ND)",
        ),
        ("All Rights Reserved", None, "Its licence, All Rights Reserved, reserves all rights"),
        ("GFDL", None, "Its licence, GFDL, is not one KalaVigyan takes"),
        ("No known copyright restrictions", None, "Its licence, No known copyright restrictions, is not one"),
        (None, None, "Its page states no licence, so it cannot be shown"),
    ],
)
def test_non_commercial_no_derivatives_all_rights_reserved_and_unknown_licences_are_refused_by_name(
    name: str | None, url: str | None, says: str
) -> None:
    with pytest.raises(InvalidInput) as refused:
        credited_licence(name, url)
    assert str(refused.value).startswith(says) and ACCEPTED in str(refused.value)


def test_each_restriction_is_named_from_a_licence_s_name_or_address() -> None:
    assert licence_restriction("Attribution-NonCommercial License") == NON_COMMERCIAL
    assert licence_restriction("https://creativecommons.org/licenses/by-nc-nd/4.0/") == NON_COMMERCIAL
    assert licence_restriction("Attribution-NoDerivs License") == NO_DERIVATIVES
    assert licence_restriction("All rights reserved") == ALL_RIGHTS_RESERVED
    assert licence_restriction("CC BY-SA 4.0") is None and licence_restriction(None) is None


@pytest.mark.parametrize("author", [None, "", "   ", "Unknown author", "anonymous", HIDDEN_MARKS])
def test_a_picture_whose_author_cannot_be_credited_is_refused(author: str | None) -> None:
    with pytest.raises(InvalidInput, match="names no author to credit"):
        credited_author(author)


def test_an_author_s_hidden_direction_marks_are_dropped() -> None:
    assert credited_author(f"{RTL_OVERRIDE}{chr(0x202D)}{POP}bees{POP}") == "bees"


def record(site: str, **changes: Any) -> OpenPictureRecord:
    values: dict[str, Any] = {
        "site": site,
        "page_url": "https://commons.wikimedia.org/wiki/File:Printing_with_Hand_Carved_Block.jpg",
        "file_url": "https://upload.wikimedia.org/wikipedia/commons/3/3c/Printing_with_Hand_Carved_Block.jpg",
        "fetch_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3c/x.jpg/1920px-x.jpg",
        "record_url": "https://commons.wikimedia.org/w/api.php?action=query",
        "title": "Printing with Hand Carved Block",
        "author": "Ketayun Katz",
        "licence": "CC BY-SA 4.0",
        "licence_url": "https://creativecommons.org/licenses/by-sa/4.0",
        "width": 4000,
        "height": 3000,
        "read_at": READ,
    }
    return OpenPictureRecord.model_validate(values | changes)


def test_the_credit_names_the_author_the_licence_and_the_site_in_the_design_s_form() -> None:
    commons = open_source(record(COMMONS))
    flickr = open_source(
        record(
            FLICKR, author="nevil zaveri (thank you for 20+M views:)", licence="CC BY 2.0", licence_url=None
        )
    )
    openverse = open_source(
        record(
            OPENVERSE, author="Jane Doe", licence="CC0 1.0", licence_url=None, original_site="rawpixel.com"
        )
    )
    assert commons.credit == "Photo: Ketayun Katz, CC BY-SA 4.0, via Wikimedia Commons"
    assert flickr.credit == "Photo: nevil zaveri (thank you for 20+M views:), CC BY 2.0, via Flickr"
    assert openverse.credit == "Photo: Jane Doe, CC0 1.0, via Openverse from rawpixel.com"
    assert (commons.page_url, commons.read_at) == (record(COMMONS).page_url, READ)


def test_the_credit_line_keeps_only_the_parts_a_source_states() -> None:
    assert photo_credit(None, None, "Wikimedia Commons") == "Photo: Wikimedia Commons"
    assert photo_credit("A. Printer", None, "Flickr") == "Photo: A. Printer, via Flickr"


def test_a_licence_is_judged_before_its_author() -> None:
    with pytest.raises(InvalidInput, match="forbids commercial use"):
        open_source(record(FLICKR, author=None, licence="CC BY-NC 2.0", licence_url=None))


def test_the_thumbnail_returned_to_the_agent_is_a_small_jpeg_of_the_whole_picture() -> None:
    shown = Image.open(io.BytesIO(thumbnail(picture(800, 600, seed=3))))
    assert (shown.format, shown.size) == ("JPEG", (THUMBNAIL_SIDE, 240))
    tall = Image.open(io.BytesIO(thumbnail(picture(375, 500, seed=4, kind="JPEG"))))
    assert tall.size == (240, THUMBNAIL_SIDE)
