from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import httpx

from app.sources.http import RatePolicy, ResponseCache, SourceHttp
from app.sources.reference.wikidata import WikidataAdapter

FIXTURES = Path(__file__).parent / "fixtures"
RETRIEVED = datetime(2026, 11, 16, 9, 30, tzinfo=UTC)
CONTACT = "cxa.craftecosystem@gmail.com"
CONTENT_TYPES = {
    ".json": "application/json",
    ".xml": "application/atom+xml",
    ".txt": "text/plain",
    ".html": "text/html",
    ".sdf": "chemical/x-mdl-sdfile",
}


def recorded(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


@dataclass(frozen=True)
class Reply:
    fixture: str
    status: int = 200
    headers: dict[str, str] = field(default_factory=dict)

    def response(self) -> httpx.Response:
        content_type = CONTENT_TYPES[Path(self.fixture).suffix]
        return httpx.Response(
            self.status, content=recorded(self.fixture), headers={"content-type": content_type} | self.headers
        )


@dataclass
class FakeClock:
    now: float = 1000.0
    slept: list[float] = field(default_factory=list)

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


@dataclass
class Recorder:
    routes: dict[str, Reply | list[Reply]]
    requests: list[httpx.Request] = field(default_factory=list)

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        key = f"{request.url.host}{request.url.raw_path.decode().split('?')[0]}"
        reply = self.routes.get(key)
        if reply is None:
            raise AssertionError(f"no recorded reply for {key}")
        if isinstance(reply, list):
            return reply.pop(0).response()
        return reply.response()

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handle))


def source_http(
    recorder: Recorder,
    service: str,
    *,
    policy: RatePolicy | None = None,
    clock: FakeClock | None = None,
) -> SourceHttp:
    ticks = clock or FakeClock()
    return SourceHttp(
        client=recorder.client(),
        service=service,
        policy=policy or RatePolicy(min_interval=0.0),
        cache=ResponseCache(clock=ticks),
        clock=ticks,
        sleep=ticks.sleep,
    )


def fixed_clock() -> Callable[[], datetime]:
    return lambda: RETRIEVED


WIKIDATA_API = "www.wikidata.org/w/api.php"
WIKIDATA_SPARQL = "query.wikidata.org/sparql"
WIKIDATA_ALIZARIN = {
    WIKIDATA_API: Reply("wikidata_entity.json"),
    WIKIDATA_SPARQL: Reply("wikidata_statements.json"),
}


def wikidata_adapter(routes: dict[str, Reply | list[Reply]]) -> tuple[WikidataAdapter, Recorder]:
    recorder = Recorder(routes)
    adapter = WikidataAdapter(
        source_http(recorder, "wikidata"),
        sparql=source_http(recorder, "wikidata_sparql"),
        clock=fixed_clock(),
    )
    return adapter, recorder
