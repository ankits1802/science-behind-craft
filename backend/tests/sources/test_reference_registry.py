import re

from app.research.evidence import ADAPTER_NAME_PATTERN, Quote, SourceAdapter, SourceDocument
from app.research.quotes import quote_occurs
from app.research.write_back import ClaimWriteBack, WriteBackCitation, WriteBackSubject
from app.sources.reference.registry import reference_sources
from app.sources.reference.wikidata import WikidataAdapter

from .recorded import WIKIDATA_ALIZARIN, Recorder, fixed_clock, wikidata_adapter


def test_every_reference_adapter_meets_the_contract_and_paces_itself() -> None:
    adapters = reference_sources(Recorder({}).client(), clock=fixed_clock())
    assert [adapter.name for adapter in adapters] == ["wikipedia", "wikidata", "pubchem", "wikimedia_commons"]
    assert all(isinstance(adapter, SourceAdapter) for adapter in adapters)
    assert all(re.fullmatch(ADAPTER_NAME_PATTERN, adapter.name) for adapter in adapters)
    assert all(adapter.tier == "T3" for adapter in adapters)
    intervals = {adapter.http.service: adapter.http.policy.min_interval for adapter in adapters}
    assert intervals == {"wikipedia": 0.2, "wikidata": 0.2, "pubchem": 0.25, "wikimedia_commons": 0.2}
    sparql = next(adapter for adapter in adapters if isinstance(adapter, WikidataAdapter)).sparql
    assert (sparql.service, sparql.policy.min_interval) == ("wikidata_sparql", 1.0)


async def test_a_quote_from_a_fetched_wikidata_document_writes_back_as_a_quoted_claim() -> None:
    adapter, _ = wikidata_adapter(WIKIDATA_ALIZARIN)
    document = await adapter.fetch("wikidata:Q267813")
    quote = Quote(text="melting point: 288 degree Celsius; 289 degree Celsius")
    assert quote_occurs(quote.text, document.text)
    quoted = document.item.model_copy(update={"quotes": [quote]})
    SourceDocument(
        item=quoted,
        text=document.text,
        text_sha256=document.text_sha256,
        truncated=document.truncated,
        content=document.content,
    )
    claim = ClaimWriteBack(
        craft_slug="Kutch-Ajrakh",
        subject=WriteBackSubject(concept_type="MATERIAL", concept_name="alizarin"),
        predicate="melting_point",
        text="Alizarin melts at 288 to 289 degrees Celsius.",
        label="QUOTED",
        level_reason="Wikidata statement quoted verbatim",
        citations=[WriteBackCitation(evidence=quoted, quote=quote, quote_check="PASS", relation="DIRECT")],
        found_by="BACKGROUND",
    )
    assert claim.evidence_level == "PROVISIONAL"
    assert claim.citations[0].evidence.source_key == "url:https://www.wikidata.org/wiki/Q267813"
