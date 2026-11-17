from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import httpx
import pytest

from app.core.errors import ExternalFailure
from app.providers.elevenlabs_download import DOWNLOAD_HOSTS, downloaded

CONTENT = "https://storage.googleapis.com/generations/JWr5N6X9ZTqf8jD2LmQb"
CHUNK = b"\x89PNG" * 256


@dataclass
class Endless(httpx.AsyncByteStream):
    sent: list[int] = field(default_factory=list)

    async def __aiter__(self) -> AsyncIterator[bytes]:
        while True:
            self.sent.append(len(CHUNK))
            yield CHUNK


def client(answer: httpx.Response, seen: list[httpx.Request]) -> httpx.AsyncClient:
    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return answer

    return httpx.AsyncClient(transport=httpx.MockTransport(handle))


async def test_the_documented_signed_link_is_fetched_whole_within_the_limit() -> None:
    seen: list[httpx.Request] = []
    body = CHUNK * 4
    fetched = await downloaded(client(httpx.Response(200, content=body), seen), CONTENT, limit=len(body))
    assert fetched == body
    assert [request.url.host for request in seen] == ["storage.googleapis.com"]
    assert sorted(DOWNLOAD_HOSTS) == ["storage.googleapis.com"]


@pytest.mark.parametrize(
    "url",
    [
        "https://example.org/generations/a",
        "https://storage.googleapis.com.example.org/a",
        "http://storage.googleapis.com/a",
        "https://user@storage.googleapis.com/a",
        "https://storage.googleapis.com:8443/a",
        "https://storage.googleapis.com:notaport/a",
    ],
)
async def test_a_link_off_the_documented_host_is_never_fetched(url: str) -> None:
    seen: list[httpx.Request] = []
    with pytest.raises(ExternalFailure, match="generation link"):
        await downloaded(client(httpx.Response(200, content=CHUNK), seen), url, limit=1024)
    assert seen == []


async def test_a_declared_length_over_the_limit_is_refused_before_the_body_is_read() -> None:
    stream = Endless()
    answer = httpx.Response(200, headers={"content-length": str(10 * len(CHUNK))}, stream=stream)
    with pytest.raises(ExternalFailure, match="bytes declared"):
        await downloaded(client(answer, []), CONTENT, limit=len(CHUNK))
    assert stream.sent == []


async def test_a_body_that_streams_past_the_limit_is_cut_as_soon_as_it_passes() -> None:
    stream = Endless()
    with pytest.raises(ExternalFailure, match=f"more than {3 * len(CHUNK)} bytes"):
        await downloaded(client(httpx.Response(200, stream=stream), []), CONTENT, limit=3 * len(CHUNK))
    assert len(stream.sent) == 4


async def test_an_empty_or_refused_download_fails_loudly() -> None:
    with pytest.raises(ExternalFailure, match="0 bytes"):
        await downloaded(client(httpx.Response(200, content=b""), []), CONTENT, limit=1024)
    with pytest.raises(ExternalFailure, match="answered 403"):
        await downloaded(client(httpx.Response(403, content=b"no"), []), CONTENT, limit=1024)
