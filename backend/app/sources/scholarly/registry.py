from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import httpx

from app.core.errors import NotConfigured

from ..adapter import Clock, HttpSourceAdapter, utc_now
from ..http import RatePolicy, ResponseCache, SourceHttp
from .arxiv import ARXIV_RATE, ArxivAdapter
from .core_works import CORE_RATE, CoreAdapter
from .crossref import CROSSREF_RATE, CrossrefAdapter
from .doaj import DOAJ_RATE, DoajAdapter
from .elsevier import ELSEVIER_RATE, ElsevierAdapter
from .europe_pmc import EUROPE_PMC_RATE, EuropePmcAdapter
from .openalex import OPENALEX_RATE, OpenAlexAdapter
from .semantic_scholar import SEMANTIC_SCHOLAR_RATE, SemanticScholarAdapter
from .springer_nature import SPRINGER_NATURE_RATE, SpringerNatureAdapter
from .unpaywall import UNPAYWALL_RATE, UnpaywallLocator

__all__ = ["SCHOLARLY_KEY_NAMES", "ScholarlyKeys", "ScholarlySources", "scholarly_sources"]

SCHOLARLY_KEY_NAMES = (
    "OPENALEX_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY",
    "CORE_API_KEY",
    "ELSEVIER_API_KEY",
    "ELSEVIER_INSTTOKEN",
    "SPRINGER_NATURE_API_KEY",
)


HttpFactory = Callable[[str, RatePolicy], SourceHttp]


@dataclass(frozen=True, repr=False)
class ScholarlyKeys:
    contact_email: str
    openalex_api_key: str | None = None
    semantic_scholar_api_key: str | None = None
    core_api_key: str | None = None
    elsevier_api_key: str | None = None
    elsevier_insttoken: str | None = None
    springer_nature_api_key: str | None = None

    def __repr__(self) -> str:
        present = [name for name in SCHOLARLY_KEY_NAMES if getattr(self, name.lower())]
        return f"ScholarlyKeys(contact_email={self.contact_email!r}, present={present})"


@dataclass(frozen=True)
class ScholarlySources:
    adapters: tuple[HttpSourceAdapter, ...]
    locator: UnpaywallLocator
    unconfigured: tuple[str, ...]


def scholarly_sources(
    keys: ScholarlyKeys, client: httpx.AsyncClient, *, clock: Clock = utc_now
) -> ScholarlySources:
    if not keys.contact_email:
        raise NotConfigured("RESEARCH_CONTACT_EMAIL", "Scholarly APIs need a contact email address")
    http = _http_factory(client)
    keyed, unconfigured = _keyed_adapters(keys, http, clock)
    locator = UnpaywallLocator(
        http("unpaywall", UNPAYWALL_RATE), contact_email=keys.contact_email, clock=clock
    )
    return ScholarlySources((*_open_adapters(keys, http, clock), *keyed), locator, unconfigured)


def _open_adapters(keys: ScholarlyKeys, http: HttpFactory, clock: Clock) -> list[HttpSourceAdapter]:
    email = keys.contact_email
    return [
        OpenAlexAdapter(
            http("openalex", OPENALEX_RATE), contact_email=email, api_key=keys.openalex_api_key, clock=clock
        ),
        CrossrefAdapter(http("crossref", CROSSREF_RATE), contact_email=email, clock=clock),
        SemanticScholarAdapter(
            http("semantic_scholar", SEMANTIC_SCHOLAR_RATE),
            api_key=keys.semantic_scholar_api_key,
            clock=clock,
        ),
        EuropePmcAdapter(http("europe_pmc", EUROPE_PMC_RATE), clock=clock),
        ArxivAdapter(http("arxiv", ARXIV_RATE), clock=clock),
        DoajAdapter(http("doaj", DOAJ_RATE), clock=clock),
    ]


def _keyed_adapters(
    keys: ScholarlyKeys, http: HttpFactory, clock: Clock
) -> tuple[list[HttpSourceAdapter], tuple[str, ...]]:
    adapters: list[HttpSourceAdapter] = []
    unconfigured: tuple[str, ...] = ()
    if keys.core_api_key:
        adapters.append(CoreAdapter(http("core", CORE_RATE), api_key=keys.core_api_key, clock=clock))
    else:
        unconfigured = ("CORE_API_KEY",)
    if keys.elsevier_api_key:
        elsevier_http = http("elsevier", ELSEVIER_RATE)
        adapters.append(
            ElsevierAdapter(
                elsevier_http, api_key=keys.elsevier_api_key, insttoken=keys.elsevier_insttoken, clock=clock
            )
        )
    if keys.springer_nature_api_key:
        springer_http = http("springer_nature", SPRINGER_NATURE_RATE)
        adapters.append(
            SpringerNatureAdapter(springer_http, api_key=keys.springer_nature_api_key, clock=clock)
        )
    return adapters, unconfigured


def _http_factory(client: httpx.AsyncClient) -> HttpFactory:
    def build(service: str, policy: RatePolicy) -> SourceHttp:
        return SourceHttp(client=client, service=service, policy=policy, cache=ResponseCache())

    return build
