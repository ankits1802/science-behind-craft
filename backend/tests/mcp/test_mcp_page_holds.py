import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from app.api import mcp_page_tools
from app.models import PageDraft, User
from app.research.page_proposals import PageBundle, PageHeld, PageProposalResult, PageSubject, PartReport

from ..research.general_spec_fixtures import TABLE
from .test_mcp_page_tools import COMPONENT, SITE, SUBJECT, UNITS, call, context

HOLD = uuid.UUID("0e000000-0000-4000-8000-0000000000a1")
EXPIRES = datetime(2026, 11, 27, 9, tzinfo=UTC)
CONFIRM_URL = f"{SITE}/contributions/pages/{HOLD}"
DELIVERED = {"proposal": COMPONENT | {"spec": TABLE, "units": UNITS}}
WHOLE = {"subject": SUBJECT, "components": [DELIVERED], "layout": {"base_version": 0, "entries": []}}
BORROWED = "shared/chemistry/alizarin-model is borrowed from the shared library"


def held(bundle: PageBundle) -> PageProposalResult:
    return PageProposalResult(
        subject=PageSubject(kind="craft", slug="Kutch-Ajrakh"),
        page_url=f"{SITE}/crafts/Kutch-Ajrakh",
        accepted=0,
        refused=0,
        parts=[],
        message="Held for one confirmation.",
        held=PageHeld(id=HOLD, confirm_url=CONFIRM_URL, expires_at=EXPIRES),
    )


@pytest.fixture
def seen(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[Any]]:
    found: dict[str, list[Any]] = {"proposed": [], "held": [], "asked": []}

    async def page_proposed(session: Any, bundle: PageBundle, user: User, **_: Any) -> PageProposalResult:
        found["proposed"].append(bundle)
        return held(bundle).model_copy(update={"held": None, "accepted": 2})

    async def hold_page(
        session: Any, user: User, bundle: PageBundle, draft: PageDraft | None, place: Any
    ) -> PageProposalResult:
        found["held"].append((bundle, place.client_name))
        return held(bundle)

    async def nothing_refused(session: Any, bundle: PageBundle, *, site: str) -> None:
        return None

    monkeypatch.setattr(mcp_page_tools, "page_proposed", page_proposed)
    monkeypatch.setattr(mcp_page_tools.page_holds, "hold_page", hold_page)
    monkeypatch.setattr(mcp_page_tools, "held_refusal", nothing_refused)
    return found


def publishing(monkeypatch: pytest.MonkeyPatch, seen: dict[str, list[Any]], *, at_once: bool) -> None:
    async def publishes_at_once(session: Any, user_id: uuid.UUID, origin: str) -> bool:
        seen["asked"].append(origin)
        return at_once

    monkeypatch.setattr(mcp_page_tools, "publishes_at_once", publishes_at_once)


async def test_a_whole_page_from_an_account_that_publishes_at_once_is_held_and_nothing_proposed(
    monkeypatch: pytest.MonkeyPatch, seen: dict[str, list[Any]]
) -> None:
    publishing(monkeypatch, seen, at_once=True)
    reply = await call("propose_page", {"bundle": WHOLE}, context(number=71))
    content = reply["structuredContent"]
    assert reply["isError"] is False and seen["proposed"] == [] and seen["asked"] == ["AGENT"]
    assert content["held"] == {
        "id": str(HOLD),
        "confirmUrl": CONFIRM_URL,
        "expiresAt": "2026-11-27T09:00:00Z",
    }
    assert (content["accepted"], content["refused"], content["parts"]) == (0, 0, [])
    assert "confirm_url" in content["nextStep"] and "press" in content["nextStep"]


async def test_a_whole_page_from_an_account_that_waits_for_review_is_proposed_as_before(
    monkeypatch: pytest.MonkeyPatch, seen: dict[str, list[Any]]
) -> None:
    publishing(monkeypatch, seen, at_once=False)
    reply = await call("propose_page", {"bundle": WHOLE}, context(number=72))
    assert reply["isError"] is False and seen["held"] == [] and len(seen["proposed"]) == 1
    assert reply["structuredContent"]["accepted"] == 2 and "held" not in reply["structuredContent"]


async def test_a_single_component_keeps_its_tier_and_is_never_held(
    monkeypatch: pytest.MonkeyPatch, seen: dict[str, list[Any]]
) -> None:
    publishing(monkeypatch, seen, at_once=True)
    alone = {"subject": SUBJECT, "components": [DELIVERED]}
    reply = await call("propose_page", {"bundle": alone}, context(number=73))
    assert reply["isError"] is False and seen["asked"] == [] and seen["held"] == []
    assert len(seen["proposed"]) == 1


async def test_a_held_page_that_places_a_component_that_cannot_pass_holds_nothing(
    monkeypatch: pytest.MonkeyPatch, seen: dict[str, list[Any]]
) -> None:
    publishing(monkeypatch, seen, at_once=True)

    async def refused(session: Any, bundle: PageBundle, *, site: str) -> PageProposalResult:
        part = PartReport(part="layout", index=0, outcome="REFUSED", message=BORROWED)
        return held(bundle).model_copy(update={"held": None, "refused": 1, "parts": [part]})

    monkeypatch.setattr(mcp_page_tools, "held_refusal", refused)
    reply = await call("propose_page", {"bundle": WHOLE}, context(number=74))
    content = reply["structuredContent"]
    assert seen["held"] == [] and seen["proposed"] == [] and "held" not in content
    assert [(part["part"], part["outcome"], part["message"]) for part in content["parts"]] == [
        ("layout", "REFUSED", BORROWED)
    ]
    assert (
        content["nextStep"].startswith("Fix each refused part") and "nothing was held" in content["nextStep"]
    )
