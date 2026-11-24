import io
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.models import ImageContribution, MediaAsset, OpenPicture, User
from app.research.craft_contributed import contributed_url
from app.research.image_contributions import BatchPicture
from app.research.image_intake_fetch import FetchedPicture
from app.research.open_pictures import COMMONS, FLICKR, OpenLink, OpenPictureRecord
from app.services import image_contributions as images
from app.services.monograph_generated_pictures import plate_spec, plates_of
from app.services.open_pictures import ON_THE_PAGE, OpenGiven, OpenPlacing, OpenTools, place_open_pictures

from ..pictures import AI_SOURCE, FakeObjects, picture, screen_tools
from .picture_seed import FACT, NOW, SLUG, STAGE, People, people_in, seeded_session

pytestmark = pytest.mark.db

READ = datetime(2026, 11, 24, 9, 30, tzinfo=UTC)
BLOCK_PAGE = "https://commons.wikimedia.org/wiki/File:Printing_with_Hand_Carved_Block.jpg"
BLOCK_FILE = "https://upload.wikimedia.org/wikipedia/commons/3/3c/Printing_with_Hand_Carved_Block.jpg"
BLOCK_FETCH = "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3c/x.jpg/1920px-x.jpg"
RACK_PAGE = "https://www.flickr.com/photos/nevilzaveri/339988080/"
RACK_FILE = "https://live.staticflickr.com/146/339988080_a98e6b2091.jpg"
BLOCK_CREDIT = "Photo: Ketayun Katz, CC BY-SA 4.0, via Wikimedia Commons"
RACK_CREDIT = "Photo: nevil zaveri, CC BY 2.0, via Flickr"


def commons(**changes: Any) -> OpenPictureRecord:
    values: dict[str, Any] = {
        "site": COMMONS,
        "page_url": BLOCK_PAGE,
        "file_url": BLOCK_FILE,
        "fetch_url": BLOCK_FETCH,
        "record_url": "https://commons.wikimedia.org/w/api.php?action=query&titles=File%3APrinting",
        "title": "Printing with Hand Carved Block",
        "author": "Ketayun Katz",
        "licence": "CC BY-SA 4.0",
        "licence_url": "https://creativecommons.org/licenses/by-sa/4.0",
        "width": 4000,
        "height": 3000,
        "read_at": READ,
    }
    return OpenPictureRecord.model_validate(values | changes)


def flickr(**changes: Any) -> OpenPictureRecord:
    values: dict[str, Any] = {
        "site": FLICKR,
        "page_url": RACK_PAGE,
        "file_url": RACK_FILE,
        "fetch_url": RACK_FILE,
        "record_url": "https://www.flickr.com/services/oembed/?url=https%3A%2F%2Fflic.kr%2Fp%2Fw3wBs&format=json",
        "title": "on the drying rack, sanganer",
        "author": "nevil zaveri",
        "licence": "CC BY 2.0",
        "licence_url": "https://creativecommons.org/licenses/by/2.0/",
        "width": 375,
        "height": 500,
        "read_at": READ,
    }
    return OpenPictureRecord.model_validate(values | changes)


@dataclass
class Pages:
    records: dict[str, OpenPictureRecord]

    async def record(self, link: OpenLink) -> OpenPictureRecord:
        return self.records[link.key]


@dataclass
class Files:
    data: dict[str, bytes]
    asked: list[str] = field(default_factory=list)

    async def fetch_picture(self, url: str) -> FetchedPicture:
        self.asked.append(url)
        return FetchedPicture(url=url, final_url=url, content_type="image/png", data=self.data[url])


def tools(pages: dict[str, OpenPictureRecord], files: Files) -> OpenTools:
    return OpenTools(
        pages=Pages(pages),
        fetcher=files,
        screen=screen_tools(),
        objects=cast(Any, FakeObjects()),
        now=NOW,
    )


def given(position: int, page_url: str, **target: Any) -> OpenGiven:
    shown = BatchPicture(
        caption="A printer presses a carved block onto cloth",
        alt_text="Hands pressing a wooden block on cotton",
        claim_ids=[FACT],
        **target,
    )
    return OpenGiven(position, page_url, shown)


BLOCK_KEY = "File:Printing with Hand Carved Block.jpg"
RACK_KEY = "339988080"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in seeded_session():
        yield opened


@pytest.fixture
async def people(session: AsyncSession) -> People:
    return await people_in(session)


async def place(session: AsyncSession, user: User, chosen: list[OpenGiven], kit: OpenTools) -> Any:
    return await place_open_pictures(session, user, OpenPlacing(craft_slug=SLUG, pictures=chosen), tools=kit)


async def placed_block(session: AsyncSession, user: User) -> Any:
    files = Files({BLOCK_FETCH: picture(1200, 900, seed=61)})
    placed = await place(
        session, user, [given(1, BLOCK_PAGE, stage_id=STAGE)], tools({BLOCK_KEY: commons()}, files)
    )
    assert files.asked == [BLOCK_FETCH]
    return placed


async def test_a_researcher_s_open_picture_waits_for_review_and_comes_back_with_a_thumbnail(
    session: AsyncSession, people: People
) -> None:
    placed = await placed_block(session, people.researcher)
    (shown,) = placed.pictures
    assert (placed.given, shown.status, shown.label) == (1, "PENDING", "Open-licence picture")
    assert shown.open_source is not None and shown.open_source.credit == BLOCK_CREDIT
    assert shown.plate == f"{SLUG.lower()}/pictures/contributed-{shown.contribution_id.hex[:12]}"
    (small,) = placed.thumbnails
    assert (small.position, small.credit, Image.open(io.BytesIO(small.data)).size) == (
        1,
        BLOCK_CREDIT,
        (320, 240),
    )


async def test_an_open_picture_is_filed_with_its_licence_evidence_which_the_review_queue_shows(
    session: AsyncSession, people: People
) -> None:
    (shown,) = (await placed_block(session, people.researcher)).pictures
    row = await session.get(ImageContribution, shown.contribution_id)
    assert row is not None and (row.origin, row.stageId, row.claimIds, row.rightsConfirmedAt) == (
        "OPEN_LICENCE",
        STAGE,
        [FACT],
        READ,
    )
    stored = await session.get(OpenPicture, row.id)
    assert stored is not None and (stored.pageUrl, stored.licence, stored.author, stored.credit) == (
        BLOCK_PAGE,
        "CC BY-SA 4.0",
        "Ketayun Katz",
        BLOCK_CREDIT,
    )
    (view,) = await images.views(session, await images.queue(session, "PENDING"), objects=None, now=NOW)
    assert view.open_source is not None and (view.open_source.record_url, view.open_source.licence_url) == (
        commons().record_url,
        "https://creativecommons.org/licenses/by-sa/4.0",
    )


async def test_a_professor_s_clear_open_picture_is_shown_at_once_as_its_tier_allows(
    session: AsyncSession, people: People
) -> None:
    files = Files({RACK_FILE: picture(375, 500, seed=62)})
    placed = await place(
        session, people.professor, [given(1, "https://flic.kr/p/w3wBs")], tools({RACK_KEY: flickr()}, files)
    )
    assert [picture.status for picture in placed.pictures] == ["APPROVED"] and placed.approved == 1


async def test_a_licence_or_an_author_that_fails_is_refused_by_name_before_the_file_is_read(
    session: AsyncSession, people: People
) -> None:
    files = Files({})
    records = {
        BLOCK_KEY: commons(licence="CC BY-NC-SA 4.0", licence_url=None),
        RACK_KEY: flickr(author=None),
    }
    chosen = [given(1, BLOCK_PAGE), given(2, RACK_PAGE)]
    placed = await place(session, people.researcher, chosen, tools(records, files))
    assert [picture.refused for picture in placed.pictures] == [
        "Its licence, CC BY-NC-SA 4.0, forbids commercial use (NC); KalaVigyan takes only public domain, CC0, "
        "CC BY or CC BY-SA pictures, any version.",
        "Its page names no author to credit, so it cannot be shown.",
    ]
    assert (placed.given, files.asked) == (0, [])
    assert list(await session.scalars(select(OpenPicture))) == []


async def test_a_picture_already_on_the_page_or_given_twice_is_refused(
    session: AsyncSession, people: People
) -> None:
    same = picture(900, 700, seed=63)
    files = Files({RACK_FILE: same, BLOCK_FETCH: same})
    kit = tools({RACK_KEY: flickr(), BLOCK_KEY: commons()}, files)
    first = await place(session, people.researcher, [given(1, RACK_PAGE), given(2, BLOCK_PAGE)], kit)
    assert [picture.refused for picture in first.pictures] == [
        None,
        "The same picture is given twice in this call",
    ]
    again = await place(session, people.other_researcher, [given(1, "https://flic.kr/p/w3wBs")], kit)
    assert [picture.refused for picture in again.pictures] == [ON_THE_PAGE]


async def test_an_ai_marked_file_is_refused_as_any_contributed_picture_is(
    session: AsyncSession, people: People
) -> None:
    files = Files({BLOCK_FETCH: picture(note=AI_SOURCE)})
    placed = await place(
        session, people.researcher, [given(1, BLOCK_PAGE)], tools({BLOCK_KEY: commons()}, files)
    )
    (refused,) = placed.pictures
    assert refused.refused is not None and "metadata says an AI made it" in refused.refused


async def test_an_unknown_page_is_refused_before_any_source_is_asked(
    session: AsyncSession, people: People
) -> None:
    files = Files({})
    placed = await place(
        session, people.researcher, [given(1, "https://example.org/a.jpg")], tools({}, files)
    )
    (refused,) = placed.pictures
    assert refused.refused is not None and refused.refused.startswith(
        "https://example.org/a.jpg is not a picture's page"
    )
    with pytest.raises(InvalidInput):
        await place_open_pictures(
            session,
            people.researcher,
            OpenPlacing(craft_slug="No-Such-Craft", pictures=[]),
            tools=tools({}, files),
        )


async def test_an_approved_commons_picture_is_drawn_from_commons_and_a_flickr_one_from_its_own_copy_each_credited_with_a_link(
    session: AsyncSession, people: People
) -> None:
    files = Files({BLOCK_FETCH: picture(1200, 900, seed=64), RACK_FILE: picture(375, 500, seed=65)})
    kit = tools({BLOCK_KEY: commons(), RACK_KEY: flickr()}, files)
    placed = await place(
        session, people.professor, [given(1, BLOCK_PAGE, slot="MASTHEAD"), given(2, RACK_PAGE)], kit
    )
    rows = [await session.get(ImageContribution, shown.contribution_id) for shown in placed.pictures]
    assets = [await session.get(MediaAsset, row.assetId) for row in rows if row is not None]
    pairs = [
        (row, asset) for row, asset in zip(rows, assets, strict=True) if row is not None and asset is not None
    ]
    block, rack = await plates_of(session, pairs, contributed_url)
    assert (block.src, block.width, block.height, block.role) == (BLOCK_FILE, 4000, 3000, "HERO")
    assert (rack.src, rack.width, rack.height) == (contributed_url(pairs[1][0].id), 375, 500)
    assert (block.credit, block.credit_url, rack.credit, rack.credit_url) == (
        BLOCK_CREDIT,
        BLOCK_PAGE,
        RACK_CREDIT,
        RACK_PAGE,
    )
    built = plate_spec(block, None, 0)
    assert built is not None
    spec, units = built
    credit = units[spec["figure"]["credit"]]
    assert credit.nodes == [
        "Photo: ",
        {
            "m": "link",
            "href": BLOCK_PAGE,
            "rel": "noopener",
            "target": "_blank",
            "c": [BLOCK_CREDIT.removeprefix("Photo: ")],
        },
    ]
