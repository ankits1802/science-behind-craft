import json
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.errors import InvalidInput
from app.research.retrieval import ClaimHit, KnowledgeHits, KnowledgeQuery
from app.research.vocabulary import CONCEPT_TYPE_DISCIPLINES
from app.retrieval.evaluation import (
    GoldenQuestion,
    evaluate_golden,
    recall_at,
    reciprocal_rank,
)
from app.retrieval.golden import GOLDEN_QUESTIONS

SEED_FILE = Path(__file__).resolve().parents[2] / "app" / "data" / "seed_claims.json"


def key(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"test-evaluation/{name}")


class RankedRetriever:
    def __init__(self, ranked: Mapping[str, Sequence[uuid.UUID]]) -> None:
        self.ranked = ranked
        self.queries: list[KnowledgeQuery] = []

    async def search(self, query: KnowledgeQuery) -> KnowledgeHits:
        self.queries.append(query)
        hits = tuple(
            ClaimHit(
                claim_id=found,
                text="A stored claim.",
                level="PROVISIONAL",
                subject_type="CONCEPT",
                subject_id=found,
                score=1.0 / rank,
            )
            for rank, found in enumerate(self.ranked[query.text], start=1)
        )
        return KnowledgeHits(craft_slug=query.craft_slug, claims=hits)


def test_recall_counts_the_expected_hits_within_the_depth() -> None:
    ranked = ["a", "b", "c", "d", "e", "f"]
    assert recall_at(ranked, {"b", "f"}, 5) == 0.5
    assert recall_at(ranked, {"a", "e"}, 5) == 1.0
    assert recall_at(ranked, {"z"}, 5) == 0.0
    with pytest.raises(InvalidInput):
        recall_at(ranked, set(), 5)


def test_the_reciprocal_rank_is_that_of_the_first_expected_hit() -> None:
    ranked = ["a", "b", "c", "d"]
    assert reciprocal_rank(ranked, {"c", "d"}) == pytest.approx(1 / 3)
    assert reciprocal_rank(ranked, {"a"}) == 1.0
    assert reciprocal_rank(ranked, {"z"}) == 0.0


async def test_the_report_averages_recall_and_reciprocal_rank_over_the_questions() -> None:
    golden = (
        GoldenQuestion(key="first", craft_slug="Kutch-Ajrakh", question="q1", expected=("x", "y")),
        GoldenQuestion(key="second", craft_slug=None, question="q2", expected=("z",), fields=("CHEMISTRY",)),
    )
    ids = {"x": key("x"), "y": key("y"), "z": key("z")}
    noise = [key(f"noise-{n}") for n in range(6)]
    retriever = RankedRetriever({"q1": [noise[0], ids["x"], *noise[1:5], ids["y"]], "q2": [ids["z"]]})
    report = await evaluate_golden(retriever, golden, claim_id=ids.__getitem__)
    assert report.recall_at_depth == pytest.approx((0.5 + 1.0) / 2)
    assert report.mean_reciprocal_rank == pytest.approx((1 / 2 + 1) / 2)
    assert report.as_dict()["misses"] == {"first": ["y"]}
    assert [(q.mode, q.limit, q.fields) for q in retriever.queries] == [
        ("HYBRID", 10, ()),
        ("HYBRID", 10, ("CHEMISTRY",)),
    ]


async def test_expected_hits_missing_from_the_database_are_reported_not_scored() -> None:
    golden = (
        GoldenQuestion(key="kept", craft_slug=None, question="q1", expected=("x", "gone")),
        GoldenQuestion(key="lost", craft_slug=None, question="q2", expected=("lost",)),
    )
    ids = {"x": key("x"), "gone": key("gone"), "lost": key("lost")}
    retriever = RankedRetriever({"q1": [ids["x"]], "q2": []})
    report = await evaluate_golden(retriever, golden, claim_id=ids.__getitem__, present={ids["x"]})
    assert report.absent == ("gone", "lost")
    assert [result.key for result in report.results] == ["kept"]
    assert report.recall_at_depth == 1.0 and report.mean_reciprocal_rank == 1.0
    assert [query.text for query in retriever.queries] == ["q1"]


def test_a_golden_question_lists_each_expected_hit_once() -> None:
    with pytest.raises(ValidationError):
        GoldenQuestion(key="twice", craft_slug=None, question="q", expected=("x", "x"))
    with pytest.raises(ValidationError):
        GoldenQuestion(key="none", craft_slug=None, question="q", expected=())


def test_every_golden_hit_is_a_seeded_claim_of_the_named_craft_in_an_allowed_field() -> None:
    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    claims = {row["id"]: row for row in data["claims"]}
    types = {row["key"]: row["type"] for row in data["concepts"]}
    assert 18 <= len(GOLDEN_QUESTIONS) <= 25
    assert len({question.key for question in GOLDEN_QUESTIONS}) == len(GOLDEN_QUESTIONS)
    for question in GOLDEN_QUESTIONS:
        for expected in question.expected:
            claim = claims[expected]
            field = CONCEPT_TYPE_DISCIPLINES.get(types[claim["subjectKey"]])
            assert claim["subjectType"] == "CONCEPT" and claim["evidenceLevel"] == "PROVISIONAL", expected
            assert claim["craftSlug"] == question.craft_slug, expected
            assert not question.fields or field is None or field in question.fields, expected
