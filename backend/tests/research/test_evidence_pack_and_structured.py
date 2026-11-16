import uuid

import pytest
from pydantic import ValidationError

from app.core.errors import ExternalFailure
from app.research.evidence_pack import EvidencePack, PackedEvidence, ResearchFailure
from app.research.planning import (
    COVERING_LEVELS,
    FACET_COVERED_MIN_CLAIMS,
    FacetCoverage,
    PlanRequest,
    RetrievalPlan,
)
from app.research.retrieval import KnowledgeHits
from app.research.structured import StructuredReply, reply_object
from app.sources.adapter import build_document

from .fixtures import AJRAKH, BAGRU, evidence_item

PLAN = RetrievalPlan.model_validate(
    {
        "mode": "HYBRID",
        "craft": AJRAKH,
        "intent": "SCIENCE",
        "language": "en",
        "needsRegion": False,
        "facets": [{"type": "MATERIAL", "target": "alum"}, {"type": "MECHANISM", "target": "binding"}],
        "tiers": ["T0", "T1", "T2", "T3"],
        "queries": [{"tier": "T3", "facetIndex": 1, "query": {"text": "Ajrakh alum binding"}}],
        "maxFetches": 1,
    }
)
ITEM = evidence_item()
OTHER = evidence_item(id="openalex:W2", url="https://example.org/w2", doi=None, quotes=[])


def entry(item=ITEM, **changes: object) -> PackedEvidence:
    fields: dict[str, object] = {
        "item": item,
        "facetIndexes": (1,),
        "foundBy": ("openalex",),
        "hits": 1,
        "bestRank": 1,
    }
    fields.update(changes)
    return PackedEvidence.model_validate(fields)


def pack(**changes: object) -> EvidencePack:
    fields: dict[str, object] = {
        "plan": PLAN,
        "degraded": False,
        "stored": KnowledgeHits(craft_slug=AJRAKH.slug),
        "coverage": (FacetCoverage(facet_index=0), FacetCoverage(facet_index=1)),
        "evidence": (entry(),),
        "documents": (
            build_document(ITEM, "alum forms a red lake with alizarin at about 60 °C.", "ABSTRACT"),
        ),
    }
    fields.update(changes)
    return EvidencePack.model_validate(fields)


def test_mode_coverage_follows_the_plan() -> None:
    assert FACET_COVERED_MIN_CLAIMS == 2
    assert dict(COVERING_LEVELS) == {
        "VERIFIED": ("VERIFIED", "REVIEWED"),
        "HYBRID": ("VERIFIED", "REVIEWED", "PROVISIONAL"),
        "DEEP": ("VERIFIED", "REVIEWED", "PROVISIONAL"),
    }
    assert not FacetCoverage(facet_index=0, claim_ids=(uuid.uuid4(),)).covered
    assert FacetCoverage(facet_index=0, claim_ids=(uuid.uuid4(), uuid.uuid4())).covered


def test_a_pack_is_consistent_with_its_plan() -> None:
    assert pack().model_dump()["schemaVersion"] == 1
    followed = entry(OTHER, followedFrom=ITEM.id)
    assert pack(evidence=(entry(), followed)).evidence[1].followed_from == ITEM.id
    document = build_document(OTHER, "text", "ABSTRACT")
    for changes in [
        {"stored": KnowledgeHits(craft_slug=BAGRU.slug)},
        {"coverage": (FacetCoverage(facet_index=1), FacetCoverage(facet_index=0))},
        {"coverage": (FacetCoverage(facet_index=0),)},
        {"evidence": (entry(), entry())},
        {"evidence": (entry(facetIndexes=(2,)),)},
        {"evidence": (entry(), entry(OTHER, followedFrom="openalex:W9"))},
        {"documents": (document,)},
        {"evidence": (entry(), entry(OTHER)), "documents": (*pack().documents, document)},
    ]:
        with pytest.raises(ValidationError):
            pack(**changes)


def test_a_failure_names_its_stage_and_only_refusals_carry_a_reason() -> None:
    base = {"stage": "FETCH", "service": "fetcher", "target": "https://example.org/a"}
    assert ResearchFailure(**base, kind="refused", reason="ROBOTS_DISALLOWED", message="robots").reason
    assert ResearchFailure(**base, kind="not_found", message="gone").kind == "not_found"
    for bad in [
        {"kind": "refused", "message": "no reason"},
        {"kind": "not_found", "reason": "ROBOTS_DISALLOWED", "message": "x"},
        {"kind": "teapot", "message": "x"},
        {"kind": "error", "message": "x", "stage": "GUESS"},
    ]:
        with pytest.raises(ValidationError):
            ResearchFailure(**{**base, **bad})


def test_a_plan_request_keeps_withheld_terms_short() -> None:
    fields = {"question": "Why alum?", "mode": "HYBRID", "craft": AJRAKH}
    assert PlanRequest(**fields, withheld_terms=(" Meera ",)).withheld_terms == ("Meera",)
    for terms in [("x",), ("y" * 201,), tuple(f"term {n}" for n in range(21))]:
        with pytest.raises(ValidationError):
            PlanRequest(**fields, withheld_terms=terms)


def test_a_structured_reply_is_one_json_object() -> None:
    assert reply_object(StructuredReply(text='{"a": 1}', degraded=False)) == {"a": 1}
    assert reply_object(StructuredReply(text='```json\n{"a": [1]}\n```', degraded=False)) == {"a": [1]}
    for text, message in [("{oops", "not JSON"), ("[1, 2]", "JSON list"), ("", "not JSON")]:
        with pytest.raises(ExternalFailure, match=message) as raised:
            reply_object(StructuredReply(text=text, degraded=False))
        assert raised.value.service == "model"
