import pytest

from app.core.errors import InvalidInput
from app.research.evidence import SearchQuery
from app.sources.reference.commons import WikimediaCommonsAdapter
from app.sources.reference.mediawiki import language_and_native, with_language

from .recorded import (
    WIKIDATA_API,
    WIKIDATA_SPARQL,
    Recorder,
    Reply,
    fixed_clock,
    source_http,
    wikidata_adapter,
)

COMMONS_API = "commons.wikimedia.org/w/api.php"


def commons(routes: dict) -> tuple[WikimediaCommonsAdapter, Recorder]:
    recorder = Recorder(routes)
    return WikimediaCommonsAdapter(source_http(recorder, "wikimedia_commons"), clock=fixed_clock()), recorder


def test_an_id_carries_its_language_unless_it_is_english() -> None:
    assert with_language("Q267813", "en") == "Q267813"
    assert with_language("Q267813", "hi") == "hi:Q267813"
    assert language_and_native("Q267813") == ("en", "Q267813")
    assert language_and_native("ta:Q267813") == ("ta", "Q267813")
    assert language_and_native("Hindi:Q267813") == ("en", "Hindi:Q267813")


async def test_an_id_with_a_malformed_language_is_refused() -> None:
    adapter, _ = wikidata_adapter({})
    for bad in ("wikidata:Hindi:Q267813", "wikidata:hi:P31", "wikidata:hi:"):
        with pytest.raises(InvalidInput):
            await adapter.fetch(bad)


async def test_a_wikidata_item_found_in_hindi_is_fetched_in_hindi() -> None:
    adapter, recorder = wikidata_adapter(
        {
            WIKIDATA_API: [Reply("wikidata_search.json"), Reply("wikidata_entities_hi.json")],
            WIKIDATA_SPARQL: Reply("wikidata_statements.json"),
        }
    )
    (alizarin, *_) = await adapter.search(SearchQuery(text="alizarin", language="hi"), 3)
    assert alizarin.id == "wikidata:hi:Q267813"
    adapter, recorder = wikidata_adapter(
        {WIKIDATA_API: Reply("wikidata_entities_hi.json"), WIKIDATA_SPARQL: Reply("wikidata_statements.json")}
    )
    document = await adapter.fetch(alizarin.id)
    entities, statements = (request.url.params for request in recorder.requests)
    assert (entities["ids"], entities["languages"], entities["languagefallback"]) == ("Q267813", "hi", "1")
    assert 'wikibase:language "hi,mul,en"' in statements["query"]
    assert document.item.id == "wikidata:hi:Q267813"
    assert document.item.external_ids["wikidata"] == "Q267813"
    assert document.text.split("\n")[0] == "alizarin (Q267813)"


async def test_an_english_wikidata_id_keeps_its_old_form() -> None:
    adapter, recorder = wikidata_adapter(
        {WIKIDATA_API: Reply("wikidata_entity.json"), WIKIDATA_SPARQL: Reply("wikidata_statements.json")}
    )
    document = await adapter.fetch("wikidata:Q267813")
    assert document.item.id == "wikidata:Q267813"
    assert recorder.requests[0].url.params["languages"] == "en"


async def test_commons_ids_carry_the_metadata_language() -> None:
    adapter, recorder = commons({COMMONS_API: Reply("commons_search.json")})
    items = await adapter.search(SearchQuery(text="ajrak", language="hi"), 3)
    assert [item.id for item in items] == [
        "wikimedia_commons:hi:15565262",
        "wikimedia_commons:hi:67760143",
        "wikimedia_commons:hi:49875448",
    ]
    assert recorder.requests[0].url.params["iiextmetadatalanguage"] == "hi"
    adapter, recorder = commons({COMMONS_API: Reply("commons_file.json")})
    document = await adapter.fetch("wikimedia_commons:hi:60897367")
    sent = recorder.requests[0].url.params
    assert (sent["pageids"], sent["iiextmetadatalanguage"]) == ("60897367", "hi")
    assert document.item.id == "wikimedia_commons:hi:60897367"
