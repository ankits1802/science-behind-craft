from __future__ import annotations

import httpx

from ..adapter import Clock, HttpSourceAdapter, utc_now
from ..http import RatePolicy, ResponseCache, SourceHttp
from .commons import COMMONS_RATE, WikimediaCommonsAdapter
from .pubchem import PUBCHEM_RATE, PubChemAdapter
from .wikidata import WIKIDATA_RATE, WIKIDATA_SPARQL_RATE, WikidataAdapter
from .wikipedia import WIKIPEDIA_RATE, WikipediaAdapter

__all__ = ["reference_sources"]


def reference_sources(client: httpx.AsyncClient, *, clock: Clock = utc_now) -> tuple[HttpSourceAdapter, ...]:
    def http(service: str, policy: RatePolicy) -> SourceHttp:
        return SourceHttp(client=client, service=service, policy=policy, cache=ResponseCache())

    return (
        WikipediaAdapter(http("wikipedia", WIKIPEDIA_RATE), clock=clock),
        WikidataAdapter(
            http("wikidata", WIKIDATA_RATE), sparql=http("wikidata_sparql", WIKIDATA_SPARQL_RATE), clock=clock
        ),
        PubChemAdapter(http("pubchem", PUBCHEM_RATE), clock=clock),
        WikimediaCommonsAdapter(http("wikimedia_commons", COMMONS_RATE), clock=clock),
    )
