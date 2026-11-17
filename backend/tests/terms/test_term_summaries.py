import json
import uuid

import pytest

from app.core.errors import Refused
from app.research.composition import ComposedSentence, QuotedSpan
from app.services.knowledge_view import ClaimView
from app.services.term_research import ResearchedSummary
from app.services.term_summaries import NO_SUMMARY_REASON, UNKNOWN_TERM_REASON, StoredClaims, TermLookup

from ..answering.fakes import translation
from ..planner.fakes import FakeModel
from .fakes import (
    CHECKED_AT,
    KUT_CONCEPT,
    FakeResearch,
    FakeTermStore,
    golden_claims,
    golden_term,
    kut_term,
)

PAGE = "https://crafts.example.org/ajrakh/kut"
SOURCE_ID = uuid.UUID("7e57ab1e-0000-4000-8000-0000000000a1")
WRITTEN_ID = uuid.UUID("7e57ab1e-0000-4000-8000-0000000000c1")
ENGLISH = "Kut is the iron black of Ajrakh, made by fermenting scrap iron with jaggery."
QUOTE = "It is made by fermenting scrap iron with jaggery"
HINDI = "कुट अजरख का लोहे वाला काला रंग है, जो लोहे के टुकड़ों को गुड़ के साथ सड़ाकर बनता है।"
WEB_SOURCE = {
    "id": str(SOURCE_ID),
    "kind": "WEB_PAGE",
    "title": "Kut, the iron black of Ajrakh",
    "authors": [],
    "year": None,
    "doi": None,
    "url": PAGE,
    "publisher": None,
    "licence": None,
    "attribution": None,
    "reliability": "C",
}
WRITTEN = ClaimView(
    id=WRITTEN_ID,
    text=ENGLISH,
    level="PROVISIONAL",
    concept_type="MATERIAL",
    concept_id=KUT_CONCEPT,
    citations=[
        {
            "id": "7e57ab1e-0000-4000-8000-0000000000d1",
            "claimId": str(WRITTEN_ID),
            "sourceId": str(SOURCE_ID),
            "quote": QUOTE,
            "locator": None,
            "context": None,
            "evidence": "QUOTED",
            "level": "PROVISIONAL",
        }
    ],
)
RESEARCHED = ResearchedSummary(
    basis="WEB_SEARCH",
    documents=(),
    sentences=(
        ComposedSentence(
            text=ENGLISH,
            evidence_ids=[f"searxng:{PAGE}"],
            spans=[QuotedSpan(ref=f"searxng:{PAGE}", text=QUOTE)],
        ),
    ),
)


def researched_store() -> FakeTermStore:
    return FakeTermStore({"kut": kut_term()}, written=StoredClaims([WRITTEN], {str(SOURCE_ID): WEB_SOURCE}))


def lookup(
    store: FakeTermStore, research: FakeResearch | None = None, model: FakeModel | None = None
) -> TermLookup:
    return TermLookup(
        store=store,
        research=research or FakeResearch(None),
        translation=translation(model),
        clock=lambda: CHECKED_AT,
    )


async def test_a_stored_summary_reproduces_the_term_fixture() -> None:
    store = FakeTermStore({"kut": kut_term()}, stored=golden_claims())
    found = await lookup(store).summary("kut", "en")
    assert found.model_dump(mode="json", by_alias=True) == golden_term()
    assert store.cache[(kut_term().id, "en")] == found


async def test_a_cached_summary_makes_no_second_search_write_or_claim_read() -> None:
    store, research = researched_store(), FakeResearch(RESEARCHED)
    first = await lookup(store, research).summary("kut", "en")
    second = await lookup(store, research).summary("kut", "en")
    assert first == second
    assert first.basis == "WEB_SEARCH"
    assert [sentence.text for sentence in first.summary] == [ENGLISH]
    assert [source.id for source in first.sources] == [str(SOURCE_ID)]
    assert research.calls == 1
    assert (store.calls["defining_claims"], store.calls["write_back"], store.calls["cited"]) == (1, 1, 1)


async def test_another_language_is_translated_once_from_the_english_summary_and_cached() -> None:
    store, research = researched_store(), FakeResearch(RESEARCHED)
    model = FakeModel([json.dumps({"items": [{"key": "kut.1", "text": HINDI}]}, ensure_ascii=False)])
    first = await lookup(store, research, model).summary("kut", "hi")
    again = await lookup(store, research, model).summary("kut", "hi")
    assert first == again
    sentence = first.summary[0]
    assert (first.language, sentence.text, sentence.translated, sentence.original) == (
        "hi",
        HINDI,
        True,
        ENGLISH,
    )
    assert sentence.citations == store.cache[(kut_term().id, "en")].summary[0].citations
    assert len(model.calls) == 1
    assert research.calls == 1


async def test_an_unknown_term_is_refused() -> None:
    with pytest.raises(Refused) as refused:
        await lookup(FakeTermStore({})).summary("not-a-term", "en")
    assert refused.value.reason == UNKNOWN_TERM_REASON


async def test_a_term_with_no_cited_source_is_refused_and_nothing_is_cached() -> None:
    store = FakeTermStore({"kut": kut_term()})
    with pytest.raises(Refused) as refused:
        await lookup(store, FakeResearch(None)).summary("kut", "en")
    assert refused.value.reason == NO_SUMMARY_REASON
    assert store.cache == {}


async def test_stored_hypotheses_are_never_a_summary() -> None:
    claims = golden_claims()
    guess = claims.views[0]
    store = FakeTermStore(
        {"kut": kut_term()},
        stored=StoredClaims(
            [
                ClaimView(
                    guess.id,
                    guess.text,
                    "HYPOTHESIS",
                    guess.concept_type,
                    guess.concept_id,
                    0.0,
                    guess.citations,
                )
            ],
            claims.sources,
        ),
    )
    with pytest.raises(Refused) as refused:
        await lookup(store).summary("kut", "en")
    assert refused.value.reason == NO_SUMMARY_REASON
