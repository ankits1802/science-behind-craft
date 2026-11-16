import pytest
from pydantic import ValidationError

from app.research.crafts import CraftCandidate, CraftRef, CraftResolution, MatchReason, clear_winner
from app.research.evidence import SearchQuery
from app.research.planning import MODE_POLICIES, RetrievalPlan

from .fixtures import AJRAKH, BAGRU


def candidate(craft: CraftRef, score: float) -> CraftCandidate:
    return CraftCandidate(
        craft=craft, score=score, reasons=[MatchReason(kind="FUZZY", matched=craft.name, score=score)]
    )


def resolution(status: str, craft: CraftRef | None, *scored: tuple[CraftRef, float]) -> CraftResolution:
    return CraftResolution(
        status=status,
        craft=craft,
        candidates=[candidate(c, s) for c, s in scored],
        normalised="ajrakh",
        script="Latn",
    )


def test_a_craft_ref_points_at_its_page() -> None:
    assert AJRAKH.model_dump() == {
        "slug": "Kutch-Ajrakh",
        "name": "Kutch Ajrakh",
        "path": "/crafts/Kutch-Ajrakh",
    }
    with pytest.raises(ValidationError):
        CraftRef(slug="Kutch-Ajrakh", name="Kutch Ajrakh", path="/crafts/kutch-ajrakh")


def test_a_resolution_agrees_with_its_ranked_candidates() -> None:
    assert resolution("RESOLVED", AJRAKH, (AJRAKH, 0.95), (BAGRU, 0.4)).craft == AJRAKH
    assert resolution("AMBIGUOUS", None, (AJRAKH, 0.6), (BAGRU, 0.55)).craft is None
    assert resolution("AMBIGUOUS", None, (AJRAKH, 0.6)).candidates[0].craft == AJRAKH
    assert resolution("NONE", None).candidates == []
    for status, craft, scored in [
        ("RESOLVED", BAGRU, [(AJRAKH, 0.95), (BAGRU, 0.4)]),
        ("RESOLVED", AJRAKH, [(BAGRU, 0.4), (AJRAKH, 0.95)]),
        ("AMBIGUOUS", None, []),
        ("AMBIGUOUS", AJRAKH, [(AJRAKH, 0.6), (BAGRU, 0.5)]),
        ("NONE", None, [(AJRAKH, 0.2)]),
        ("AMBIGUOUS", None, [(AJRAKH, 0.6)] * 6),
    ]:
        with pytest.raises(ValidationError):
            resolution(status, craft, *scored)


def test_a_clear_winner_needs_score_and_margin() -> None:
    assert clear_winner([candidate(AJRAKH, 0.9), candidate(BAGRU, 0.7)])
    assert clear_winner([candidate(AJRAKH, 0.95), candidate(BAGRU, 0.8)])
    assert not clear_winner([candidate(AJRAKH, 0.9), candidate(BAGRU, 0.8)])
    assert clear_winner([candidate(AJRAKH, 0.85)])
    assert not clear_winner([candidate(AJRAKH, 0.84)])
    assert not clear_winner([])


def test_mode_policies_follow_the_plan() -> None:
    summary = {
        mode: (policy.tiers, policy.live_only_for_open_facets, policy.max_queries, policy.max_fetches)
        for mode, policy in MODE_POLICIES.items()
    }
    assert summary == {
        "VERIFIED": (("T0", "T1"), True, 0, 0),
        "HYBRID": (("T0", "T1", "T2", "T3", "T4"), True, 4, 10),
        "DEEP": (("T0", "T1", "T2", "T3", "T4"), False, 8, 20),
    }


def plan(**changes: object) -> RetrievalPlan:
    fields: dict[str, object] = {
        "mode": "HYBRID",
        "craft": AJRAKH,
        "intent": "SCIENCE",
        "language": "en",
        "needsRegion": False,
        "facets": [{"type": "MECHANISM", "target": "mordant"}],
        "tiers": ["T0", "T1", "T2", "T3"],
        "queries": [{"tier": "T3", "facetIndex": 0, "query": {"text": "Ajrakh alum mordant chemistry"}}],
        "maxFetches": 10,
    }
    fields.update(changes)
    return RetrievalPlan.model_validate(fields)


def test_a_plan_stays_inside_its_mode() -> None:
    assert plan().model_dump()["schemaVersion"] == 1
    query = {"tier": "T3", "facetIndex": 0, "query": {"text": "Ajrakh mordant"}}
    assert len(plan(mode="DEEP", queries=[query] * 8, maxFetches=20).queries) == 8
    for changes in [
        {"mode": "VERIFIED", "maxFetches": 0},
        {"queries": [query] * 5},
        {"maxFetches": 11},
        {"tiers": ["T0", "T1", "T2"]},
        {"tiers": ["T1", "T0", "T3"]},
        {"tiers": ["T0", "T0", "T3"]},
        {"queries": [{"tier": "T3", "facetIndex": 1, "query": {"text": "Ajrakh mordant"}}]},
        {"facets": []},
    ]:
        with pytest.raises(ValidationError):
            plan(**changes)


def test_search_queries_never_carry_personal_data() -> None:
    assert SearchQuery(text="Ajrakh indigo 2019 reduction").text == "Ajrakh indigo 2019 reduction"
    for text in ["Ajrakh asked by someone@example.org", "Ajrakh 98765 43210", "Ajrakh 1234 5678 9012"]:
        with pytest.raises(ValidationError):
            SearchQuery(text=text)
