import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.api.mcp_input import Answer
from app.api.mcp_staged_confirm import chosen_positions
from app.api.mcp_tools import TOOLS
from app.models import StagedReview
from app.services import staged_review_summary

from .modern_client import TASKS, error_of, legacy, result_of, tool_call
from .staged_confirm_desk import (
    ADMIN_ID,
    BATCH_ID,
    GRANT_ID,
    LABELS,
    NOTE,
    OTHER_ID,
    PROPOSAL,
    REVIEW,
    STAGE,
    Desk,
    context,
    person,
    staging,
)

ALL = {"confirm": {"action": "accept", "content": {"choice": "all"}}}
NONE_OF_IT = "chose to confirm none of it"


@pytest.fixture
def desk(monkeypatch: pytest.MonkeyPatch) -> Desk:
    held = Desk()
    held.patch(monkeypatch)
    return held


async def answered(desk: Desk, first: dict[str, Any], responses: dict[str, Any]) -> dict[str, Any]:
    message = staging(inputResponses=responses, requestState=first["requestState"])
    return await result_of(message, context(desk))


async def asked(desk: Desk) -> dict[str, Any]:
    first = await result_of(staging(), context(desk))
    assert first["resultType"] == "input_required" and isinstance(first["requestState"], str)
    return first


def test_only_stage_reviews_asks_after_it_runs() -> None:
    assert {name for name, tool in TOOLS.items() if tool.after is not None} == {"stage_reviews"}


async def test_a_client_that_shows_forms_asks_the_person_what_each_staged_item_will_do(desk: Desk) -> None:
    first = await asked(desk)
    request = first["inputRequests"]["confirm"]
    assert request["method"] == "elicitation/create" and request["params"]["mode"] == "form"
    message = request["params"]["message"]
    assert message.startswith("Your AI client Claude staged 3 review decisions for you. Nothing is published")
    assert f"What you leave waits on {REVIEW} for 3 days." in message
    assert "\n1. Approve “An indigo vat turns blue at its surface.”: it is published for readers." in message
    assert "\n2. Reject “Lime keeps the indigo vat alkaline.”: it is not published" in message
    assert (
        "It touches the chapter The chemistry, and the component Black and red from one dye bath." in message
    )
    assert f"for reviewers only: {REVIEW}?proposal={PROPOSAL}" in message
    schema = request["params"]["requestedSchema"]
    assert list(schema["properties"]) == ["choice", "item_1", "item_2", "item_3"]
    assert schema["required"] == ["choice"]
    assert [option["const"] for option in schema["properties"]["choice"]["oneOf"]] == ["all", "some", "none"]
    ticks = [schema["properties"][f"item_{number}"] for number in (1, 2, 3)]
    assert [tick["default"] for tick in ticks] == [False, False, False]
    assert ticks[0]["title"] == f"1. {LABELS[0]}"
    assert (desk.staged, desk.confirmed, desk.finished) == (1, [], 0)


async def test_confirming_all_in_the_form_confirms_the_batch_without_staging_it_again(desk: Desk) -> None:
    reply = await answered(desk, await asked(desk), ALL)
    assert reply["isError"] is False and desk.confirmed == [frozenset({0, 1, 2})]
    assert (desk.staged, desk.finished) == (1, 1)
    content = reply["structuredContent"]
    assert content["published"] is True and content["batchId"] == str(BATCH_ID)
    assert [item["state"] for item in content["batch"]["items"]] == ["APPLIED", "APPLIED", "APPLIED"]
    assert content["batch"]["refresh"] == NOTE
    assert content["message"] == (
        "The person confirmed 3 of 3 staged decisions in their client: 3 applied, 0 refused by the checks, "
        f"the rest left out of the batch. {NOTE}"
    )


async def test_a_partial_confirmation_applies_only_the_ticked_items(desk: Desk) -> None:
    ticked = {"choice": "some", "item_1": True, "item_2": False, "item_3": True}
    reply = await answered(desk, await asked(desk), {"confirm": {"action": "accept", "content": ticked}})
    assert reply["isError"] is False and desk.confirmed == [frozenset({0, 2})]
    content = reply["structuredContent"]
    assert [item["state"] for item in content["batch"]["items"]] == ["APPLIED", "SKIPPED", "APPLIED"]
    assert content["message"].startswith("The person confirmed 2 of 3 staged decisions in their client")


@pytest.mark.parametrize(
    ("responses", "how"),
    [
        ({"confirm": {"action": "decline"}}, "declined to confirm"),
        ({"confirm": {"action": "cancel"}}, "declined to confirm"),
        ({"confirm": {"action": "accept", "content": {"choice": "none", "item_1": True}}}, NONE_OF_IT),
        ({"confirm": {"action": "accept", "content": {"choice": "some"}}}, "ticked none of it"),
        ({"confirm": {"action": "accept", "content": {"choice": "every one"}}}, NONE_OF_IT),
        ({}, "gave no answer"),
    ],
)
async def test_a_declined_or_empty_answer_leaves_the_batch_waiting_on_the_review_page(
    desk: Desk, responses: dict[str, Any], how: str
) -> None:
    reply = await answered(desk, await asked(desk), responses)
    assert reply["isError"] is False and desk.confirmed == [] and desk.finished == 0
    content = reply["structuredContent"]
    assert "batch" not in content and content["published"] is False and content["batchId"] == str(BATCH_ID)
    assert content["message"] == (
        f"The person {how} in their client, so nothing is published yet: the staged batch waits until an Admin "
        f"confirms it on {REVIEW}, within 3 days."
    )
    assert desk.batch is not None and desk.batch.status == "OPEN"


@pytest.mark.parametrize(
    "message",
    [
        legacy("tools/call", tool_call("stage_reviews", STAGE)),
        staging(capabilities=TASKS),
        staging(capabilities={}),
    ],
)
async def test_a_client_without_form_elicitation_stages_as_before_and_is_never_asked(
    desk: Desk, message: dict[str, Any]
) -> None:
    reply = await result_of(message, context(desk))
    assert "inputRequests" not in reply and reply["isError"] is False
    content = reply["structuredContent"]
    waiting = f"Nothing is published yet. 3 decisions wait in a staged batch until an Admin confirms them on {REVIEW}"
    assert content["message"].startswith(waiting)
    assert (desk.staged, desk.confirmed) == (1, [])


@pytest.mark.parametrize(
    ("scopes", "role", "said"),
    [
        (("read", "contribute"), "ADMIN", "review scope"),
        (("read", "review"), "PROFESSOR", "Admin and Master Admin"),
    ],
)
async def test_a_person_without_the_review_scope_or_rank_never_gets_the_form(
    desk: Desk, scopes: tuple[str, ...], role: str, said: str
) -> None:
    reply = await result_of(staging(), context(desk, scopes=scopes, user=person(role=role)))
    assert "inputRequests" not in reply and reply["isError"] is True and said in reply["content"][0]["text"]
    assert (desk.staged, desk.confirmed) == (0, [])


@pytest.mark.parametrize(
    "smuggled",
    [{"inputResponses": ALL}, {"requestState": "made-up"}, {"confirm": "all"}, {"choice": "all"}],
)
async def test_an_answer_carried_in_the_tool_s_arguments_is_refused_and_confirms_nothing(
    desk: Desk, smuggled: dict[str, Any]
) -> None:
    reply = await result_of(staging(STAGE | smuggled), context(desk))
    assert reply["isError"] is True and "inputRequests" not in reply
    assert (desk.staged, desk.confirmed) == (0, [])


async def test_an_answer_without_the_server_s_request_state_is_ignored_and_the_person_is_asked(
    desk: Desk,
) -> None:
    reply = await result_of(staging(inputResponses=ALL), context(desk))
    assert reply["resultType"] == "input_required" and desk.confirmed == []


async def test_the_form_s_answer_is_taken_only_from_the_client_it_was_asked_of(desk: Desk) -> None:
    first = await asked(desk)
    state = first["requestState"]
    tampered = state[:-3] + ("AAA" if not state.endswith("AAA") else "BBB")
    refused = [
        (staging(capabilities=TASKS, inputResponses=ALL, requestState=state), context(desk)),
        (staging(inputResponses=ALL, requestState=state), context(desk, user=person(OTHER_ID))),
        (
            staging({"decisions": STAGE["decisions"][:1]}, inputResponses=ALL, requestState=state),
            context(desk),
        ),
        (staging(inputResponses=ALL, requestState=tampered), context(desk)),
    ]
    for message, where in refused:
        assert (await error_of(message, where))["code"] == -32602
    assert desk.confirmed == []


async def test_an_answer_from_another_client_of_the_same_person_confirms_nothing(desk: Desk) -> None:
    first = await asked(desk)
    message = staging(inputResponses=ALL, requestState=first["requestState"])
    reply = await result_of(message, context(desk, grant=uuid.uuid4()))
    assert reply["isError"] is True and "no longer open to this account" in reply["content"][0]["text"]
    assert desk.confirmed == []


@pytest.mark.parametrize(("proposer", "status"), [(OTHER_ID, "OPEN"), (ADMIN_ID, "CONFIRMED")])
async def test_a_form_is_asked_only_of_the_person_whose_ai_staged_a_batch_still_open(
    desk: Desk, proposer: uuid.UUID, status: str
) -> None:
    desk.proposer, desk.status = proposer, status
    reply = await result_of(staging(), context(desk))
    assert reply["resultType"] == "complete" and "inputRequests" not in reply
    assert reply["structuredContent"]["message"].startswith("Nothing is published yet.")
    assert (desk.staged, desk.confirmed) == (1, [])


def test_the_answer_names_the_positions_it_confirms() -> None:
    def said(action: str, **content: Any) -> Answer:
        return Answer(action=action, content=content)

    assert chosen_positions(None, 3) == frozenset()
    assert chosen_positions(said("decline", choice="all"), 3) == frozenset()
    assert chosen_positions(said("accept", choice="all"), 3) == frozenset({0, 1, 2})
    assert chosen_positions(said("accept", choice="some", item_2=True, item_3="true"), 3) == frozenset({1})
    assert chosen_positions(said("accept", choice="none", item_1=True), 3) == frozenset()
    assert chosen_positions(said("accept", choice="ALL"), 3) == frozenset()


async def test_an_open_batch_is_its_own_proposer_s_through_the_client_that_staged_it() -> None:
    now = datetime.now(UTC)
    held = Desk()
    held.batch = StagedReview(
        id=BATCH_ID,
        proposerId=ADMIN_ID,
        grantId=GRANT_ID,
        clientName="Claude",
        status="OPEN",
        createdAt=now,
        expiresAt=now + timedelta(days=3),
    )
    own = staged_review_summary.own_open_batch
    session: Any = held
    assert await own(session, BATCH_ID, person(), grant_id=GRANT_ID, now=now) is held.batch
    assert await own(session, BATCH_ID, person(OTHER_ID), grant_id=GRANT_ID, now=now) is None
    assert await own(session, BATCH_ID, person(), grant_id=uuid.uuid4(), now=now) is None
    assert await own(session, uuid.uuid4(), person(), grant_id=GRANT_ID, now=now) is None
    assert await own(session, BATCH_ID, person(), grant_id=GRANT_ID, now=now + timedelta(days=4)) is None
    held.batch.status = "CONFIRMED"
    assert await own(session, BATCH_ID, person(), grant_id=GRANT_ID, now=now) is None
