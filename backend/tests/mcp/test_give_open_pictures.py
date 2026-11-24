import base64
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import pytest

from app.api import mcp_picture_tools
from app.api.mcp_picture_texts import OPEN_STEP
from app.api.mcp_tools import ToolContext, answer
from app.research.image_contributions_give import GivenPicture, GivenPictures
from app.research.image_screens import ScreenSummary, ScreenTools
from app.research.open_pictures import COMMONS, OpenSource
from app.research.upload_links import SlotCraft
from app.services.open_pictures import OpenPlacing, PlacedPictures, Thumbnail
from app.services.upload_links_give import Giving

from .test_picture_uploads import DECLARATION, WORDS, context

FACT = uuid.UUID(int=31)
MADE = uuid.UUID(int=32)
PAGE = "https://commons.wikimedia.org/wiki/File:Printing_with_Hand_Carved_Block.jpg"
CREDIT = "Photo: Ketayun Katz, CC BY-SA 4.0, via Wikimedia Commons"
THUMBNAIL = b"\xff\xd8\xff\xe0small-jpeg"
CRAFT = SlotCraft(slug="Sanganeri-Hand-Block-Printing", name="Sanganeri Hand Block Printing")
SOURCE = OpenSource(
    site=COMMONS,
    page_url=PAGE,
    file_url="https://upload.wikimedia.org/wikipedia/commons/3/3c/Printing_with_Hand_Carved_Block.jpg",
    record_url="https://commons.wikimedia.org/w/api.php?action=query",
    title="Printing with Hand Carved Block",
    author="Ketayun Katz",
    licence="CC BY-SA 4.0",
    licence_url="https://creativecommons.org/licenses/by-sa/4.0",
    credit=CREDIT,
    width=4000,
    height=3000,
    read_at=datetime(2026, 11, 24, 9, 30, tzinfo=UTC),
)
LABEL = "sanganeri-hand-block-printing/pictures/contributed-000000000000"
CONFIRMED = "Yes, I drew it myself and the Centre may publish it without my name."


@pytest.fixture
def placed(monkeypatch: pytest.MonkeyPatch) -> list[OpenPlacing]:
    seen: list[OpenPlacing] = []

    async def place(session: Any, user: Any, placing: OpenPlacing, *, tools: Any) -> PlacedPictures:
        seen.append(placing)
        (first, *rest) = placing.pictures
        shown = GivenPicture(
            position=first.position,
            contribution_id=MADE,
            status="PENDING",
            label="Open-licence picture",
            mime="image/jpeg",
            width=1920,
            height=1440,
            screen=ScreenSummary(verdict="CLEAR", flags=[], reasons=[]),
            open_source=SOURCE,
            plate=LABEL,
        )
        refused = [
            GivenPicture(position=other.position, refused="Its licence, CC BY-NC 2.0, ...") for other in rest
        ]
        return PlacedPictures(
            craft=CRAFT,
            pictures=[shown, *refused],
            thumbnails=[Thumbnail(position=first.position, credit=CREDIT, data=THUMBNAIL)],
            given=1,
            approved=0,
        )

    @asynccontextmanager
    async def opened() -> AsyncIterator[Any]:
        yield object()

    monkeypatch.setattr(mcp_picture_tools, "place_open_pictures", place)
    monkeypatch.setattr(mcp_picture_tools, "open_picture_reader", opened)
    monkeypatch.setattr(mcp_picture_tools, "picture_fetcher", opened)
    monkeypatch.setattr(mcp_picture_tools, "media_bucket", lambda: "bucket")
    monkeypatch.setattr(mcp_picture_tools, "picture_screen_tools", lambda: ScreenTools(vision=None))
    return seen


async def call(arguments: dict[str, Any], tool_context: ToolContext) -> dict[str, Any]:
    message = {
        "jsonrpc": "2.0",
        "id": 11,
        "method": "tools/call",
        "params": {"name": "give_pictures", "arguments": arguments},
    }
    reply = await answer(message, tool_context)
    assert reply is not None and "result" in reply, reply
    return reply["result"]


def open_picture(**changes: Any) -> dict[str, Any]:
    picture = {"page_url": PAGE, "slot": "MASTHEAD", "claim_ids": [str(FACT)], **WORDS} | changes
    return {key: value for key, value in picture.items() if value is not None}


async def test_an_open_picture_needs_no_declaration_and_comes_back_with_its_credit_and_a_thumbnail(
    placed: list[OpenPlacing],
) -> None:
    result = await call({"craft_slug": CRAFT.slug, "pictures": [open_picture()]}, context())
    shown = result["structuredContent"]
    (picture,) = shown["pictures"]
    assert (shown["given"], shown["refused"], shown["declarationId"], picture["plate"]) == (1, 0, None, LABEL)
    assert picture["openSource"]["credit"] == CREDIT and picture["openSource"]["pageUrl"] == PAGE
    assert OPEN_STEP in shown["nextStep"] and shown["craft"]["slug"] == CRAFT.slug
    text, caption, image = result["content"]
    assert text["type"] == "text" and caption == {"type": "text", "text": f"Picture 1: {CREDIT}"}
    assert image == {
        "type": "image",
        "data": base64.b64encode(THUMBNAIL).decode("ascii"),
        "mimeType": "image/jpeg",
    }
    (placing,) = placed
    (given,) = placing.pictures
    assert (placing.craft_slug, given.position, given.page_url, given.refused) == (CRAFT.slug, 1, PAGE, None)
    assert (given.picture.slot, given.picture.claim_ids, given.picture.caption) == (
        "MASTHEAD",
        [FACT],
        WORDS["caption"],
    )


async def test_a_refused_open_picture_says_why_and_shows_no_thumbnail_of_it(
    placed: list[OpenPlacing],
) -> None:
    pictures = [open_picture(), open_picture(page_url="https://flic.kr/p/w3wBs", slot=None)]
    result = await call({"craft_slug": CRAFT.slug, "pictures": pictures}, context())
    shown = result["structuredContent"]
    assert (shown["given"], shown["refused"]) == (1, 1)
    assert [picture["refused"] for picture in shown["pictures"]] == [None, "Its licence, CC BY-NC 2.0, ..."]
    assert [item["type"] for item in result["content"]] == ["text", "text", "image"]


async def test_open_and_declared_pictures_keep_their_positions_in_one_reply(
    placed: list[OpenPlacing], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def give(session: Any, user: Any, giving: Giving, *, handing: Any) -> GivenPictures:
        return GivenPictures(
            craft=CRAFT,
            declaration_id=uuid.UUID(int=88),
            given=1,
            refused=0,
            pictures=[GivenPicture(position=2, contribution_id=uuid.UUID(int=89), status="PENDING")],
            next_step="A picture waits for an Admin's review.",
        )

    monkeypatch.setattr(mcp_picture_tools, "give_pictures", give)
    drawn = {"image_base64": base64.b64encode(b"\x89PNG\r\n\x1a\nbytes").decode("ascii"), **WORDS}
    arguments = {
        "craft_slug": CRAFT.slug,
        "declaration": DECLARATION,
        "confirmation": CONFIRMED,
        "pictures": [open_picture(), drawn],
    }
    shown = (await call(arguments, context()))["structuredContent"]
    assert [picture["position"] for picture in shown["pictures"]] == [1, 2]
    assert (shown["given"], shown["declarationId"]) == (2, str(uuid.UUID(int=88)))
    assert len(placed[0].pictures) == 1 and placed[0].pictures[0].position == 1


@pytest.mark.parametrize(
    ("changes", "says"),
    [
        ({"claim_ids": None}, "names the facts it shows"),
        ({"prompt": "An indigo vat"}, "carries no prompt"),
        ({"image_url": "https://files.example.org/a.png"}, "exactly one of them"),
        ({"caption": None}, "caption and alt_text"),
        ({"page_url": "http://commons.wikimedia.org/wiki/File:A.jpg"}, "page_url"),
    ],
)
async def test_an_open_picture_names_its_facts_its_words_and_one_page(
    placed: list[OpenPlacing], changes: dict[str, Any], says: str
) -> None:
    result = await call({"craft_slug": CRAFT.slug, "pictures": [open_picture(**changes)]}, context())
    assert result["isError"] is True and says in result["content"][0]["text"], result
    assert placed == []


async def test_a_spent_upload_allowance_refuses_an_open_picture_before_its_page_is_read(
    placed: list[OpenPlacing], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def spent(kind: str, user: Any) -> Any:
        return type("Spent", (), {"message": "spent"})()

    monkeypatch.setattr(mcp_picture_tools, "spent_limit", spent)
    await call({"craft_slug": CRAFT.slug, "pictures": [open_picture()]}, context())
    assert placed[0].pictures[0].refused == "spent"


async def test_the_listed_tool_offers_the_page_link_and_names_the_licences_it_takes() -> None:
    reply = await answer({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, context(None))
    assert reply is not None
    (listed,) = [tool for tool in reply["result"]["tools"] if tool["name"] == "give_pictures"]
    assert "page_url" in listed["inputSchema"]["$defs"]["GivenOrUploaded"]["properties"]
    for named in ("Wikimedia Commons", "Openverse", "Flickr", "CC BY-SA", "thumbnail"):
        assert named in listed["description"], named
