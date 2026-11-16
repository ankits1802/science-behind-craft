import httpx
import pytest

from app.core.errors import ExternalFailure, failure_kind
from app.sources.http import (
    DEFAULT_BLOCK_SECONDS,
    SOURCE_MAX_BYTES,
    RatePolicy,
    ResponseCache,
    SourceHttp,
    source_client,
)

from .recorded import FakeClock, Recorder, Reply, source_http

WORKS = "api.openalex.org/works"
URL = "https://api.openalex.org/works"


async def test_calls_are_spaced_by_the_minimum_interval() -> None:
    clock = FakeClock()
    recorder = Recorder({WORKS: Reply("openalex_search.json")})
    http = source_http(recorder, "openalex", policy=RatePolicy(min_interval=0.5), clock=clock)
    for page in ("1", "2", "3"):
        await http.get(URL, params={"page": page})
    assert clock.slept == [0.5, 0.5]
    assert len(recorder.requests) == 3


async def test_a_repeated_call_is_answered_from_the_cache_until_it_expires() -> None:
    clock = FakeClock()
    recorder = Recorder({WORKS: Reply("openalex_search.json")})
    http = source_http(recorder, "openalex", clock=clock)
    first = await http.get(URL, params={"search": "alizarin"})
    again = await http.get(URL, params={"search": "alizarin"})
    assert again is first
    assert len(recorder.requests) == 1
    clock.now += 601
    await http.get(URL, params={"search": "alizarin"})
    assert len(recorder.requests) == 2


async def test_secrets_are_sent_but_never_part_of_the_cache_key() -> None:
    recorder = Recorder({WORKS: Reply("openalex_search.json")})
    http = source_http(recorder, "openalex")
    await http.get(
        URL, params={"search": "dye"}, secret_params={"api_key": "k1"}, secret_headers={"x-api-key": "h1"}
    )
    await http.get(URL, params={"search": "dye"}, secret_params={"api_key": "k2"})
    assert len(recorder.requests) == 1
    sent = recorder.requests[0]
    assert sent.url.params["api_key"] == "k1"
    assert sent.headers["x-api-key"] == "h1"
    assert all("k1" not in str(part) for key in http.cache._entries for part in key)


async def test_a_short_retry_after_is_waited_out_once() -> None:
    clock = FakeClock()
    recorder = Recorder(
        {
            WORKS: [
                Reply("semantic_scholar_429.json", status=429, headers={"Retry-After": "3"}),
                Reply("openalex_search.json"),
            ]
        }
    )
    http = source_http(recorder, "openalex", clock=clock)
    response = await http.get(URL)
    assert response.status == 200
    assert clock.slept == [3.0]
    assert len(recorder.requests) == 2


async def test_a_long_retry_after_fails_and_blocks_later_calls_without_sending() -> None:
    clock = FakeClock()
    recorder = Recorder(
        {WORKS: Reply("semantic_scholar_429.json", status=429, headers={"Retry-After": "120"})}
    )
    http = source_http(recorder, "openalex", clock=clock)
    with pytest.raises(ExternalFailure) as first:
        await http.get(URL)
    assert (first.value.kind, first.value.retryable, first.value.retry_after) == ("rate_limit", True, 120.0)
    clock.now += 30
    with pytest.raises(ExternalFailure) as blocked:
        await http.get(URL, params={"other": "query"})
    assert blocked.value.kind == "rate_limit"
    assert blocked.value.retry_after == 90.0
    assert len(recorder.requests) == 1


async def test_a_rate_limit_without_retry_after_pauses_the_service() -> None:
    clock = FakeClock()
    recorder = Recorder({WORKS: Reply("semantic_scholar_429.json", status=429)})
    http = source_http(recorder, "openalex", clock=clock)
    with pytest.raises(ExternalFailure) as failure:
        await http.get(URL)
    assert failure.value.retry_after is None
    with pytest.raises(ExternalFailure) as blocked:
        await http.get(URL)
    assert blocked.value.retry_after == DEFAULT_BLOCK_SECONDS
    assert len(recorder.requests) == 1


@pytest.mark.parametrize(
    ("status", "kind", "retryable"),
    [
        (400, "bad_request", False),
        (401, "auth", False),
        (403, "auth", False),
        (404, "not_found", False),
        (410, "not_found", False),
        (422, "bad_request", False),
        (500, "unavailable", True),
        (503, "unavailable", True),
        (302, "error", False),
        (418, "error", False),
    ],
)
async def test_a_status_becomes_a_failure_of_one_kind(status: int, kind: str, retryable: bool) -> None:
    recorder = Recorder({WORKS: Reply("openalex_missing.html", status=status)})
    with pytest.raises(ExternalFailure) as failure:
        await source_http(recorder, "openalex").get(URL)
    assert (failure.value.kind, failure.value.retryable, failure.value.status) == (kind, retryable, status)
    assert failure.value.service == "openalex"
    assert str(failure.value) == f"openalex answered {status}"


def test_failure_kinds_by_status() -> None:
    assert [failure_kind(s) for s in (429, 599, 404, 401, 400)] == [
        "rate_limit",
        "unavailable",
        "not_found",
        "auth",
        "bad_request",
    ]


async def test_transport_failures_are_unavailable_and_name_no_url() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    clock = FakeClock()
    http = SourceHttp(
        client=httpx.AsyncClient(transport=httpx.MockTransport(refuse)),
        service="crossref",
        policy=RatePolicy(min_interval=0),
        cache=ResponseCache(clock=clock),
        clock=clock,
        sleep=clock.sleep,
    )
    with pytest.raises(ExternalFailure) as failure:
        await http.get("https://api.crossref.org/works", secret_params={"api_key": "hidden"})
    assert failure.value.kind == "unavailable"
    assert "hidden" not in str(failure.value)
    assert "api.crossref.org" not in str(failure.value)


async def test_an_oversized_body_is_refused() -> None:
    def huge(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * (SOURCE_MAX_BYTES + 1))

    clock = FakeClock()
    http = SourceHttp(
        client=httpx.AsyncClient(transport=httpx.MockTransport(huge)),
        service="core",
        policy=RatePolicy(min_interval=0),
        cache=ResponseCache(clock=clock),
        clock=clock,
        sleep=clock.sleep,
    )
    with pytest.raises(ExternalFailure, match="core sent more than"):
        await http.get("https://api.core.ac.uk/v3/works/1")


async def test_a_body_that_is_not_json_is_an_error() -> None:
    recorder = Recorder({WORKS: Reply("openalex_missing.html")})
    response = await source_http(recorder, "openalex").get(URL)
    with pytest.raises(ExternalFailure, match="not JSON") as failure:
        response.json("openalex")
    assert failure.value.kind == "error"


def test_the_client_names_the_contact_and_never_follows_redirects() -> None:
    client = source_client("cxa.craftecosystem@gmail.com")
    assert "mailto:cxa.craftecosystem@gmail.com" in client.headers["User-Agent"]
    assert client.follow_redirects is False


def test_rate_policies_are_never_negative() -> None:
    with pytest.raises(ValueError):
        RatePolicy(min_interval=-1)
