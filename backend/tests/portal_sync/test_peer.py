import httpx
import pytest

from app.core.errors import ExternalFailure, NotConfigured, Refused
from app.services.portal_peer import peer_for, peer_signature
from tests.portal_sync.fixtures import (
    TOKEN,
    designer_payload,
    reference_signature,
    settings,
    signed_transport,
)

DESIGNER_PORTAL_SIGNATURE = "23cad0533be57bffb503168b57ca582581991c4929bec2785a60b9c80d12bdb6"


def test_signature_matches_the_designer_portal_signer() -> None:
    signature = peer_signature(
        TOKEN,
        b'{"schemaVersion":1}',
        method="GET",
        path="/cross-portal/peer/crafts",
        nonce="0123456789abcdef0123456789abcdef",
    )
    assert signature == DESIGNER_PORTAL_SIGNATURE


async def test_the_feed_is_fetched_with_the_peer_headers_and_checked() -> None:
    seen: list[httpx.Request] = []
    transport = signed_transport({"designer.example.com": designer_payload()}, seen=seen)
    feed = await peer_for(settings(), "DESIGNER", transport=transport).craft_feed()
    assert len(feed.crafts) == 4
    request = seen[0]
    assert str(request.url) == "https://designer.example.com/api/cross-portal/peer/crafts"
    assert request.method == "GET"
    assert request.headers["authorization"] == f"Bearer {TOKEN}"
    assert len(request.headers["x-cross-portal-nonce"]) == 32
    assert request.headers["x-cross-portal-requested-by"] == "kalavigyan-craft-sync"


async def test_an_answer_signed_with_another_token_is_refused() -> None:
    transport = signed_transport({"designer.example.com": designer_payload()}, token="z" * 40)
    with pytest.raises(Refused) as caught:
        await peer_for(settings(), "DESIGNER", transport=transport).craft_feed()
    assert caught.value.reason == "unsigned_answer"


async def test_an_unsigned_answer_is_refused() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=designer_payload()))
    with pytest.raises(Refused):
        await peer_for(settings(), "DESIGNER", transport=transport).craft_feed()


@pytest.mark.parametrize(
    ("status", "kind", "retryable"),
    [(404, "not_found", False), (401, "auth", False), (429, "rate_limit", True), (503, "unavailable", True)],
)
async def test_a_failed_answer_names_its_kind(status: int, kind: str, retryable: bool) -> None:
    transport = signed_transport({"designer.example.com": {"detail": "x"}}, status=status)
    with pytest.raises(ExternalFailure) as caught:
        await peer_for(settings(), "DESIGNER", transport=transport).craft_feed()
    assert (caught.value.kind, caught.value.retryable, caught.value.status) == (kind, retryable, status)
    assert caught.value.service == "DESIGNER"


async def test_an_unreachable_portal_is_an_unavailable_failure() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(ExternalFailure) as caught:
        await peer_for(settings(), "FIELD_REPOSITORY", transport=httpx.MockTransport(refuse)).craft_feed()
    assert caught.value.kind == "unavailable"
    assert TOKEN not in str(caught.value)


async def test_a_signed_body_that_is_not_json_is_a_failure() -> None:
    transport = signed_transport({"designer.example.com": b"<html>"})
    with pytest.raises(ExternalFailure, match="not UTF-8 JSON"):
        await peer_for(settings(), "DESIGNER", transport=transport).craft_feed()


@pytest.mark.parametrize(
    ("overrides", "name"),
    [
        ({"DESIGNER_PORTAL_API_URL": None}, "DESIGNER_PORTAL_API_URL"),
        ({"DESIGNER_PORTAL_API_URL": "http://designer.example.com/api"}, "DESIGNER_PORTAL_API_URL"),
        ({"CROSS_PORTAL_TOKEN": "short"}, "CROSS_PORTAL_TOKEN"),
        ({"CROSS_PORTAL_TOKEN": None}, "CROSS_PORTAL_TOKEN"),
    ],
)
def test_missing_settings_are_not_configured(overrides: dict, name: str) -> None:
    with pytest.raises(NotConfigured) as caught:
        peer_for(settings(**overrides), "DESIGNER")
    assert caught.value.name == name


def test_the_fixture_signer_agrees_with_the_designer_portal() -> None:
    assert (
        reference_signature(
            TOKEN,
            b'{"schemaVersion":1}',
            method="GET",
            path="/cross-portal/peer/crafts",
            nonce="0123456789abcdef0123456789abcdef",
        )
        == DESIGNER_PORTAL_SIGNATURE
    )
