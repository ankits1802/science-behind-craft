import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.api import mcp_page_tools, mcp_questions, mcp_studio_sources
from app.api.mcp_tools import TOOLS, ToolContext
from app.models import PageDraft, User
from app.research.crafts import CraftRef
from app.research.knowledge_api import FoundCraft, FoundCrafts
from app.research.page_proposals import PageBundle, PageProposalResult, PageSubject
from app.services.supplied_sources import Supplied

from ..research.test_page_proposals import COMPONENT, FACT
from .modern_client import FORMS, TASKS, error_of, legacy, modern, result_of, tool_call
from .test_mcp_studio_tools import (
    ACCESS,
    DRAFT_ID,
    IDENTITY,
    PASSAGE,
    context,
    draft_row,
    lookups,
    noop,
    owned,
    supplied_row,
)

__all__ = ["lookups"]

ASKING = {"edit_draft", "propose_page", "supply_source"}
PREVIEW = "https://kalavigyan.example/preview/kvpv_private"
LONG_TEXT = "Alum is printed before the madder bath so that the red fixes only where the mordant lies. " * 4


def asked_call(
    name: str, arguments: dict[str, Any], *, capabilities: dict[str, Any] = FORMS, **extra: Any
) -> dict[str, Any]:
    return modern("tools/call", tool_call(name, arguments, **extra), capabilities=capabilities)


def asking() -> ToolContext:
    return context()


async def asked(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    result = await result_of(asked_call(name, arguments), asking())
    assert result["resultType"] == "input_required" and isinstance(result["requestState"], str)
    assert "ttlMs" not in result
    return result


async def answered(
    name: str, arguments: dict[str, Any], first: dict[str, Any], responses: dict[str, Any]
) -> dict[str, Any]:
    message = asked_call(name, arguments, inputResponses=responses, requestState=first["requestState"])
    return await result_of(message, asking())


def found(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    queries: list[str] = []

    async def find(session: Any, store: Any, query: str, *, site: str) -> FoundCrafts:
        queries.append(query)
        craft = CraftRef(slug="Kutch-Ajrakh", name="Kutch Ajrakh", path="/crafts/Kutch-Ajrakh")
        return FoundCrafts(
            query=query, crafts=[FoundCraft(craft=craft, score=0.9, page_url=f"{site}/crafts/Kutch-Ajrakh")]
        )

    monkeypatch.setattr(mcp_questions.craft_finder, "find_crafts", find)
    return queries


def created(monkeypatch: pytest.MonkeyPatch) -> list[PageSubject]:
    seen: list[PageSubject] = []

    async def create(session: Any, user: User, subject: PageSubject, *, now: datetime) -> PageDraft:
        seen.append(subject)
        return draft_row()

    monkeypatch.setattr(mcp_page_tools.page_drafts, "create_draft", create)
    return seen


def test_only_the_three_decisions_that_are_the_person_s_ask_anything() -> None:
    assert {name for name, tool in TOOLS.items() if tool.asks is not None} == ASKING


async def test_no_other_tool_asks_even_a_client_that_can_be_asked() -> None:
    page = await result_of(asked_call("get_page", {}), asking())
    assert (page["resultType"], page["isError"]) == ("complete", False)


async def test_a_vague_request_asks_which_craft_and_what_the_person_wants_to_give(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = await asked("edit_draft", {})
    (request,) = first["inputRequests"].values()
    assert request["method"] == "elicitation/create" and request["params"]["mode"] == "form"
    schema = request["params"]["requestedSchema"]
    assert set(schema["properties"]) == {"craft", "contribution"} and schema["required"] == [
        "craft",
        "contribution",
    ]
    options = [option["const"] for option in schema["properties"]["contribution"]["oneOf"]]
    assert options == ["page", "facts", "figures", "pictures", "sources"]
    assert request["params"]["message"].startswith("Which craft's page is this for")
    queries, subjects = found(monkeypatch), created(monkeypatch)
    reply = await answered(
        "edit_draft",
        {},
        first,
        {"page": {"action": "accept", "content": {"craft": "ajrakh", "contribution": "figures"}}},
    )
    assert reply["isError"] is False and queries == ["ajrakh"]
    assert subjects == [PageSubject(kind="craft", slug="Kutch-Ajrakh")]
    assert reply["structuredContent"]["notices"][0] == (
        "The person chose Kutch Ajrakh (Kutch-Ajrakh) and wants to contribute figures, maps and other components."
    )


@pytest.mark.parametrize("action", ["decline", "cancel"])
async def test_a_person_who_chooses_no_page_opens_no_draft(
    monkeypatch: pytest.MonkeyPatch, action: str
) -> None:
    subjects = created(monkeypatch)
    first = await asked("edit_draft", {})
    reply = await answered("edit_draft", {}, first, {"page": {"action": action}})
    assert reply["isError"] is True and "chose no page" in reply["content"][0]["text"] and subjects == []


@pytest.mark.parametrize(
    "message",
    [legacy("tools/call", tool_call("edit_draft", {})), asked_call("edit_draft", {}, capabilities=TASKS)],
)
async def test_a_client_that_cannot_be_asked_is_told_to_name_the_page_as_before(
    message: dict[str, Any],
) -> None:
    refused = await result_of(message, asking())
    assert refused["isError"] is True and "one of them" in refused["content"][0]["text"]


async def test_a_named_page_or_draft_is_never_asked_about(monkeypatch: pytest.MonkeyPatch) -> None:
    subjects = created(monkeypatch)
    opened = await result_of(
        asked_call("edit_draft", {"subject": {"kind": "craft", "slug": "Kutch-Ajrakh"}}), asking()
    )
    assert opened["resultType"] == "complete" and subjects == [PageSubject(kind="craft", slug="Kutch-Ajrakh")]


async def test_a_tampered_or_borrowed_request_state_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    first = await asked("edit_draft", {})
    state = first["requestState"]
    tampered = state[:-3] + ("AAA" if not state.endswith("AAA") else "BBB")
    for sent, arguments, user in (
        (tampered, {}, None),
        (state, {"draft_id": str(DRAFT_ID)}, None),
        (
            state,
            {},
            User(
                id=uuid.uuid4(), name="Someone", email="else@example.org", role="RESEARCHER", tokenVersion=0
            ),
        ),
    ):
        tool_context = asking() if user is None else replace(asking(), user=user)
        message = asked_call(
            "edit_draft", arguments, inputResponses={"page": {"action": "decline"}}, requestState=sent
        )
        assert (await error_of(message, tool_context))["code"] == -32602


def proposable(monkeypatch: pytest.MonkeyPatch, *, previewed: bool) -> dict[str, Any]:
    changes = (
        {"previewUrl": PREVIEW, "previewExpiresAt": datetime.now(UTC) + timedelta(hours=6)}
        if previewed
        else {}
    )
    row = draft_row(
        {"facts": [FACT], "components": [{"proposal": COMPONENT, "cites": {"u0006": ["fact:0"]}}]}, **changes
    )
    seen: dict[str, Any] = {}

    async def proposed(
        session: Any, bundle: PageBundle, user: User, *, origin: str, site: str
    ) -> PageProposalResult:
        seen.update(components=len(bundle.components))
        return PageProposalResult(
            subject=bundle.subject,
            page_url=f"{site}/crafts/Kutch-Ajrakh",
            accepted=2,
            refused=0,
            parts=[],
            message="2 of 2.",
        )

    async def reviews_first(session: Any, user_id: uuid.UUID, origin: str) -> bool:
        return False

    monkeypatch.setattr(mcp_page_tools.page_drafts, "own_draft", owned(row))
    monkeypatch.setattr(mcp_page_tools.page_drafts, "record_submission", noop)
    monkeypatch.setattr(mcp_page_tools, "page_proposed", proposed)
    monkeypatch.setattr(mcp_page_tools, "publishes_at_once", reviews_first)
    return seen


async def test_proposing_a_page_asks_the_person_first_and_shows_what_goes_with_its_private_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = proposable(monkeypatch, previewed=True)
    work = {"draft_id": str(DRAFT_ID)}
    first = await asked("propose_page", work)
    said = first["inputRequests"]["send"]["params"]["message"]
    assert "craft Kutch-Ajrakh: 1 facts, 1 components" in said and PREVIEW in said and seen == {}
    kept = await answered(
        "propose_page", work, first, {"send": {"action": "accept", "content": {"send": False}}}
    )
    assert kept["isError"] is True and "chose not to send" in kept["content"][0]["text"] and seen == {}
    sent = await answered(
        "propose_page", work, first, {"send": {"action": "accept", "content": {"send": True}}}
    )
    assert (
        sent["isError"] is False and sent["structuredContent"]["accepted"] == 2 and seen == {"components": 1}
    )


async def test_a_page_with_no_preview_says_so_and_a_client_that_cannot_be_asked_proposes_as_before(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = proposable(monkeypatch, previewed=False)
    first = await asked("propose_page", {"draft_id": str(DRAFT_ID)})
    assert "It has no preview yet." in first["inputRequests"]["send"]["params"]["message"]
    direct = await result_of(
        legacy("tools/call", tool_call("propose_page", {"draft_id": str(DRAFT_ID)})), asking()
    )
    assert direct["isError"] is False and seen == {"components": 1}


def supplying(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    drafts: list[Any] = []

    async def supply(session: Any, user: User, draft: Any, *, lookup: Any, now: datetime) -> Supplied:
        drafts.append(draft)
        return Supplied(row=supplied_row(), slot_token=None)

    monkeypatch.setattr(mcp_studio_sources.supplied_sources, "supply_source", supply)
    return drafts


async def test_a_source_only_the_person_can_open_is_asked_for_its_words(
    monkeypatch: pytest.MonkeyPatch, lookups: list[Any]
) -> None:
    drafts = supplying(monkeypatch)
    source = {"identity": IDENTITY, "access": ACCESS}
    first = await asked("supply_source", source)
    words = first["inputRequests"]["words"]["params"]
    assert IDENTITY["title"] in words["message"] and set(words["requestedSchema"]["properties"]) == {
        "text",
        "locator",
    }
    whole = await answered(
        "supply_source", source, first, {"words": {"action": "accept", "content": {"text": LONG_TEXT}}}
    )
    assert whole["isError"] is False and drafts[-1].text == LONG_TEXT.strip()
    passage = {"text": PASSAGE["text"], "locator": "p. 14"}
    short = await answered(
        "supply_source", source, first, {"words": {"action": "accept", "content": passage}}
    )
    assert short["isError"] is False and drafts[-1].passages[0].locator == "p. 14"
    declined = await answered("supply_source", source, first, {"words": {"action": "decline"}})
    assert declined["isError"] is True and "gave none" in declined["content"][0]["text"] and len(drafts) == 2


async def test_a_source_whose_words_are_given_is_not_asked_about_and_old_clients_are_told_as_before(
    monkeypatch: pytest.MonkeyPatch, lookups: list[Any]
) -> None:
    drafts = supplying(monkeypatch)
    given = await result_of(
        asked_call("supply_source", {"identity": IDENTITY, "access": ACCESS, "passages": [PASSAGE]}), asking()
    )
    assert given["resultType"] == "complete" and given["isError"] is False and len(drafts) == 1
    old = await result_of(
        legacy("tools/call", tool_call("supply_source", {"identity": IDENTITY, "access": ACCESS})), asking()
    )
    assert old["isError"] is True and "one way" in old["content"][0]["text"] and len(drafts) == 1
