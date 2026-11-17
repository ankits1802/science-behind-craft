import json

from app.planner.drafting import draft_plan
from app.planner.orchestrator import ResearchPlanner
from app.planner.plans import retrieval_plan
from app.planner.reading import LiveSources
from app.research.crafts import ANY_CRAFT_LINE
from app.research.planning import FacetCoverage

from .fakes import TWO_FACET_PLAN, FakeAdapter, FakeModel, FakeRetriever, model_for, request, scholarly

OPEN = (FacetCoverage(facet_index=0), FacetCoverage(facet_index=1))
UNANCHORED = {
    **TWO_FACET_PLAN,
    "queries": [{"facetIndex": 1, "tier": "T4", "text": "alizarin alum lake chemistry"}],
}


async def test_a_question_for_any_craft_plans_without_a_craft() -> None:
    model = FakeModel([json.dumps(UNANCHORED)])
    draft = await draft_plan(model, request(craft=None))
    (call,) = model.calls
    assert ANY_CRAFT_LINE in call["user"]
    assert 'ref="craft"' not in call["user"]
    plan = retrieval_plan(request(craft=None), draft, OPEN, mode="HYBRID")
    assert plan.craft is None
    assert [(q.tier, q.facet_index, q.query.text) for q in plan.queries] == [
        ("T3", 0, "alum"),
        ("T4", 1, "alizarin alum lake chemistry"),
    ]


async def test_any_craft_searches_stored_knowledge_across_every_craft() -> None:
    retriever = FakeRetriever()
    openalex = FakeAdapter("openalex", "T3", [scholarly("W1", doi=None)])
    web = FakeAdapter("web", "T4")
    planner = ResearchPlanner(
        model=FakeModel([json.dumps(UNANCHORED)]),
        retriever=retriever,
        sources=LiveSources(searchers=(openalex, web)),
    )
    pack = await planner.research(request(craft=None))
    assert {query.craft_slug for query in retriever.queries} == {None}
    assert pack.stored.craft_slug is None and pack.plan.craft is None
    assert (openalex.searched[0][0], web.searched[0][0]) == ("alum", "alizarin alum lake chemistry")


async def test_a_basic_answer_researches_lightly() -> None:
    six = {
        **TWO_FACET_PLAN,
        "queries": [
            {"facetIndex": 0, "tier": "T3", "text": "Ajrakh alum mordant"},
            {"facetIndex": 1, "tier": "T4", "text": "Ajrakh alizarin alum lake chemistry"},
            {"facetIndex": 0, "tier": "T4", "text": "Ajrakh alum source"},
        ],
    }
    basic = request(depth="BASIC")
    model = FakeModel([json.dumps(six)])
    draft = await draft_plan(model, basic)
    assert "Queries: at most 2" in model.calls[0]["user"]
    plan = retrieval_plan(basic, draft, OPEN, mode="HYBRID")
    assert len(plan.queries) == 2 and plan.max_fetches == 5


async def test_a_detailed_answer_keeps_the_hybrid_budget_and_an_expert_one_the_deep_budget() -> None:
    detailed = request(depth="DETAILED")
    plan = retrieval_plan(detailed, await draft_plan(model_for(), detailed), OPEN, mode="HYBRID")
    assert plan.max_fetches == 10
    expert = request("DEEP", depth="EXPERT")
    plan = retrieval_plan(expert, await draft_plan(model_for(), expert), OPEN, mode="DEEP")
    assert plan.max_fetches == 20
