from contextlib import asynccontextmanager

import httpx
import pytest

from app.services.portal_craft_reconcile import plan_sync
from app.services.portal_craft_sync import fetch_feeds, run_sync
from tests.portal_sync.fixtures import (
    SYNCED_AT,
    both_portals,
    designer_payload,
    known_state,
    settings,
    signed_transport,
)


class SessionOpened(Exception):
    pass


@asynccontextmanager
async def refuse_session():
    raise SessionOpened
    yield


async def test_fetched_feeds_plan_end_to_end() -> None:
    fetched = await fetch_feeds(settings(), transport=signed_transport(both_portals()))
    assert [(o.portal, o.ok, o.crafts) for o in fetched.outcomes] == [
        ("DESIGNER", True, 4),
        ("FIELD_REPOSITORY", True, 4),
    ]
    plan = plan_sync(fetched.feeds, known_state(), synced_at=SYNCED_AT)
    assert {write.slug for write in plan.crafts if write.insert} == {
        "Dabu-Print",
        "Dabu-Printing",
        "Sanjhi",
        "Pattachitra-Odisha",
    }


async def test_a_failing_portal_is_reported_and_the_other_still_syncs() -> None:
    transport = signed_transport({"designer.example.com": designer_payload()})
    fetched = await fetch_feeds(settings(), transport=transport)
    assert [feed.portal for feed in fetched.feeds] == ["DESIGNER"]
    failure = fetched.outcomes[1]
    assert (failure.portal, failure.ok, failure.crafts) == ("FIELD_REPOSITORY", False, 0)
    assert failure.error == "ExternalFailure: FIELD_REPOSITORY craft feed answered 404"
    with pytest.raises(SessionOpened):
        await run_sync(settings(), open_session=refuse_session, synced_at=SYNCED_AT, transport=transport)


async def test_no_feed_means_no_database_work_and_a_failed_report() -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    report = await run_sync(
        settings(), open_session=refuse_session, synced_at=SYNCED_AT, transport=httpx.MockTransport(down)
    )
    assert report.ok is False
    assert report.counts is None
    assert [(p["portal"], p["ok"]) for p in report.as_dict()["portals"]] == [
        ("DESIGNER", False),
        ("FIELD_REPOSITORY", False),
    ]


async def test_unconfigured_portals_are_reported_by_setting_name() -> None:
    report = await run_sync(
        settings(DESIGNER_PORTAL_API_URL=None, FIELD_REPOSITORY_API_URL=None),
        open_session=refuse_session,
        synced_at=SYNCED_AT,
    )
    errors = [outcome.error for outcome in report.outcomes]
    assert errors == [
        "NotConfigured: DESIGNER_PORTAL_API_URL must be the portal's https API address",
        "NotConfigured: FIELD_REPOSITORY_API_URL must be the portal's https API address",
    ]
