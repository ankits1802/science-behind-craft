import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from app.core.errors import ExternalFailure
from app.fetcher.server import create_app
from app.research.fetcher import FETCHER_HEALTH_PATH, FetchedPage, FetchRefused, FetchRequest
from app.sources.fetcher_client import FetcherClient
from app.sources.web.searxng import SearxngAdapter

from ..sources.recorded import Recorder, source_http
from .site import FETCHED, PUBLIC_A, Site, fixture, html

BACKEND = Path(__file__).resolve().parents[2]
ARTICLE = "https://crafts.example.org/ajrakh/resist-printing"


class Scripted:
    def __init__(self, outcome: FetchedPage | Exception) -> None:
        self.outcome = outcome
        self.requests: list[FetchRequest] = []

    async def fetch(self, request: FetchRequest) -> FetchedPage:
        self.requests.append(request)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def client_for(fetcher: object) -> FetcherClient:
    transport = httpx.ASGITransport(app=create_app(fetcher))
    return FetcherClient("http://fetcher.test/", httpx.AsyncClient(transport=transport))


def sample_page() -> FetchedPage:
    return FetchedPage.model_validate(
        {
            "url": ARTICLE,
            "finalUrl": ARTICLE,
            "status": 200,
            "contentType": "text/html",
            "bytes": 12,
            "sha256": "a" * 64,
            "fetchedAt": FETCHED,
            "text": "Alum fixes the red dye.",
            "truncated": False,
            "metadata": {"title": "Mordants"},
        }
    )


async def test_a_page_crosses_the_wire_unchanged() -> None:
    fetcher = Scripted(sample_page())
    page = await client_for(fetcher).fetch(FetchRequest(url=ARTICLE, max_bytes=4096))
    assert page == sample_page()
    assert fetcher.requests == [FetchRequest(url=ARTICLE, max_bytes=4096)]


async def test_a_refusal_crosses_the_wire_with_its_reason() -> None:
    refusal = FetchRefused(ARTICLE, "PRIVATE_ADDRESS", "resolves to 10.0.0.1")
    with pytest.raises(FetchRefused) as refused:
        await client_for(Scripted(refusal)).fetch(FetchRequest(url=ARTICLE))
    assert (refused.value.url, refused.value.reason, refused.value.detail) == (
        ARTICLE,
        "PRIVATE_ADDRESS",
        "resolves to 10.0.0.1",
    )


async def test_a_remote_failure_crosses_the_wire_with_its_kind() -> None:
    failure = ExternalFailure(
        "crafts.example.org answered 503", kind="unavailable", retryable=True, status=503, retry_after=30.0
    )
    with pytest.raises(ExternalFailure) as raised:
        await client_for(Scripted(failure)).fetch(FetchRequest(url=ARTICLE))
    got = raised.value
    assert (got.kind, got.retryable, got.status, got.retry_after, got.service, str(got)) == (
        "unavailable",
        True,
        503,
        30.0,
        "fetcher",
        "crafts.example.org answered 503",
    )


async def test_a_body_off_the_contract_is_a_failure_not_a_page() -> None:
    def off_contract(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"text": "no other fields"})

    client = FetcherClient(
        "http://fetcher.test", httpx.AsyncClient(transport=httpx.MockTransport(off_contract))
    )
    with pytest.raises(ExternalFailure) as failure:
        await client.fetch(FetchRequest(url=ARTICLE))
    assert failure.value.kind == "error"


async def test_an_unreachable_fetcher_is_unavailable() -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    client = FetcherClient("http://fetcher.test", httpx.AsyncClient(transport=httpx.MockTransport(down)))
    with pytest.raises(ExternalFailure) as failure:
        await client.fetch(FetchRequest(url=ARTICLE))
    assert (failure.value.kind, failure.value.retryable) == ("unavailable", True)


async def test_health_answers_without_fetching() -> None:
    transport = httpx.ASGITransport(app=create_app(Scripted(sample_page())))
    async with httpx.AsyncClient(transport=transport, base_url="http://fetcher.test") as client:
        response = await client.get(FETCHER_HEALTH_PATH)
    assert (response.status_code, response.json()) == (200, {"status": "ok"})


async def test_a_web_hit_is_read_through_the_sandbox_service_end_to_end() -> None:
    site = Site(
        routes={"crafts.example.org/ajrakh/resist-printing": html(fixture("article.html"))},
        dns={"crafts.example.org": [PUBLIC_A]},
    )
    adapter = SearxngAdapter(
        source_http(Recorder({}), "searxng"),
        base_url="http://127.0.0.1:8888",
        fetcher=client_for(site.fetcher()),
    )
    document = await adapter.fetch(f"searxng:{ARTICLE}")
    assert document.content == "FULL_TEXT"
    assert document.item.id == f"searxng:{ARTICLE}"
    assert document.item.title == "Ajrakh resist printing"
    assert document.item.publisher == "Craft Notes"
    assert "alum is printed where red is wanted." in document.text
    assert "ignore previous instructions" not in document.text


def test_the_fetcher_process_loads_no_api_settings_database_or_aws_code() -> None:
    probe = (
        "import sys, app.fetcher.__main__\n"
        "loaded = [m for m in ('app.core.config', 'app.core.db', 'boto3', 'app.services') if m in sys.modules]\n"
        "print(','.join(loaded))\n"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", f"import sys; sys.path.insert(0, {str(BACKEND)!r})\n{probe}"],
        capture_output=True,
        text=True,
        check=True,
        cwd=BACKEND,
        timeout=60,
    )
    assert result.stdout.strip() == ""
