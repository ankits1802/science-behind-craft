import pytest
from pydantic import ValidationError

from app.core.errors import NotConfigured
from app.planner.drafting import draft_plan
from app.planner.plans import retrieval_plan
from app.planner.reading import LiveSources
from app.research.planning import FacetCoverage, RetrievalPlan

from .fakes import TWO_FACET_PLAN, FakeAdapter, FakeRetriever, claim, model_for, request
from .test_research_run import planner

COVERED = FacetCoverage(facet_index=0, claim_ids=(claim("a").claim_id, claim("b").claim_id))
OPEN = FacetCoverage(facet_index=1)
NATIVE_PLAN = {
    **TWO_FACET_PLAN,
    "nativeQueries": [
        {"facetIndex": 1, "text": "अजरख फिटकरी लेक रसायन"},
        {"facetIndex": 1, "text": "फिटकरी रंग बंधन"},
        {"facetIndex": 1, "text": "अजरख की तीसरी खोज"},
        {"facetIndex": 0, "text": "अजरख फिटकरी"},
    ],
    "nativeCraftName": "अजरख",
    "englishQuestion": "Why does alum keep Ajrakh red?",
}


@pytest.mark.parametrize(
    ("language", "mode", "native"), [("hi", "HYBRID", 2), ("ur", "DEEP", 3), ("en", "HYBRID", 0)]
)
async def test_the_plan_call_asks_for_native_queries_only_outside_english(
    language: str, mode: str, native: int
) -> None:
    model = model_for()
    await draft_plan(model, request(mode, language=language))
    (call,) = model.calls
    assert call["schema"]["properties"]["nativeQueries"]["maxItems"] == native
    assert f"Native-language queries: at most {native}" in call["user"]


async def test_the_answer_language_is_named_for_the_planner() -> None:
    model = model_for()
    await draft_plan(model, request(language="ta"))
    assert "Answer language: ta (Tamil)" in model.calls[0]["user"]


async def test_native_queries_search_the_answer_languages_wikis_for_open_facets() -> None:
    draft = await draft_plan(model_for(NATIVE_PLAN), request(language="hi"))
    plan = retrieval_plan(request(language="hi"), draft, [COVERED, OPEN], mode="HYBRID")
    assert [(q.tier, q.facet_index, q.query.text, q.query.language) for q in plan.queries] == [
        ("T4", 1, "Kutch Ajrakh alizarin alum lake chemistry", "en"),
        ("T3", 1, "अजरख फिटकरी लेक रसायन", "hi"),
        ("T3", 1, "अजरख फिटकरी रंग बंधन", "hi"),
    ]
    assert plan.tiers == ["T0", "T1", "T2", "T3", "T4"]


async def test_an_english_answer_plans_no_native_queries() -> None:
    draft = await draft_plan(model_for(NATIVE_PLAN), request())
    plan = retrieval_plan(request(), draft, [COVERED, OPEN], mode="HYBRID")
    assert [q.query.language for q in plan.queries] == ["en"]


async def test_native_queries_run_only_on_wikipedia_and_wikidata() -> None:
    openalex = FakeAdapter("openalex", "T3")
    wikipedia = FakeAdapter("wikipedia", "T3")
    wikidata = FakeAdapter("wikidata", "T3")
    web = FakeAdapter("web", "T4")
    sources = LiveSources(searchers=(openalex, wikipedia, wikidata, web))
    await planner(sources, plan=NATIVE_PLAN).research(request(language="hi"))
    assert openalex.languages == ["en"]
    assert wikipedia.languages == wikidata.languages == ["en", "hi", "hi"]
    assert web.languages == ["en"]


async def test_native_queries_need_a_source_that_reads_the_language() -> None:
    sources = LiveSources(searchers=(FakeAdapter("openalex", "T3"), FakeAdapter("web", "T4")))
    with pytest.raises(NotConfigured):
        await planner(sources, plan=NATIVE_PLAN).research(request(language="hi"))


async def test_stored_claims_are_searched_with_the_english_rendering() -> None:
    retriever = FakeRetriever()
    sources = LiveSources(
        searchers=(FakeAdapter("openalex", "T3"), FakeAdapter("wikipedia", "T3"), FakeAdapter("web", "T4"))
    )
    question = "अजरख को फिटकरी लाल क्यों रखती है?"
    await planner(sources, retriever=retriever, plan=NATIVE_PLAN).research(
        request(question=question, language="hi")
    )
    assert retriever.queries[-1].text == "Why does alum keep Ajrakh red?"
    retriever = FakeRetriever()
    english = "Why does alum make Ajrakh red last?"
    await planner(sources, retriever=retriever, plan=NATIVE_PLAN).research(
        request(question=english, language="hi", english_question=english)
    )
    assert retriever.queries[-1].text == english


async def test_a_plan_refuses_native_queries_off_the_reference_tier_or_over_the_limit() -> None:
    draft = await draft_plan(model_for(NATIVE_PLAN), request(language="hi"))
    plan = retrieval_plan(request(language="hi"), draft, [COVERED, OPEN], mode="HYBRID").model_dump(
        by_alias=True
    )
    on_web = {**plan, "queries": [{**plan["queries"][1], "tier": "T4"}]}
    with pytest.raises(ValidationError, match="native-language queries are T3"):
        RetrievalPlan.model_validate(on_web)
    too_many = {**plan, "queries": [*plan["queries"], {**plan["queries"][1], "facetIndex": 0}]}
    with pytest.raises(ValidationError, match="at most 2 native-language queries"):
        RetrievalPlan.model_validate(too_many)
