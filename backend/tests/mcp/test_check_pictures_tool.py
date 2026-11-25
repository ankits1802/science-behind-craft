import base64
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from app.api import mcp_check_tools
from app.api.mcp_check_tools import CheckPictures
from app.api.mcp_tool_base import OPEN_WRITES, PICTURES, ToolContext
from app.api.mcp_tools import TOOLS, answer
from app.api.proposal_limits import Spent
from app.core.mcp_scopes import CONTRIBUTE_SCOPE
from app.models import User
from app.research.images import media_ref_of
from app.research.picture_checks import PictureToCheck
from app.services.craft_resolver import CraftIndexStore
from app.services.export_pictures import Picture
from app.services.picture_check_batches import CheckBatch, ShownCheck, check_picture_url
from app.services.picture_check_links import FETCHED_PREFIXES

from ..images.fakes import candidate

SITE = "https://kalavigyan.example"
LINK = uuid.UUID("5d1f0000-0000-4000-8000-000000000001")
FACT = uuid.UUID("5d1f0000-0000-4000-8000-000000000002")
JPEG = b"\xff\xd8\xff\xe0 a picture"
NOW = datetime(2026, 11, 25, 9, tzinfo=UTC)


class Session:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None

    @asynccontextmanager
    async def begin_nested(self) -> AsyncIterator[None]:
        yield None


class Standing:
    tasks_held_max = 5


def context(role: str = "RESEARCHER") -> ToolContext:
    user = User(id=uuid.UUID(int=9), name="Checker", email="checker@example.org", role=role)
    return ToolContext(
        session=Session(),  # type: ignore[arg-type]
        index=CraftIndexStore(),
        site=SITE,
        user=user,
        scopes=frozenset({CONTRIBUTE_SCOPE}),
    )


async def called(arguments: dict[str, Any], role: str = "RESEARCHER") -> dict[str, Any]:
    message = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "check_pictures"}}
    message["params"]["arguments"] = arguments
    reply = await answer(message, context(role))
    assert reply is not None and "result" in reply, reply
    return reply["result"]


@pytest.fixture
def quiet(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    recorded: list[Any] = []

    async def trusted(*_: Any) -> bool:
        return False

    async def standing(*_: Any) -> Standing:
        return Standing()

    async def held(*_: Any, **__: Any) -> int:
        return 0

    async def record(*arguments: Any, **options: Any) -> Any:
        recorded.append((arguments, options))
        raise AssertionError("a verdict over the hour's allowance is never recorded")

    monkeypatch.setattr(mcp_check_tools, "publishes_at_once", trusted)
    monkeypatch.setattr(mcp_check_tools, "account_standing", standing)
    monkeypatch.setattr(mcp_check_tools, "holding", held)
    monkeypatch.setattr(mcp_check_tools, "record_verdict", record)
    return recorded


def test_the_tool_sits_with_give_pictures_and_writes_with_a_contributor_s_scope() -> None:
    tool = TOOLS["check_pictures"]
    assert (tool.group, tool.scope, dict(tool.annotations)) == (PICTURES, CONTRIBUTE_SCOPE, dict(OPEN_WRITES))
    assert tool.commits and "outputSchema" not in tool.listed()
    verdict = tool.listed()["inputSchema"]["properties"]["verdicts"]
    assert verdict["maxItems"] == 10


@pytest.mark.parametrize(
    "arguments",
    [
        {"verdicts": [{"link_id": str(LINK), "verdict": "shows", "reason": "a printed cloth"}]},
        {"verdicts": [{"link_id": str(LINK), "verdict": "maybe", "reason": "A block-printed cloth drying"}]},
        {"take": 11},
        {"take": -1},
    ],
)
def test_a_verdict_without_a_reason_of_twelve_characters_or_a_wrong_word_is_refused(
    arguments: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError):
        CheckPictures.model_validate(arguments)


def test_a_verdict_with_what_the_picture_shows_is_read() -> None:
    reason = "A dyer lifting cloth printed in Ajrakh from a vat"
    read = CheckPictures.model_validate(
        {"verdicts": [{"link_id": str(LINK), "verdict": "does_not_show", "reason": reason}], "take": 0}
    )
    assert (read.verdicts[0].verdict, read.verdicts[0].reason, read.take) == ("does_not_show", reason, 0)


async def test_an_account_without_the_work_capability_is_refused(quiet: list[Any]) -> None:
    result = await called({"take": 0}, role="STUDENT")
    assert result["isError"] is True
    assert "check_pictures needs an account of Researcher or above" in result["content"][0]["text"]


async def test_a_verdict_over_the_hour_s_allowance_is_refused_and_never_recorded(
    quiet: list[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def spent(*_: Any) -> Spent:
        return Spent(message="This account made 60 picture checks this hour.", wait_seconds=60)

    monkeypatch.setattr(mcp_check_tools, "spent_limit", spent)
    reason = "A block-printed cloth drying in the sun"
    result = await called(
        {"verdicts": [{"link_id": str(LINK), "verdict": "shows", "reason": reason}], "take": 0}
    )
    assert result["isError"] is False and quiet == []
    (refused,) = result["structuredContent"]["recorded"]
    assert refused == {
        "linkId": str(LINK),
        "state": None,
        "refused": "This account made 60 picture checks this hour.",
    }


async def test_each_picture_of_a_batch_arrives_as_image_content_never_as_a_link(
    quiet: list[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    item = PictureToCheck(
        position=1,
        link_id=LINK,
        fact_id=FACT,
        fact="Ajrakh cloth is printed with a resist of lime and gum.",
        craft=None,
        title="Ajrakh printing in Dhamadka",
        caption="A printer pressing a block on cloth",
        credit="A. Photographer, CC BY-SA 4.0",
        page_url="https://commons.wikimedia.org/wiki/File:Ajrakh.jpg",
        served=4,
        reserved_until=NOW,
    )
    batch = CheckBatch(shown=[ShownCheck(item, Picture(JPEG, 330, 220))], skipped=1, full=False)

    @asynccontextmanager
    async def source() -> AsyncIterator[object]:
        yield object()

    async def taken(*_: Any, **options: Any) -> CheckBatch:
        assert options["take"] == 3
        return batch

    monkeypatch.setattr(mcp_check_tools, "check_source", source)
    monkeypatch.setattr(mcp_check_tools, "take_batch", taken)
    result = await called({"take": 3})
    (picture,) = result["structuredContent"]["pictures"]
    assert (picture["linkId"], picture["served"], result["structuredContent"]["skipped"]) == (str(LINK), 4, 1)
    images = [part for part in result["content"] if part["type"] == "image"]
    assert images == [
        {"type": "image", "data": base64.b64encode(JPEG).decode("ascii"), "mimeType": "image/jpeg"}
    ]
    assert "1 pictures could not be fetched" in result["structuredContent"]["message"]


def test_a_commons_picture_is_looked_at_through_its_330_pixel_thumbnail_on_an_allowed_host() -> None:
    found = candidate("wikimedia_commons", 1, "Ajrakh", licence="CC BY-SA 4.0", author="A")
    media = media_ref_of(found, media_id=LINK, source_id=None).model_copy(
        update={
            "image_url": "https://thumb.wikimedia.org/wikipedia/commons/thumb/4/40/Toys.jpg/960px-Toys.jpg"
        }
    )
    assert (
        check_picture_url(media)
        == "https://upload.wikimedia.org/wikipedia/commons/thumb/4/40/Toys.jpg/330px-Toys.jpg"
    )
    openverse = media.model_copy(update={"image_url": "https://api.openverse.org/v1/images/04c049ef/thumb/"})
    assert check_picture_url(openverse) == "https://api.openverse.org/v1/images/04c049ef/thumb/"
    assert set(FETCHED_PREFIXES) == {
        "https://api.openverse.org/",
        "https://upload.wikimedia.org/",
        "https://thumb.wikimedia.org/wikipedia/commons/thumb/",
    }
