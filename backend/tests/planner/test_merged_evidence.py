from __future__ import annotations

from app.planner.live_search import SearchHit, merged_evidence
from app.sources.adapter import native_id
from tests.composer.fixtures import PLAN
from tests.research.fixtures import evidence_item

SHARED_DOI = "10.1000/Example.2019.1"


def test_the_kept_item_is_fetched_by_the_source_that_found_it_even_when_another_found_it_first() -> None:
    from_crossref = evidence_item(
        id="crossref:10.1000/example.2019.1", adapter="crossref", doi=SHARED_DOI, trust="C"
    )
    from_openalex = evidence_item(id="openalex:W2003869387", adapter="openalex", doi=SHARED_DOI, trust="A")
    hits = [
        SearchHit(searcher="crossref", query_index=0, rank=1, item=from_crossref),
        SearchHit(searcher="openalex", query_index=1, rank=3, item=from_openalex),
    ]
    (entry,) = merged_evidence(PLAN, hits)
    assert entry.item.id == "openalex:W2003869387"
    assert entry.found_by == ("openalex", "crossref")
    assert native_id(entry.found_by[0], entry.item.id) == "W2003869387"


def test_a_single_source_keeps_its_own_order() -> None:
    hits = [
        SearchHit(searcher="openalex", query_index=0, rank=1, item=evidence_item()),
        SearchHit(searcher="openalex", query_index=1, rank=2, item=evidence_item()),
    ]
    (entry,) = merged_evidence(PLAN, hits)
    assert entry.found_by == ("openalex",)
