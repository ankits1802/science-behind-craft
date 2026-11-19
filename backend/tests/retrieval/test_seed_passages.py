from typing import Any

from app.retrieval.indexing import SourceChunk
from app.services.claim_seed import seed_id
from app.services.claim_seed_passages import seed_passages

GI_QUOTE = "Kutch Ajrakh is an elaborate resist block printing technique"
KHAMIR_QUOTE = "Ajrakh printing originally came from Sindh"


def cite(source: str, quote: str | None, locator: str | None, check: str = "PASS") -> dict[str, Any]:
    return {"sourceId": source, "quote": quote, "locator": locator, "quoteCheck": check}


SEED: dict[str, Any] = {
    "claims": [
        {
            "id": "seed-1",
            "sources": [cite("ie:S1", GI_QUOTE, "PDF p. 1"), cite("ie:S2", KHAMIR_QUOTE, "para 2")],
        },
        {
            "id": "seed-2",
            "sources": [cite("ie:S1", f"  {GI_QUOTE} ", "PDF p. 4"), cite("ie:S1", GI_QUOTE, "PDF p. 1")],
        },
        {"id": "seed-3", "sources": [cite("inf:W", None, "Structure and function of wood", "NA")]},
        {"id": "seed-4", "sources": [cite("ie:S2", "A quote nobody re-found", "para 9", "FAIL")]},
    ]
}


def test_each_seeded_source_keeps_its_verbatim_quotes_once_with_every_locator() -> None:
    planned = {passages.source_id: passages.chunks for passages in seed_passages(SEED)}
    assert planned == {
        seed_id("source", "ie:S1"): (SourceChunk(GI_QUOTE, "PDF p. 1; PDF p. 4", "en", "PUBLIC"),),
        seed_id("source", "ie:S2"): (SourceChunk(KHAMIR_QUOTE, "para 2", "en", "PUBLIC"),),
    }


def test_a_citation_without_a_checked_quote_stores_no_passage() -> None:
    assert seed_passages({"claims": [SEED["claims"][2], SEED["claims"][3]]}) == []
    assert seed_passages({}) == []
