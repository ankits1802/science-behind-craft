import copy

import pytest
from pydantic import ValidationError

from app.research.craft_compare import CraftComparison
from app.research.explainer import Explainer
from app.research.quiz import ExplainerQuiz, explainer_quiz

from .explainer_golden import DOCUMENT, golden_json, seed_citations
from .golden import reproduces
from .phase_d_golden import phase_d, phase_d_blocks

QUIZ = "learning.quiz.golden.json"
COMPARE = "learning.compare.golden.json"


def document() -> Explainer:
    return Explainer.model_validate(golden_json(DOCUMENT))


@pytest.mark.parametrize(("shape", "name"), [(ExplainerQuiz, QUIZ), (CraftComparison, COMPARE)])
def test_the_quiz_and_compare_fixtures_are_reproduced_byte_for_byte(shape: type, name: str) -> None:
    assert reproduces(shape, name)


def test_the_quiz_fixture_is_what_the_server_makes_of_the_document() -> None:
    every = frozenset(c.claim_id for s in document().sections for b in s.blocks for c in b.citations())
    made = explainer_quiz(document(), visible_claim_ids=every)
    assert made is not None
    assert made.model_dump(mode="json", by_alias=True) == golden_json(QUIZ)


def test_every_quiz_citation_resolves_to_a_seeded_claim_source() -> None:
    seeded = seed_citations()
    quiz = ExplainerQuiz.model_validate(golden_json(QUIZ))
    for sentence in quiz.quiz.cited_sentences():
        for citation in sentence.citations:
            assert seeded[citation.id]["quote"] == citation.quote


def test_the_compare_fixture_is_the_phase_d_comparison_on_its_own_screen() -> None:
    body = CraftComparison.model_validate(golden_json(COMPARE))
    block = copy.deepcopy(phase_d_blocks()["s3.b1"])
    shown = body.comparison.model_dump(mode="json", by_alias=True)
    for row, expected in zip(shown["rows"], block["rows"], strict=True):
        assert [c["sentence"] | {"id": ""} for c in row["cells"]] == [
            c["sentence"] | {"id": ""} for c in expected["cells"]
        ]
    assert (shown["id"], shown["crafts"]) == ("compare", block["crafts"])
    known = {source["id"]: source for source in phase_d()["sources"]}
    assert [s.model_dump(mode="json", by_alias=True) for s in body.sources] == [
        known[s.id] for s in body.sources
    ]


def test_a_comparison_out_of_its_source_order_is_refused() -> None:
    payload = copy.deepcopy(golden_json(COMPARE))
    payload["sources"].reverse()
    with pytest.raises(ValidationError, match="every source it cites once"):
        CraftComparison.model_validate(payload)
